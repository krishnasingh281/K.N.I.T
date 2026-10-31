"""Heterogeneity-aware layer assignment (v0: proportional, largest-remainder)."""
from typing import List, Tuple


def partition_layers(n_layers: int, capacities: List[float]) -> List[Tuple[int, int]]:
    """Split n_layers into contiguous [start, end) ranges proportional to capacity.

    `capacities` is any positive score per node (free VRAM in GB, measured
    tokens/s, ...). Every node gets at least one layer.
    """
    k = len(capacities)
    assert 0 < k <= n_layers, "need 1 <= nodes <= layers"
    total = float(sum(capacities))
    ideal = [c / total * n_layers for c in capacities]
    counts = [max(1, int(x)) for x in ideal]
    # fix rounding: hand out / take back layers by largest fractional remainder
    while sum(counts) < n_layers:
        i = max(range(k), key=lambda j: ideal[j] - counts[j])
        counts[i] += 1
    while sum(counts) > n_layers:
        i = max((j for j in range(k) if counts[j] > 1), key=lambda j: counts[j] - ideal[j])
        counts[i] -= 1
    ranges, s = [], 0
    for c in counts:
        ranges.append((s, s + c))
        s += c
    return ranges