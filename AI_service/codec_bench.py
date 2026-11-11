"""Wire-codec ablation: bytes moved vs output fidelity."""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from knit.partition import partition_layers
from knit.pipeline import Pipeline
from knit.stage import StageExecutor

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
PROMPTS = ["Explain pipeline parallelism in two sentences.",
           "Write a Python function that reverses a linked list.",
           "Why is the sky blue?"]
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()
stages = [StageExecutor(model, s, e) for s, e in partition_layers(len(model.model.layers), [1, 1, 1])]
ids = [tok(p, return_tensors="pt").input_ids for p in PROMPTS]

ref_logits, ref_tokens = {}, {}
print(f"{'codec':>6} {'KB/gen':>9} {'max|dlogit|':>12} {'top1 agree':>11} {'gen match':>10}")
for codec in ["none", "bf16", "fp16", "int8", "int8g"]:
    agree, dmax, match, kb = [], 0.0, 0, 0.0
    for i, x in enumerate(ids):
        p = Pipeline(stages, codec=codec)
        p.reset("c"); lg = p.forward("c", x)
        toks = Pipeline(stages, codec=codec)
        out = toks.generate("g", x, 32)
        kb += toks.stats["bytes"] / 1024
        if codec == "none":
            ref_logits[i], ref_tokens[i] = lg, out
        dmax = max(dmax, (lg - ref_logits[i]).abs().max().item())
        agree.append((lg.argmax(-1) == ref_logits[i].argmax(-1)).float().mean().item())
        n = min(len(out), len(ref_tokens[i])); match += int(out[:n] == ref_tokens[i][:n])
    print(f"{codec:>6} {kb/len(ids):>9.1f} {dmax:>12.3e} {sum(agree)/len(agree):>11.3f} {match}/{len(ids)}")