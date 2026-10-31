"""RemoteStage: same interface as StageExecutor, but talks to a stage_server over HTTP."""
import httpx
import torch

from .wire import pack, unpack


class RemoteStage:
    def __init__(self, url: str):
        self.url, self.last_compute_ms = url.rstrip("/"), 0.0
        self.c = httpx.Client(timeout=120)
        self.info = self.c.get(f"{self.url}/info").json()

    def reset(self, sid):
        self.c.post(f"{self.url}/reset/{sid}")

    def forward(self, sid, x: torch.Tensor):
        raw, m = pack(x)
        r = self.c.post(f"{self.url}/forward/{sid}", content=raw, headers={
            "x-dtype": m["dtype"], "x-shape": ",".join(map(str, m["shape"]))})
        r.raise_for_status()
        self.last_compute_ms = float(r.headers["x-compute-ms"])
        return unpack(r.content, r.headers["x-dtype"], [int(v) for v in r.headers["x-shape"].split(",")])