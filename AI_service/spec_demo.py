"""Speculative decoding over a layer-sharded pipeline.

  python spec_demo.py
  python spec_demo.py --remote http://localhost:9001 --rtts 0   # chained servers (step 5)
"""
import argparse
import csv
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from knit.partition import partition_layers
from knit.pipeline import Pipeline
from knit.remote import RemoteStage
from knit.stage import StageExecutor

ap = argparse.ArgumentParser()
ap.add_argument("--target", default="Qwen/Qwen2.5-1.5B-Instruct")
ap.add_argument("--draft", default="Qwen/Qwen2.5-0.5B-Instruct")
ap.add_argument("--capacities", type=float, nargs="+", default=[1, 1, 1])
ap.add_argument("--ks", type=int, nargs="+", default=[1, 2, 4, 8])
ap.add_argument("--rtts", type=float, nargs="+", default=[0, 20, 50, 80])
ap.add_argument("--max-new", type=int, default=48)
ap.add_argument("--codec", default="none", choices=["none", "bf16", "fp16", "int8", "int8g"])
ap.add_argument("--remote", nargs="*")
ap.add_argument("--out", default="spec_results.csv")
ap.add_argument("--prompts", nargs="+", default=[
    "Explain pipeline parallelism in two sentences.",
    "Write a Python function that reverses a linked list.",
    "List three benefits of decentralized computing."])
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.target)
eos = tok.eos_token_id
draft = AutoModelForCausalLM.from_pretrained(a.draft, torch_dtype=torch.float32).eval()

if a.remote:
    stages = [RemoteStage(u, codec=a.codec) for u in a.remote]
    pipe_codec = "none"
else:
    target = AutoModelForCausalLM.from_pretrained(a.target, torch_dtype=torch.float32).eval()
    ranges = partition_layers(len(target.model.layers), a.capacities)
    print("layer ranges:", ranges)
    stages = [StageExecutor(target, s, e) for s, e in ranges]
    pipe_codec = a.codec


def enc(p):
    text = tok.apply_chat_template([{"role": "user", "content": p}],
                                   tokenize=False, add_generation_prompt=True)
    return tok(text, return_tensors="pt").input_ids


prompts = [enc(p) for p in a.prompts]


def trunc(t):
    return t[:t.index(eos) + 1] if eos in t else t


def run(rtt, k):
    """k == 0 -> plain greedy baseline."""
    p = Pipeline(stages, rtt_ms=rtt, codec=pipe_codec)
    outs, passes, acc, prop = [], 0, 0, 0
    t0 = time.perf_counter()
    for i, ids in enumerate(prompts):
        sid = f"s{i}-{rtt}-{k}"
        if k == 0:
            o = p.generate(sid, ids, a.max_new, eos)
            passes += len(o)
        else:
            o, st = p.generate_spec(sid, ids, draft, k=k, max_new=a.max_new, eos_id=eos)
            passes += st["passes"]; acc += st["accepted"]; prop += st["proposed"]
        outs.append(trunc(o))
    dt = time.perf_counter() - t0
    n_tok = sum(len(o) for o in outs)
    return outs, {"tok_s": n_tok / dt, "tok_per_pass": n_tok / passes,
                  "accept": acc / prop if prop else 0.0, "hops": p.stats["hops"],
                  "kb": p.stats["bytes"] / 1024}


rows = []
print(f"{'rtt':>5} {'k':>3} {'tok/s':>8} {'speedup':>8} {'accept':>7} {'tok/pass':>9}")
for rtt in a.rtts:
    base_out, base = run(rtt, 0)
    rows.append({"rtt_ms": rtt, "k": 0, **base, "speedup": 1.0})
    print(f"{rtt:>5.0f} {0:>3} {base['tok_s']:>8.2f} {1.0:>8.2f} {'-':>7} {base['tok_per_pass']:>9.2f}")
    for k in a.ks:
        out, m = run(rtt, k)
        ok = out == base_out
        sp = m["tok_s"] / base["tok_s"]
        rows.append({"rtt_ms": rtt, "k": k, **m, "speedup": sp})
        print(f"{rtt:>5.0f} {k:>3} {m['tok_s']:>8.2f} {sp:>8.2f} {m['accept']:>7.2f} "
              f"{m['tok_per_pass']:>9.2f}" + ("" if ok else "   <-- OUTPUT MISMATCH"))

with open(a.out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("saved", a.out)