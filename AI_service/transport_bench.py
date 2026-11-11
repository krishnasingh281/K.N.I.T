"""python transport_bench.py --http http://localhost:9001 http://localhost:9002 http://localhost:9003 \
                            --grpc localhost:9101 localhost:9102 localhost:9103"""
import argparse
import time

from transformers import AutoTokenizer

from knit.grpc_remote import GrpcStage
from knit.pipeline import Pipeline
from knit.remote import RemoteStage

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
ap.add_argument("--http", nargs="+", required=True)
ap.add_argument("--grpc", nargs="+", required=True)
ap.add_argument("--codec", default="none")
ap.add_argument("--max-new", type=int, default=64)
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.model)
ids = tok("Explain pipeline parallelism in one sentence.", return_tensors="pt").input_ids

for name, stages in [("http", [RemoteStage(u, a.codec) for u in a.http]),
                     ("grpc", [GrpcStage(t, a.codec) for t in a.grpc])]:
    Pipeline(stages).generate("warm", ids, 4)                       # warm-up
    runs = []
    for r in range(3):
        t0 = time.perf_counter()
        out = Pipeline(stages).generate(f"b{r}", ids, a.max_new)
        runs.append(len(out) / (time.perf_counter() - t0))
    print(f"{name}: {sum(runs)/len(runs):.2f} tok/s (mean of 3)   "
          f"token-ids head: {out[:6]}")