"""Chat gateway: finds the ready cluster, runs the sharded pipeline, streams tokens to the dashboard.

  python -m service.gateway KNIT-8821-X [--port 8000] [--orch http://127.0.0.1:8080] [--spec] [--k 4]
"""
import argparse
import base64
import io
import json
import threading
import time
import uuid

import httpx
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from knit.discover import discover
from knit.pipeline import Pipeline

ap = argparse.ArgumentParser()
ap.add_argument("code")
ap.add_argument("--orch", default="http://127.0.0.1:8080")
ap.add_argument("--host", default="127.0.0.1")
ap.add_argument("--port", type=int, default=8000)
ap.add_argument("--spec", action="store_true", help="speculative decoding with a 0.5B drafter")
ap.add_argument("--draft", default="Qwen/Qwen2.5-0.5B-Instruct")
ap.add_argument("--k", type=int, default=4)
ap.add_argument("--vision", action="store_true", help="describe attached images with a BLIP captioner (not true multimodal)")
a = ap.parse_args()
CODE = a.code.strip().upper()

app = FastAPI(title="Knit gateway")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
lock = threading.Lock()           # one chat at a time
cache = {}
draft = AutoModelForCausalLM.from_pretrained(a.draft, torch_dtype=torch.float32).eval() if a.spec else None

blip = {}
if a.vision:
    from transformers import BlipForConditionalGeneration, BlipProcessor
    _n = "Salesforce/blip-image-captioning-base"
    blip["proc"] = BlipProcessor.from_pretrained(_n)
    blip["model"] = BlipForConditionalGeneration.from_pretrained(_n).eval()


def caption(data_url: str) -> str:
    from PIL import Image
    img = Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))).convert("RGB")
    inp = blip["proc"](images=img, return_tensors="pt")
    with torch.inference_mode():
        out = blip["model"].generate(**inp, max_new_tokens=40)
    return blip["proc"].decode(out[0], skip_special_tokens=True)


def cluster_info() -> dict:
    r = httpx.get(f"{a.orch}/cluster/{CODE}/info", timeout=5)
    r.raise_for_status()
    return r.json()


def get_pipe():
    i = cluster_info()
    if i["status"] != "ready":
        raise HTTPException(409, f"Cluster is {i['status']}. Start it from the dashboard first.")
    key = (i["hf"], tuple((p["id"], p["start"], p["end"]) for p in i["plan"]))
    if cache.get("key") != key:
        try:
            stages = discover(a.orch, CODE)
        except AssertionError as e:
            raise HTTPException(409, f"Stages not ready: {e}")
        cache.update(key=key, pipe=Pipeline(stages), tok=AutoTokenizer.from_pretrained(i["hf"]))
    return cache["pipe"], cache["tok"]


@torch.inference_mode()
def token_chunks(pipe, ids, max_new, eos, drafter, k):
    """Yield lists of newly committed token ids (greedy; exact with or without speculation)."""
    sid, P = uuid.uuid4().hex, ids.shape[1]
    try:
        pipe.reset(sid)
        out = [int(pipe.forward(sid, ids)[0, -1].argmax())]
        yield [out[0]]
        while len(out) < max_new and out[-1] not in eos:
            if drafter is None:
                t = int(pipe.forward(sid, torch.tensor([[out[-1]]]))[0, -1].argmax())
                out.append(t)
                yield [t]
            else:
                seq = torch.cat([ids, torch.tensor([out])], dim=1)
                d = drafter.generate(seq, attention_mask=torch.ones_like(seq),
                                     max_new_tokens=k, do_sample=False)[0, seq.shape[1]:].tolist()
                t = pipe.forward(sid, torch.tensor([[out[-1]] + d]))[0].argmax(-1).tolist()
                n = 0
                while n < len(d) and d[n] == t[n]:
                    n += 1
                new = d[:n] + [t[n]]
                out += new
                pipe.rollback(sid, P + len(out) - 1)
                yield new
    finally:
        for st in pipe.stages:
            try:
                st.close(sid)
            except Exception:
                pass


def sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"


class Chat(BaseModel):
    messages: list
    max_new: int = 256


@app.get("/status")
def status():
    return cluster_info()


@app.post("/chat")
def chat(req: Chat):
    try:
        pipe, tok = get_pipe()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(409, str(e))
    eos = {x for x in (tok.eos_token_id, tok.pad_token_id) if x is not None}

    def gen():
        with lock:
            chunks = None
            try:
                msgs = []
                for m in req.messages:
                    c = m.get("content", "")
                    for im in m.get("images") or []:
                        if not blip:
                            raise RuntimeError("The model is text-only. Restart the gateway with --vision "
                                               "to describe images with a captioner.")
                        cap = caption(im)
                        c += f"\n[Attached image: {cap}]"
                        yield sse({"caption": cap})
                    msgs.append({"role": m["role"], "content": c})
                text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                ids = tok(text, return_tensors="pt").input_ids
                base, out, shown, t0 = list(pipe.stats["compute_ms"]), [], "", time.perf_counter()
                chunks = token_chunks(pipe, ids, req.max_new, eos, draft, a.k)
                stop = False
                for chunk in chunks:
                    for t in chunk:
                        if t in eos or len(out) >= req.max_new:
                            stop = True
                            break
                        out.append(t)
                    txt = tok.decode(out, skip_special_tokens=True)
                    if not (txt.endswith("\ufffd") and not stop):
                        if txt[len(shown):]:
                            yield sse({"t": txt[len(shown):]})
                        shown = txt
                    # per-stage compute vs wall time so far (the "X-ray")
                    yield sse({"x": {"c": [round(c2 - c1, 1) for c1, c2 in zip(base, pipe.stats["compute_ms"])],
                                     "w": round((time.perf_counter() - t0) * 1000, 1), "n": len(out)}})
                    if stop:
                        break
                yield sse({"done": True, "tokens": len(out),
                           "tok_s": len(out) / max(time.perf_counter() - t0, 1e-6)})
            except Exception as e:
                yield sse({"error": f"{type(e).__name__}: {e}"})
            finally:
                if chunks:
                    chunks.close()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print(f"Knit gateway for {CODE} on http://{a.host}:{a.port}  (speculation: {'on' if draft else 'off'}, vision captioner: {'on' if blip else 'off'})")
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")