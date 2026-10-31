"""One stage as an HTTP service (the 'AI service' a worker node runs).

  python -m uvicorn service.stage_server:app --port 9001
  env: KNIT_MODEL, KNIT_START, KNIT_END, KNIT_DEVICE
"""
import os

import torch
from fastapi import FastAPI, Request, Response
from transformers import AutoModelForCausalLM

from knit.stage import StageExecutor
from knit.wire import pack, unpack

MODEL = os.environ.get("KNIT_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
START, END = int(os.environ.get("KNIT_START", 0)), int(os.environ.get("KNIT_END", 8))
DEVICE = os.environ.get("KNIT_DEVICE", "cpu")

_model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32)
stage = StageExecutor(_model, START, END, DEVICE)
del _model
app = FastAPI(title=f"Knit stage [{START},{END})")


@app.get("/info")
def info():
    return {"model": MODEL, "start": START, "end": END, "first": stage.is_first,
            "last": stage.is_last, "device": DEVICE, "sessions": len(stage.sessions)}


@app.post("/reset/{sid}")
def reset(sid: str):
    stage.reset(sid)
    return {"ok": True}


@app.post("/rollback/{sid}/{pos}")
def rollback(sid: str, pos: int):
    stage.rollback(sid, pos)
    return {"ok": True}


@app.post("/forward/{sid}")
async def forward(sid: str, request: Request):
    x = unpack(await request.body(), request.headers["x-dtype"],
               [int(v) for v in request.headers["x-shape"].split(",")])
    y = stage.forward(sid, x)
    raw, meta = pack(y)
    return Response(raw, media_type="application/octet-stream", headers={
        "x-dtype": meta["dtype"], "x-shape": ",".join(map(str, meta["shape"])),
        "x-compute-ms": f"{stage.last_compute_ms:.2f}"})