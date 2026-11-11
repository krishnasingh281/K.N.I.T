import collections
import csv

import matplotlib.pyplot as plt

rows = list(csv.DictReader(open("spec_results.csv")))
series = collections.defaultdict(list)
for r in rows:
    series[int(r["k"])].append((float(r["rtt_ms"]), float(r["tok_s"])))

plt.figure(figsize=(6, 4))
for k, pts in sorted(series.items()):
    pts.sort()
    x, y = zip(*pts)
    plt.plot(x, y, marker="o", linestyle="--" if k == 0 else "-",
             label="baseline (no spec)" if k == 0 else f"spec k={k}")
plt.xlabel("Injected RTT per hop (ms)")
plt.ylabel("Throughput (tokens/s)")
plt.title("Speculative decoding over a sharded pipeline")
plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
plt.savefig("spec_throughput.png", dpi=200)
print("saved spec_throughput.png")