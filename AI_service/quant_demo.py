import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from transformers import AutoModelForCausalLM, AutoTokenizer

from knit.partition import partition_layers
from knit.pipeline import Pipeline
from knit.stage import StageExecutor
from knit.quant import quantize_int8, mem_mb

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
tok = AutoTokenizer.from_pretrained(MODEL)
ids = tok("Explain pipeline parallelism in one sentence.", return_tensors="pt").input_ids

def build():
    m = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()
    n = len(m.model.layers)
    return m, [StageExecutor(m, s, e) for s, e in partition_layers(n, [1, 1, 1])]

# --- fp32 baseline ---
m1, stages = build()
fp32_mem = [mem_mb(s.layers) for s in stages]
pipe = Pipeline(stages); pipe.reset("a")
ref = pipe.forward("a", ids)

# --- int8 (fresh copy, quantized in place) ---
m2, stages2 = build()
for s in stages2:
    quantize_int8(s.layers)
int8_mem = [mem_mb(s.layers) for s in stages2]
pipe2 = Pipeline(stages2); pipe2.reset("b")
out = pipe2.forward("b", ids)

print("\nStage | fp32 MB | int8 MB | saving")
for i, (a, b) in enumerate(zip(fp32_mem, int8_mem)):
    print(f"  {i}   | {a:7.1f} | {b:7.1f} | {a/b:.1f}x")
print(f"\nlogit max|diff| vs fp32: {(ref - out).abs().max():.3f}")
print("same next token:", int(ref[0, -1].argmax()) == int(out[0, -1].argmax()))

# --- bar chart ---
x = range(len(stages))
plt.figure(figsize=(7, 4))
plt.bar([i - 0.2 for i in x], fp32_mem, 0.4, label="fp32")
plt.bar([i + 0.2 for i in x], int8_mem, 0.4, label="int8")
plt.xticks(list(x), [f"Stage {i}" for i in x])
plt.ylabel("Memory (MB)"); plt.title("Memory per stage"); plt.legend()
plt.tight_layout(); plt.savefig("quant_memory.png", dpi=150)
print("saved quant_memory.png")