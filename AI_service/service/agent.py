"""Worker agent: joins a Knit cluster by code, profiles this machine, and runs whatever
stage the orchestrator assigns (it starts and stops its own stage server).

  python -m service.agent KNIT-8821-X
  env: KNIT_ORCH         ws://127.0.0.1:8080
       KNIT_CODE         cluster code (or pass as first argument)
       KNIT_NAME         display name (default: hostname)
       KNIT_PUBLIC_HOST  address other machines use to reach this PC
                         (default: 127.0.0.1 if the orchestrator is local, else the LAN IP)
       KNIT_STAGE_PORT   fixed port for this PC's stage server (default: random; fix it to open one firewall port)
       KNIT_LOCAL        optional: attach a stage server you started by hand
"""
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

import httpx
import psutil
import torch
from websockets.sync.client import connect

ORCH = os.environ.get("KNIT_ORCH", "ws://127.0.0.1:8080")
CODE = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("KNIT_CODE", "")).strip().upper()
LOCAL = os.environ.get("KNIT_LOCAL", "").rstrip("/")
NAME = os.environ.get("KNIT_NAME", socket.gethostname().split(".")[0])
NODE_ID = f"{NAME}-{os.getpid()}"

http = httpx.Client(verify=False, timeout=httpx.Timeout(0.5, connect=0.3))   # built once
stage = {"url": LOCAL, "pub": os.environ.get("KNIT_PUBLIC_URL", LOCAL), "proc": None, "loading": False}


class Rejected(Exception):
    pass


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


HOST = os.environ.get("KNIT_PUBLIC_HOST") or (
    "127.0.0.1" if urlparse(ORCH).hostname in ("127.0.0.1", "localhost") else lan_ip())


def mem() -> dict:
    m = {"ram_free_gb": round(psutil.virtual_memory().available / 2**30, 2)}
    if torch.cuda.is_available():
        m["vram_free_gb"] = round(torch.cuda.mem_get_info()[0] / 2**30, 2)
    return m


def bench(device: str, n: int = 1024, secs: float = 0.6) -> float:
    """Measured fp32 matmul GFLOPS (matches how stages run today)."""
    a, b = torch.randn(n, n, device=device), torch.randn(n, n, device=device)
    for _ in range(3):
        a @ b
    if device == "cuda":
        torch.cuda.synchronize()
    t0, it = time.perf_counter(), 0
    while time.perf_counter() - t0 < secs:
        a @ b
        it += 1
    if device == "cuda":
        torch.cuda.synchronize()
    return round(2 * n**3 * it / (time.perf_counter() - t0) / 1e9, 1)


def profile() -> dict:
    vm, cuda = psutil.virtual_memory(), torch.cuda.is_available()
    device = "cuda" if cuda else "cpu"
    p = {"device": device, "cuda": cuda, "platform": platform.platform(),
         "cpu_cores": psutil.cpu_count(logical=False) or psutil.cpu_count(),
         "ram_total_gb": round(vm.total / 2**30, 2), **mem()}
    if cuda:
        p["gpu_name"] = torch.cuda.get_device_name(0)
        p["vram_total_gb"] = round(torch.cuda.mem_get_info()[1] / 2**30, 2)
        p["usable_gb"] = round(p["vram_free_gb"] * 0.9, 2)
    else:
        p["usable_gb"] = round(p["ram_free_gb"] * 0.6, 2)
    p["bench_gflops"] = bench(device)
    return p


def stage_info() -> dict:
    return http.get(f"{stage['url']}/info").json()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def stop_stage():
    p = stage["proc"]
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            p.kill()
    stage.update(proc=None, url="", pub="")


def load_stage(m: dict, prof: dict, send):
    """Start a stage server for layers [start,end) of the requested model."""
    stage["loading"] = True
    try:
        stop_stage()
        port = int(os.environ.get("KNIT_STAGE_PORT", 0)) or free_port()
        env = {**os.environ, "KNIT_MODEL": m["model"], "KNIT_START": str(m["start"]),
               "KNIT_END": str(m["end"]), "KNIT_DEVICE": prof["device"]}
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "service.stage_server:app",
                                 "--host", "0.0.0.0", "--port", str(port), "--log-level", "warning"], env=env)
        stage["proc"] = proc
        url, t0 = f"http://127.0.0.1:{port}", time.time()
        print(f"loading {m['model']} layers [{m['start']},{m['end']}) ...")
        while True:
            if proc.poll() is not None:
                raise RuntimeError(f"stage process exited with code {proc.returncode}")
            if time.time() - t0 > 1800:
                raise TimeoutError("stage did not start within 30 min")
            try:
                http.get(f"{url}/info")
                break
            except httpx.HTTPError:
                time.sleep(1)
        stage.update(url=url, pub=f"http://{HOST}:{port}")
        print(f"stage ready on {stage['pub']} ({time.time() - t0:.0f} s)")
        send({"type": "loaded"})
    except Exception as e:
        stop_stage()
        print("load failed:", e)
        send({"type": "load_failed", "error": f"{NAME}: {e}"})
    finally:
        stage["loading"] = False


def run_once(prof: dict):
    info = stage_info() if stage["url"] else {}    # raises httpx.HTTPError if a KNIT_LOCAL stage is not up
    with connect(ORCH) as ws:
        lock = threading.Lock()
        state = {"ack": False, "err": None}

        def send(o):
            with lock:
                ws.send(json.dumps(o))

        def reader():
            try:
                for raw in ws:
                    m = json.loads(raw)
                    t = m["type"]
                    if t == "ping":
                        send({"type": "pong", "t": m["t"]})
                    elif t == "registered":
                        state["ack"] = True
                    elif t == "error":
                        state["err"] = m["message"]
                    elif t == "load":
                        threading.Thread(target=load_stage, args=(m, prof, send), daemon=True).start()
                    elif t == "unload":
                        threading.Thread(target=stop_stage, daemon=True).start()
            except Exception:
                pass

        threading.Thread(target=reader, daemon=True).start()
        send({"type": "register", "code": CODE, "id": NODE_ID, "name": NAME, "url": stage["pub"],
              "capacity": prof["bench_gflops"], "profile": prof, "device": prof["device"], **info})
        t0 = time.time()
        while not state["ack"] and not state["err"] and time.time() - t0 < 5:
            time.sleep(0.05)
        if state["err"]:
            raise Rejected(state["err"])
        if not state["ack"]:
            raise ConnectionError("no ack from orchestrator")
        print(f"joined {CODE} as {NODE_ID} | {prof['device']} | {prof['bench_gflops']} GFLOPS | "
              f"{prof['usable_gb']} GB usable. Waiting for the master to start a model.")

        idle = {"start": None, "end": None, "first": None, "last": None}
        while True:
            t0 = time.perf_counter()
            if state["err"]:
                raise Rejected(state["err"])
            hb = {"type": "hb", "id": NODE_ID, **mem()}
            try:
                if stage["loading"]:
                    hb.update(idle, loading=True)
                elif stage["url"]:
                    i = stage_info()
                    hb.update(sessions=i["sessions"], start=i["start"], end=i["end"], first=i["first"],
                              last=i["last"], url=stage["pub"], loading=False)
                else:
                    hb.update(idle, loading=False, url="")
                send(hb)
            except httpx.HTTPError:
                pass        # stage died: stop heartbeating, orchestrator marks the node dead
            time.sleep(max(0.0, 0.1 - (time.perf_counter() - t0)))


def main():
    if not CODE:
        sys.exit("usage: python -m service.agent KNIT-1234-X")
    print("profiling this machine...")
    prof = profile()
    try:
        while True:
            try:
                run_once(prof)
            except Rejected as e:
                sys.exit(f"orchestrator refused: {e}")
            except httpx.HTTPError:
                print(f"waiting for stage at {stage['url']} ...")
                time.sleep(1)
            except Exception as e:
                print(f"orchestrator connection lost ({type(e).__name__}); retrying")
                time.sleep(1)
    finally:
        stop_stage()


if __name__ == "__main__":
    main()