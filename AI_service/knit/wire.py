"""Minimal tensor frame: raw bytes + (dtype, shape) metadata. Replaced by gRPC later."""
import numpy as np
import torch

_DT = {"float32": torch.float32, "float16": torch.float16,
       "bfloat16": torch.bfloat16, "int64": torch.int64}


def pack(t: torch.Tensor):
    t = t.detach().cpu().contiguous()
    name = str(t.dtype).replace("torch.", "")
    raw = t.view(torch.int16).numpy().tobytes() if t.dtype == torch.bfloat16 else t.numpy().tobytes()
    return raw, {"dtype": name, "shape": list(t.shape)}


def unpack(raw: bytes, dtype: str, shape) -> torch.Tensor:
    dt = _DT[dtype]
    if dt == torch.bfloat16:
        return torch.from_numpy(np.frombuffer(raw, dtype=np.int16).copy()).view(torch.bfloat16).reshape(shape)
    npdt = {torch.float32: np.float32, torch.float16: np.float16, torch.int64: np.int64}[dt]
    return torch.from_numpy(np.frombuffer(raw, dtype=npdt).copy()).reshape(shape)