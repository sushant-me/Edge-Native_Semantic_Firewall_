#!/usr/bin/env python3
"""
Run-to-run agreement between two evaluation passes over the same scenarios.

The model is sampled greedily (temperature 0, top-k 1), so any disagreement
between two passes is attributable to floating-point non-determinism in the
GPU kernels rather than to sampling.  This script quantifies it, which is what
lets the paper report a single-pass accuracy honestly.

Usage:
    python src/variance.py --a results/results_p1.jsonl --b results/results_p2.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="results/results_p1.jsonl")
    ap.add_argument("--b", default="results/results_p2.jsonl")
    args = ap.parse_args()

    A = {(r["id"], r["condition"]): r for r in load(args.a) if "error" not in r}
    B = {(r["id"], r["condition"]): r for r in load(args.b) if "error" not in r}
    keys = sorted(set(A) & set(B))
    print(f"overlapping (scenario, condition) pairs: {len(keys)}\n")

    by_cond = defaultdict(list)
    for k in keys:
        by_cond[k[1]].append(k)

    print(f"{'condition':10s} {'n':>5s} {'decision agree':>15s} {'rule agree':>12s} "
          f"{'both correct':>13s} {'A only':>7s} {'B only':>7s}")
    overall = []
    for cond in sorted(by_cond):
        ks = by_cond[cond]
        d_agree = sum(1 for k in ks if A[k].get("decision") == B[k].get("decision"))
        r_agree = sum(1 for k in ks if A[k].get("matched_rule") == B[k].get("matched_rule"))
        both = sum(1 for k in ks if A[k].get("correct") and B[k].get("correct"))
        a_only = sum(1 for k in ks if A[k].get("correct") and not B[k].get("correct"))
        b_only = sum(1 for k in ks if B[k].get("correct") and not A[k].get("correct"))
        n = len(ks)
        overall += [A[k] for k in ks]
        print(f"{cond:10s} {n:5d} {100*d_agree/n:14.1f}% {100*r_agree/n:11.1f}% "
              f"{100*both/n:12.1f}% {a_only:7d} {b_only:7d}")

    if overall:
        acc_a = 100 * sum(1 for r in overall if r.get("correct")) / len(overall)
        print(f"\npooled pass-1 accuracy on the overlap: {acc_a:.1f}%")

    # flip examples, most interesting first
    print("\nDisagreements where both stayed parseable and the verdict changed:")
    shown = 0
    for k in keys:
        a, b = A[k], B[k]
        if a.get("decision") and b.get("decision") and a["decision"] != b["decision"]:
            print(f"  {k[0]} {k[1]:9s} true={a['rule']} expected={a['expected_decision']:6s} "
                  f"pass1={a['decision']:6s}(rule {a.get('matched_rule')}) "
                  f"pass2={b['decision']:6s}(rule {b.get('matched_rule')})")
            shown += 1
            if shown >= 12:
                break


if __name__ == "__main__":
    main()
