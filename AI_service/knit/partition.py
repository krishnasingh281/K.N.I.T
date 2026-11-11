"""Heterogeneity-aware layer assignment (v0: proportional, largest-remainder)."""
from typing import List, Tuple

def partition_layers(n_layers: int, capacities: List[float]) -> List[Tuple[int, int]]:
    k = len(capacities)
    assert 0 < k <= n_layers, "need 1 <= nodes <= layers"
    total = float(sum(capacities))
    ideal = [c / total * n_layers for c in capacities]
    counts = [max(1, int(x)) for x in ideal]
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


def partition_bottleneck(n_layers, capacities, first_extra=0.0, last_extra=2.0):
    """Contiguous split minimizing the slowest stage's time = (layers + extras) / capacity.

    first_extra / last_extra: cost of embedding / (final norm + lm_head) in
    'layer equivalents'. Measure them once (time one layer vs the lm_head) and
    plug in; for Qwen's 150k vocab, last_extra is several layers.
    Returns (ranges, bottleneck_time).
    """
    k, INF = len(capacities), float("inf")
    assert 0 < k <= n_layers
    dp = [[INF] * (n_layers + 1) for _ in range(k + 1)]
    cut = [[0] * (n_layers + 1) for _ in range(k + 1)]
    dp[0][0] = 0.0
    for i in range(1, k + 1):
        extra = (first_extra if i == 1 else 0.0) + (last_extra if i == k else 0.0)
        for j in range(i, n_layers + 1):
            for m in range(i - 1, j):
                if dp[i - 1][m] == INF:
                    continue
                v = max(dp[i - 1][m], (j - m + extra) / capacities[i - 1])
                if v < dp[i][j]:
                    dp[i][j], cut[i][j] = v, m
    ranges, j = [], n_layers
    for i in range(k, 0, -1):
        m = cut[i][j]; ranges.append((m, j)); j = m
    return ranges[::-1], dp[k][n_layers]