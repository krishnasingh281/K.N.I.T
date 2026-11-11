"""Tensor frame: raw bytes + (dtype, shape). Codecs apply to floating tensors only.

  none : as-is            bf16 : 2 B/elem (fp32 range)
  fp16 : 2 B/elem (clamped to +-65504)
  int8 : 1 B/elem + one fp32 scale per token        (dtype tag "int8q")
  int8g: 1 B/elem + one fp32 scale per 64 channels  (dtype tag "int8g")
"""
import numpy as np
import torch

_DT = {"float32": torch.float32, "float16": torch.float16,
       "bfloat16": torch.bfloat16, "int64": torch.int64}
_FLOAT = (torch.float32, torch.float16, torch.bfloat16)
GROUP = 64


def _group(D: int) -> int:
    return GROUP if D % GROUP == 0 else D


def pack(t: torch.Tensor, codec: str = "none"):
    t = t.detach().cpu().contiguous()
    if codec != "none" and t.dtype in _FLOAT:
        if codec == "fp16":
            t = t.float().clamp(-65504, 65504).to(torch.float16)
        elif codec == "bf16":
            t = t.to(torch.bfloat16)
        elif codec == "int8":
            f = t.float()
            scale = f.abs().amax(dim=-1, keepdim=True).clamp(min=1e-8) / 127
            q = torch.round(f / scale).clamp(-127, 127).to(torch.int8)
            raw = scale.squeeze(-1).contiguous().numpy().tobytes() + q.numpy().tobytes()
            return raw, {"dtype": "int8q", "shape": list(t.shape)}
        elif codec == "int8g":
            f = t.float()
            D = f.shape[-1]
            G = _group(D)
            g = f.reshape(*f.shape[:-1], D // G, G)
            scale = g.abs().amax(dim=-1, keepdim=True).clamp(min=1e-8) / 127
            q = torch.round(g / scale).clamp(-127, 127).to(torch.int8)
            raw = scale.squeeze(-1).contiguous().numpy().tobytes() + q.numpy().tobytes()
            return raw, {"dtype": "int8g", "shape": list(t.shape)}
        else:
            raise ValueError(f"unknown codec {codec}")
    name = str(t.dtype).replace("torch.", "")
    raw = t.view(torch.int16).numpy().tobytes() if t.dtype == torch.bfloat16 else t.numpy().tobytes()
    return raw, {"dtype": name, "shape": list(t.shape)}


def unpack(raw: bytes, dtype: str, shape) -> torch.Tensor:
    shape = list(shape)
    if dtype == "int8q":
        n = int(np.prod(shape[:-1]))
        scale = torch.from_numpy(np.frombuffer(raw[:4 * n], dtype=np.float32).copy()).reshape(*shape[:-1], 1)
        q = torch.from_numpy(np.frombuffer(raw[4 * n:], dtype=np.int8).copy()).reshape(shape)
        return q.float() * scale
    if dtype == "int8g":
        D = shape[-1]
        G = _group(D)
        ng = D // G
        n = int(np.prod(shape[:-1])) * ng
        scale = torch.from_numpy(np.frombuffer(raw[:4 * n], dtype=np.float32).copy()).reshape(*shape[:-1], ng, 1)
        q = torch.from_numpy(np.frombuffer(raw[4 * n:], dtype=np.int8).copy()).reshape(*shape[:-1], ng, G)
        return (q.float() * scale).reshape(shape)
    dt = _DT[dtype]
    if dt == torch.bfloat16:
        return torch.from_numpy(np.frombuffer(raw, dtype=np.int16).copy()).view(torch.bfloat16).reshape(shape)
    npdt = {torch.float32: np.float32, torch.float16: np.float16, torch.int64: np.int64}[dt]
    return torch.from_numpy(np.frombuffer(raw, dtype=npdt).copy()).reshape(shape)