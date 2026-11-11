"""Kill a stage mid-generation; recover on a standby by replaying history.

Run from ai_service/ (spawns its own servers; first start takes a while to load models).
"""
import os
import statistics
import subprocess
import sys
import time

import httpx
import torch
from transformers import AutoTokenizer

from knit.remote import RemoteStage
from knit.resilient import ResilientPipeline

MODEL, N_NEW, KILL_AT = "Qwen/Qwen2.5-0.5B-Instruct", 24, 10
LAYOUT = {9001: (0, 8), 9002: (8, 16), 9003: (16, 24), 9012: (8, 16)}   # 9012 = standby for stage 1


def launch(port, s, e):
    env = {**os.environ, "KNIT_MODEL": MODEL, "KNIT_START": str(s), "KNIT_END": str(e)}
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "service.stage_server:app",
                             "--port", str(port), "--log-level", "warning"],
                            env=env, stdout=subprocess.DEVNULL)

def wait(port, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if httpx.get(f"http://localhost:{port}/info", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError(port)


procs = {p: launch(p, *r) for p, r in LAYOUT.items()}
try:
    for p in procs:
        wait(p)
    tok = AutoTokenizer.from_pretrained(MODEL)
    ids = tok("Explain pipeline parallelism in one sentence.", return_tensors="pt").input_ids
    pipe = ResilientPipeline([RemoteStage(f"http://localhost:{p}") for p in (9001, 9002, 9003)],
                             {1: ["http://localhost:9012"]})

    def gen(sid, kill_at=None):
        pipe.reset(sid)
        logits, out, step_ms = pipe.forward(sid, ids), [], []
        for i in range(N_NEW):
            t0 = time.perf_counter()
            nxt = int(logits[0, -1].argmax()); out.append(nxt)
            if i == kill_at:
                procs[9002].kill(); procs[9002].wait()      # crash stage 1 right now
            logits = pipe.forward(sid, torch.tensor([[nxt]]))
            step_ms.append((time.perf_counter() - t0) * 1000)
        return out, step_ms

    ref, ref_ms = gen("ref")
    out, ms = gen("fail", kill_at=KILL_AT)
    r = pipe.recoveries[-1]
    print(f"output identical after failure : {out == ref}")
    print(f"median normal step             : {statistics.median(ref_ms):.0f} ms")
    print(f"step containing the crash      : {ms[KILL_AT]:.0f} ms")
    print({k: round(v) if isinstance(v, float) else v for k, v in r.items() if k != 'sid'})
finally:
    for p in procs.values():
        p.kill()