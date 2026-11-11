"""Pipeline driver. Stages can be local StageExecutors or RemoteStage proxies."""
import time
from typing import List

import torch

from .wire import pack, unpack


class Pipeline:
    def __init__(self, stages: List, rtt_ms: float = 0.0, codec: str = "none"):
        self.stages, self.rtt_ms, self.codec = stages, rtt_ms, codec
        self.stats = {"hops": 0, "bytes": 0, "net_ms": 0.0, "compute_ms": [0.0] * len(stages)}

    def _hop(self, t: torch.Tensor):
        """Simulate one hop: codec round-trip, byte count, one-way delay."""
        self.stats["hops"] += 1
        if self.codec != "none":
            raw, m = pack(t, self.codec)
            self.stats["bytes"] += len(raw)
            t = unpack(raw, m["dtype"], m["shape"])
        else:
            self.stats["bytes"] += t.numel() * t.element_size()
        if self.rtt_ms > 0:
            time.sleep(self.rtt_ms / 2000.0)
            self.stats["net_ms"] += self.rtt_ms / 2
        return t

    def forward(self, sid: str, input_ids: torch.Tensor) -> torch.Tensor:
        x = input_ids
        for i, st in enumerate(self.stages):
            if i > 0:
                x = self._hop(x)
            x = st.forward(sid, x)
            self.stats["compute_ms"][i] += getattr(st, "last_compute_ms", 0.0)
        return x  # logits [1, T, V]

    def reset(self, sid: str):
        for st in self.stages:
            st.reset(sid)

    def rollback(self, sid: str, pos: int):
        for st in self.stages:
            st.rollback(sid, pos)

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

    @torch.inference_mode()
    def generate_spec(self, sid, prompt_ids, draft, k=4, max_new=32, eos_id=None):
        """draft: small HF causal LM with the same tokenizer, run locally."""
        self.reset(sid)
        logits = self.forward(sid, prompt_ids)
        out = [int(logits[0, -1].argmax())]
        P = prompt_ids.shape[1]
        stats = {"passes": 1, "accepted": 0, "proposed": 0}
        while len(out) < max_new and (eos_id is None or out[-1] != eos_id):
            seq = torch.cat([prompt_ids, torch.tensor([out])], dim=1)
            d = draft.generate(seq, attention_mask=torch.ones_like(seq),
                               max_new_tokens=k, do_sample=False)[0, seq.shape[1]:].tolist()
            # target cache holds P+len(out)-1 tokens; feed last committed + drafts
            ver = torch.tensor([[out[-1]] + d])
            t = self.forward(sid, ver)[0].argmax(-1).tolist()   # len(d)+1 predictions
            n = 0
            while n < len(d) and d[n] == t[n]:
                n += 1
            out += d[:n] + [t[n]]                               # accepted + bonus token
            self.rollback(sid, P + len(out) - 1)                # drop rejected KV
            stats["passes"] += 1
            stats["accepted"] += n
            stats["proposed"] += len(d)
        return out[:max_new], stats