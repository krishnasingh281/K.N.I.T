"""One stage as an HTTP service, optionally chained to the next stage.

  python -m uvicorn service.stage_server:app --port 9001
  env: KNIT_MODEL, KNIT_START, KNIT_END, KNIT_DEVICE,
       KNIT_NEXT   (url of next stage; omit on last stage)
       KNIT_CODEC  (none|bf16|fp16|int8, applied to hidden states sent downstream)
       KNIT_TTL    (idle session seconds before eviction, default 300)
       KNIT_DELAY_MS (emulated per-stage RTT, default 0)
"""
import os
import threading
import time

import httpx
import torch
from fastapi import FastAPI, Request, Response
from starlette.concurrency import run_in_threadpool
from transformers import AutoModelForCausalLM

from knit.stage import StageExecutor
from knit.wire import pack, unpack

MODEL = os.environ.get("KNIT_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
START, END = int(os.environ.get("KNIT_START", 0)), int(os.environ.get("KNIT_END", 8))
DEVICE = os.environ.get("KNIT_DEVICE", "cpu")
NEXT = os.environ.get("KNIT_NEXT", "").rstrip("/")
CODEC = os.environ.get("KNIT_CODEC", "none")
TTL = float(os.environ.get("KNIT_TTL", 300))
DELAY = float(os.environ.get("KNIT_DELAY_MS", 0))

_model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32)
stage = StageExecutor(_model, START, END, DEVICE)
del _model

lock = threading.Lock()                    # one forward at a time per stage
nxt = httpx.Client(timeout=120) if NEXT else None
app = FastAPI(title=f"Knit stage [{START},{END})")


def _reaper():
    while True:
        time.sleep(max(TTL / 4, 1))
        with lock:
            stage.reap(TTL)


threading.Thread(target=_reaper, daemon=True).start()


def _propagate(method: str, path: str):
    if nxt:
        nxt.request(method, f"{NEXT}{path}").raise_for_status()


@app.get("/info")
def info():
    return {"model": MODEL, "start": START, "end": END, "first": stage.is_first,
            "last": stage.is_last, "device": DEVICE, "sessions": len(stage.sessions),
            "next": NEXT or None, "codec": CODEC}


@app.post("/reset/{sid}")
def reset(sid: str):
    with lock:
        stage.reset(sid)
    _propagate("POST", f"/reset/{sid}")
    return {"ok": True}


@app.post("/rollback/{sid}/{pos}")
def rollback(sid: str, pos: int):
    with lock:
        stage.rollback(sid, pos)
    _propagate("POST", f"/rollback/{sid}/{pos}")
    return {"ok": True}


@app.delete("/session/{sid}")
def delete_session(sid: str):
    with lock:
        stage.drop(sid)
    _propagate("DELETE", f"/session/{sid}")
    return {"ok": True}


def _forward(sid: str, body: bytes, dtype: str, shape: str) -> Response:
    if DELAY:
        time.sleep(DELAY / 2000)
    x = unpack(body, dtype, [int(v) for v in shape.split(",")])
    with lock:
        y = stage.forward(sid, x)
        ms = stage.last_compute_ms
    if nxt is None:                                   # last stage: return logits untouched
        raw, m = pack(y)
        h = {"x-dtype": m["dtype"], "x-shape": ",".join(map(str, m["shape"]))}
    else:                                             # chain to next stage
        raw, m = pack(y, CODEC)
        r = nxt.post(f"{NEXT}/forward/{sid}", content=raw, headers={
            "x-dtype": m["dtype"], "x-shape": ",".join(map(str, m["shape"]))})
        r.raise_for_status()
        ms += float(r.headers["x-compute-ms"])
        raw = r.content
        h = {"x-dtype": r.headers["x-dtype"], "x-shape": r.headers["x-shape"]}
    if DELAY:
        time.sleep(DELAY / 2000)
    h["x-compute-ms"] = f"{ms:.2f}"
    return Response(raw, media_type="application/octet-stream", headers=h)


@app.post("/forward/{sid}")
async def forward(sid: str, request: Request):
    body = await request.body()
    hd = request.headers
    return await run_in_threadpool(_forward, sid, body, hd["x-dtype"], hd["x-shape"])