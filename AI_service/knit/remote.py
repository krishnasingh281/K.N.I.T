"""RemoteStage: same interface as StageExecutor, but talks to a stage_server over HTTP."""
import httpx
import torch

from .wire import pack, unpack


class RemoteStage:
    def __init__(self, url: str, codec: str = "none"):
        self.url, self.codec, self.last_compute_ms = url.rstrip("/"), codec, 0.0
        self.c = httpx.Client(timeout=httpx.Timeout(120, connect=1.0))
        self.info = self.c.get(f"{self.url}/info").json()

    def alive(self) -> bool:
        try:
            return httpx.get(f"{self.url}/info", timeout=httpx.Timeout(1.0, connect=0.5)).status_code == 200
        except httpx.HTTPError:
            return False

    def reset(self, sid):
        self.c.post(f"{self.url}/reset/{sid}").raise_for_status()

    def rollback(self, sid, pos):
        self.c.post(f"{self.url}/rollback/{sid}/{pos}").raise_for_status()

    def close(self, sid):
        self.c.delete(f"{self.url}/session/{sid}")

    def forward(self, sid, x: torch.Tensor):
        raw, m = pack(x, self.codec)
        r = self.c.post(f"{self.url}/forward/{sid}", content=raw, headers={
            "x-dtype": m["dtype"], "x-shape": ",".join(map(str, m["shape"]))})
        r.raise_for_status()
        self.last_compute_ms = float(r.headers["x-compute-ms"])
        return unpack(r.content, r.headers["x-dtype"], [int(v) for v in r.headers["x-shape"].split(",")])