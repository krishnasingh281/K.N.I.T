"""One stage as a gRPC service.

  python -m service.grpc_server
  env: KNIT_MODEL, KNIT_START, KNIT_END, KNIT_DEVICE, KNIT_PORT (9101),
       KNIT_NEXT (host:port of next stage), KNIT_CODEC, KNIT_TTL
"""
import os
import threading
import time
from concurrent import futures

import grpc
import torch
from transformers import AutoModelForCausalLM

from knit import stage_pb2 as pb
from knit import stage_pb2_grpc as pbg
from knit.grpc_remote import OPTS, GrpcStage
from knit.stage import StageExecutor
from knit.wire import pack, unpack

MODEL = os.environ.get("KNIT_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
START, END = int(os.environ.get("KNIT_START", 0)), int(os.environ.get("KNIT_END", 8))
DEVICE = os.environ.get("KNIT_DEVICE", "cpu")
PORT = int(os.environ.get("KNIT_PORT", 9101))
NEXT = os.environ.get("KNIT_NEXT", "")
CODEC = os.environ.get("KNIT_CODEC", "none")
TTL = float(os.environ.get("KNIT_TTL", 300))


class StageService(pbg.StageServicer):
    def __init__(self, stage):
        self.stage, self.lock = stage, threading.Lock()
        self.next = GrpcStage(NEXT, CODEC) if NEXT else None

    def Info(self, req, ctx):
        s = self.stage
        return pb.InfoReply(model=MODEL, start=s.start, end=s.end, first=s.is_first,
                            last=s.is_last, device=DEVICE, sessions=len(s.sessions))

    def Reset(self, req, ctx):
        with self.lock:
            self.stage.reset(req.sid)
        if self.next:
            self.next.reset(req.sid)
        return pb.Ack(ok=True)

    def Rollback(self, req, ctx):
        with self.lock:
            self.stage.rollback(req.sid, req.pos)
        if self.next:
            self.next.rollback(req.sid, req.pos)
        return pb.Ack(ok=True)

    def Close(self, req, ctx):
        with self.lock:
            self.stage.drop(req.sid)
        if self.next:
            self.next.close(req.sid)
        return pb.Ack(ok=True)

    def Forward(self, req, ctx):
        x = unpack(req.data, req.dtype, list(req.shape))
        with self.lock:
            y = self.stage.forward(req.sid, x)
            ms = self.stage.last_compute_ms
        if self.next:
            y = self.next.forward(req.sid, y)       # compresses hidden states with CODEC
            ms += self.next.last_compute_ms
        raw, m = pack(y)                            # logits / already-decoded tensor: raw
        return pb.Tensor(sid=req.sid, dtype=m["dtype"], shape=m["shape"], data=raw, compute_ms=ms)


def main():
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32)
    stage = StageExecutor(model, START, END, DEVICE)
    del model

    def reaper(svc):
        while True:
            time.sleep(max(TTL / 4, 1))
            with svc.lock:
                stage.reap(TTL)

    svc = StageService(stage)
    threading.Thread(target=reaper, args=(svc,), daemon=True).start()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8), options=OPTS)
    pbg.add_StageServicer_to_server(svc, server)
    server.add_insecure_port(f"[::]:{PORT}")
    server.start()
    print(f"Knit gRPC stage [{START},{END}) on :{PORT}")
    server.wait_for_termination()


if __name__ == "__main__":
    main()