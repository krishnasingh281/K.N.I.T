"""Pipeline driver. Stages can be local StageExecutors or RemoteStage proxies."""
import time
from typing import List

import torch


class Pipeline:
    def __init__(self, stages: List, rtt_ms: float = 0.0):
        self.stages, self.rtt_ms = stages, rtt_ms
        self.stats = {"hops": 0, "bytes": 0, "net_ms": 0.0, "compute_ms": [0.0] * len(stages)}

    def _hop(self, t: torch.Tensor):
        """Simulate one network hop (one-way = rtt/2) and count bytes."""
        self.stats["hops"] += 1
        self.stats["bytes"] += t.numel() * t.element_size()
        if self.rtt_ms > 0:
            time.sleep(self.rtt_ms / 2000.0)
            self.stats["net_ms"] += self.rtt_ms / 2

    def forward(self, sid: str, input_ids: torch.Tensor) -> torch.Tensor:
        x = input_ids
        for i, st in enumerate(self.stages):
            if i > 0:
                self._hop(x)
            x = st.forward(sid, x)
            self.stats["compute_ms"][i] += getattr(st, "last_compute_ms", 0.0)
        return x  # logits [1, T, V]

    def reset(self, sid: str):
        for st in self.stages:
            st.reset(sid)

    @torch.inference_mode()
    def generate(self, sid: str, prompt_ids: torch.Tensor, max_new: int = 32, eos_id=None):
        self.reset(sid)
        logits = self.forward(sid, prompt_ids)
        out = []
        for _ in range(max_new):
            nxt = int(logits[0, -1].argmax())
            out.append(nxt)
            if eos_id is not None and nxt == eos_id:
                break
            logits = self.forward(sid, torch.tensor([[nxt]]))
        return out