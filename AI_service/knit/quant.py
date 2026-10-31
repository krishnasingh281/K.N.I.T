import itertools

import torch
import torch.nn as nn
import torch.nn.functional as F


class Int8Linear(nn.Module):
    """Linear layer with int8 weights and one fp scale per output row."""

    def __init__(self, lin: nn.Linear):
        super().__init__()
        w = lin.weight.data
        scale = w.abs().amax(dim=1, keepdim=True).clamp(min=1e-8) / 127
        self.register_buffer("qw", torch.round(w / scale).to(torch.int8))
        self.register_buffer("scale", scale)
        self.bias = lin.bias

    def forward(self, x):
        return F.linear(x, self.qw.to(x.dtype) * self.scale, self.bias)


def quantize_int8(module: nn.Module):
    """Replace every nn.Linear inside `module` with Int8Linear, in place."""
    for name, child in module.named_children():
        if isinstance(child, nn.Linear):
            setattr(module, name, Int8Linear(child))
        else:
            quantize_int8(child)


def mem_mb(module: nn.Module) -> float:
    """Total parameter + buffer memory in MB."""
    tensors = itertools.chain(module.parameters(), module.buffers())
    return sum(t.numel() * t.element_size() for t in tensors) / 2**20