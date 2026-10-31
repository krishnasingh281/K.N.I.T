"""Knit AI demo: layer-sliced pipeline == monolithic model, plus latency study.

  python demo.py                                  # 3 equal local stages
  python demo.py --capacities 8 4 2 --rtts 0 20 50 80
  python demo.py --remote http://localhost:9001 http://localhost:9002 http://localhost:9003
"""
import argparse
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from knit.partition import partition_layers
from knit.pipeline import Pipeline
from knit.remote import RemoteStage
from knit.stage import StageExecutor

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
ap.add_argument("--capacities", type=float, nargs="+", default=[1, 1, 1])
ap.add_argument("--rtts", type=float, nargs="+", default=[0, 20, 50])
ap.add_argument("--prompt", default="Explain pipeline parallelism in one sentence.")
ap.add_argument("--max-new", type=int, default=24)
ap.add_argument("--remote", nargs="*")
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float32).eval()
n = len(model.model.layers)
ids = tok(a.prompt, return_tensors="pt").input_ids

print(f"\n=== Knit AI demo | {a.model} | {n} layers ===")
if a.remote:
    stages = [RemoteStage(u) for u in a.remote]
    for s in stages:
        print(f"  remote {s.url}: layers [{s.info['start']}, {s.info['end']})")
else:
    ranges = partition_layers(n, a.capacities)
    print("capacities:", a.capacities, "-> layer ranges:", ranges)
    stages = [StageExecutor(model, s, e) for s, e in ranges]
    # NOTE: stage executors now share layer objects with `model`; re-load for baseline.
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float32).eval()

# 1) Correctness: logits from the pipeline vs the full model
with torch.inference_mode():
    ref = model(ids).logits
pipe = Pipeline(stages)
pipe.reset("check")
got = pipe.forward("check", ids)
print(f"\n[1] logits max|diff| = {(ref - got).abs().max():.2e}  "
      f"argmax match = {bool((ref.argmax(-1) == got.argmax(-1)).all())}")

# 2) Correctness: greedy generation, token-for-token
with torch.inference_mode():
    ref_tokens = model.generate(ids, max_new_tokens=a.max_new, do_sample=False)[0, ids.shape[1]:].tolist()
t0 = time.perf_counter()
pipe_tokens = Pipeline(stages).generate("g", ids, a.max_new)
n_cmp = min(len(ref_tokens), len(pipe_tokens))
print(f"[2] generation identical to monolithic: {ref_tokens[:n_cmp] == pipe_tokens[:n_cmp]}")
print("    output:", tok.decode(pipe_tokens, skip_special_tokens=True).strip())

# 3) Throughput vs simulated WAN RTT
print("\n[3] tokens/s vs injected RTT (per hop)")
print(f"{'RTT ms':>8} {'tok/s':>8} {'hops':>6} {'KB moved':>10} {'net ms':>9} " + " ".join(f"st{i}_ms" for i in range(len(stages))))
for rtt in a.rtts:
    p = Pipeline(stages, rtt_ms=rtt)
    t0 = time.perf_counter()
    toks = p.generate(f"r{rtt}", ids, a.max_new)
    dt = time.perf_counter() - t0
    print(f"{rtt:>8.0f} {len(toks)/dt:>8.2f} {p.stats['hops']:>6} {p.stats['bytes']/1024:>10.1f} "
          f"{p.stats['net_ms']:>9.0f} " + " ".join(f"{c:>6.0f}" for c in p.stats["compute_ms"]))