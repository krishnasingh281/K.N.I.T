"""ResilientPipeline: survive a stage crash via standby + prefix replay (star topology)."""
import time

import httpx
import torch

from .pipeline import Pipeline
from .remote import RemoteStage

_ERRS = (httpx.TransportError, httpx.HTTPStatusError)


class ResilientPipeline(Pipeline):
    def __init__(self, stages, standbys, **kw):
        """standbys: {stage_index: [url, ...]} with the same layer range as that stage."""
        super().__init__(stages, **kw)
        self.standbys = {i: list(v) for i, v in standbys.items()}
        self.hist = {}            # sid -> token ids currently held in every stage's KV cache
        self.recoveries = []      # (sid, seconds, tokens_replayed)

    def _guard(self, sid, fn):
        for _ in range(len(self.stages) + 2):
            try:
                return fn()
            except _ERRS:
                self._recover(sid)
        raise RuntimeError("recovery failed")

    def _recover(self, sid):
        t0 = time.perf_counter()
        dead = [i for i, st in enumerate(self.stages) if not st.alive()]
        t_detect = time.perf_counter()
        for i in dead:
            if not self.standbys.get(i):
                raise RuntimeError(f"stage {i} is down and has no standby")
            self.stages[i] = RemoteStage(self.standbys[i].pop(0), codec=self.stages[i].codec)
        t_swap = time.perf_counter()
        for st in self.stages:
            st.reset(sid)
        h = self.hist.get(sid, [])
        if h:
            Pipeline.forward(self, sid, torch.tensor([h]))      # replay prefix
        t_end = time.perf_counter()
        self.recoveries.append({"sid": sid, "tokens": len(h),
                                "detect_ms": (t_detect - t0) * 1e3,
                                "swap_ms": (t_swap - t_detect) * 1e3,
                                "replay_ms": (t_end - t_swap) * 1e3,
                                "total_ms": (t_end - t0) * 1e3})

    def reset(self, sid):
        self.hist[sid] = []
        self._guard(sid, lambda: Pipeline.reset(self, sid))

    def forward(self, sid, x):
        out = self._guard(sid, lambda: Pipeline.forward(self, sid, x))
        self.hist.setdefault(sid, []).extend(x[0].tolist())
        return out

    def rollback(self, sid, pos):
        self._guard(sid, lambda: Pipeline.rollback(self, sid, pos))
        self.hist[sid] = self.hist.get(sid, [])[:pos]