"""StageExecutor: runs decoder layers [start, end) of a Llama/Qwen2-style HF model.

First stage  : input_ids  -> hidden_states
Middle stage : hidden     -> hidden
Last stage   : hidden     -> logits
Each session keeps its own KV cache, so stages are stateful per request.
"""
import inspect
import time
from dataclasses import dataclass, field
from typing import Dict

import torch
from transformers import DynamicCache


@dataclass
class Session:
    cache: DynamicCache = field(default_factory=DynamicCache)
    pos: int = 0  # number of tokens already processed by this stage


class StageExecutor:
    def __init__(self, model, start: int, end: int, device: str = "cpu"):
        inner = model.model
        n = len(inner.layers)
        assert 0 <= start < end <= n
        self.start, self.end, self.n_layers = start, end, n
        self.is_first, self.is_last = start == 0, end == n
        self.device = torch.device(device)

        self.embed = inner.embed_tokens.to(self.device) if self.is_first else None
        self.layers = torch.nn.ModuleList(list(inner.layers[start:end])).to(self.device)
        self.rotary = inner.rotary_emb.to(self.device)
        self.norm = inner.norm.to(self.device) if self.is_last else None
        self.lm_head = model.lm_head.to(self.device) if self.is_last else None

        # Re-index layers locally so this stage's KV cache is compact (0..k-1).
        for i, layer in enumerate(self.layers):
            layer.self_attn.layer_idx = i
            if hasattr(layer, "layer_idx"):
                layer.layer_idx = i
        params = inspect.signature(self.layers[0].forward).parameters
        self._cache_kw = "past_key_values" if "past_key_values" in params else "past_key_value"
        self.sessions: Dict[str, Session] = {}
        self.last_compute_ms = 0.0

    # ---- session management -------------------------------------------------
    def reset(self, sid: str):
        self.sessions[sid] = Session()

    def rollback(self, sid: str, new_pos: int):
        """Drop KV entries past new_pos (used when speculative tokens are rejected)."""
        s = self.sessions[sid]
        if new_pos < s.pos:
            s.cache.crop(new_pos)
            s.pos = new_pos

    # ---- forward ------------------------------------------------------------
    @torch.inference_mode()
    def forward(self, sid: str, x: torch.Tensor) -> torch.Tensor:
        t0 = time.perf_counter()
        s = self.sessions.setdefault(sid, Session())
        x = x.to(self.device)
        h = self.embed(x) if self.is_first else x
        T, pos = h.shape[1], s.pos

        position_ids = torch.arange(pos, pos + T, device=self.device).unsqueeze(0)
        cache_position = torch.arange(pos, pos + T, device=self.device)
        # additive causal mask [1,1,T,pos+T]; new tokens see all past + causal among themselves
        mask = torch.full((T, pos + T), float("-inf"), device=self.device, dtype=h.dtype)
        mask = torch.triu(mask, diagonal=pos + 1).unsqueeze(0).unsqueeze(0)
        pe = self.rotary(h, position_ids)

        for layer in self.layers:
            out = layer(
                h,
                attention_mask=mask,
                position_ids=position_ids,
                use_cache=True,
                cache_position=cache_position,
                position_embeddings=pe,
                **{self._cache_kw: s.cache},
            )
            h = out[0] if isinstance(out, tuple) else out
        s.pos += T

        if self.is_last:
            h = self.lm_head(self.norm(h))
        if self.device.type == "cuda":
            torch.cuda.synchronize()
        self.last_compute_ms = (time.perf_counter() - t0) * 1000
        return h