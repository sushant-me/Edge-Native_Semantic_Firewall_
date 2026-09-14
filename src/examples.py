#!/usr/bin/env python3
"""
Extract qualitative failure examples for the paper.

Pulls concrete traces that illustrate the dominant error modes, so the
results section can quote real model output rather than describe failure
in the abstract.

Usage:
    python src/examples.py --results results/results_p1.jsonl --corpus data/corpus.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/results_p1.jsonl")
    ap.add_argument("--corpus", default="data/corpus.jsonl")
    args = ap.parse_args()

    recs = load(args.results)
    corpus = {s["id"]: s for s in load(args.corpus)}

    print(f"loaded {len(recs)} records\n")

    # ---- 1. Rule A -> ACCEPT, the critical failure -------------------------
    print("=" * 78)
    print("CRITICAL: expected DENY, model returned ACCEPT")
    print("=" * 78)
    for cond in ("cot", "zeroshot", "naive"):
        bad = [r for r in recs if r["condition"] == cond
               and r["expected_decision"] == "DENY" and r.get("decision") == "ACCEPT"]
        print(f"\n--- {cond}: {len(bad)} cases ---")
        for r in bad[:6]:
            s = corpus[r["id"]]
            print(f"  {r['id']} rule={r['matched_rule']} conf={r['confidence_score']} "
                  f"tag={r['tag']} tech={r.get('injection_technique')}")
            print(f"     action: {s['proposed_action'][:110]}")
            try:
                obj = json.loads(r["raw"])
                rs = (obj.get("reasoning") or "")[:260].replace("\n", " ")
                if rs:
                    print(f"     reasoning: {rs}")
            except Exception:
                print(f"     raw: {r['raw'][:200]!r}")

    # ---- 2. Rule misattribution map ---------------------------------------
    print("\n" + "=" * 78)
    print("RULE ATTRIBUTION: true rule -> predicted rule")
    print("=" * 78)
    for cond in ("cot", "zeroshot"):
        c = Counter()
        for r in recs:
            if r["condition"] != cond or not r.get("matched_rule"):
                continue
            c[f"{r['rule']}->{r['matched_rule']}"] += 1
        tot = sum(c.values())
        print(f"\n--- {cond} (n={tot}) ---")
        for k, v in sorted(c.items()):
            mark = "  <== critical" if k == "A->C" else ""
            print(f"  {k}: {v:4d}  ({100*v/tot:5.1f}%){mark}")

    # ---- 3. Adversarial technique x outcome ------------------------------
    print("\n" + "=" * 78)
    print("ADVERSARIAL: outcome by technique (structured CoT)")
    print("=" * 78)
    by_tech = defaultdict(Counter)
    for r in recs:
        if r["condition"] != "cot" or r["tag"] != "adversarial":
            continue
        by_tech[r.get("injection_technique") or "?"][r.get("decision")] += 1
    print(f"{'technique':28s} {'n':>4s}  ACCEPT DENY FLAG   unsafe-ACCEPT")
    for t in sorted(by_tech):
        c = by_tech[t]
        n = sum(c.values())
        print(f"{t:28s} {n:4d}  {c['ACCEPT']:6d} {c['DENY']:4d} {c['FLAG']:4d}   {c['ACCEPT']}")

    # ---- 4. Free-form structural failures --------------------------------
    print("\n" + "=" * 78)
    print("FREE-FORM: structural failure examples")
    print("=" * 78)
    noparse = [r for r in recs if r["condition"] == "naive" and not r.get("parse_ok")]
    ambig = [r for r in recs if r["condition"] == "naive" and r.get("ambiguous")]
    print(f"unparseable: {len(noparse)}   ambiguous: {len(ambig)}")
    for r in ambig[:3]:
        print(f"\n  {r['id']} distinct verdicts mentioned together:")
        print(f"     {r['raw'][:300]!r}")

    # ---- 5. Confidence distribution --------------------------------------
    print("\n" + "=" * 78)
    print("CONFIDENCE SCORES (structured CoT), by whether the rule was right")
    print("=" * 78)
    for label, want in (("rule correct", True), ("rule WRONG", False)):
        vals = [r["confidence_score"] for r in recs
                if r["condition"] == "cot" and r.get("rule_correct") is want
                and r.get("confidence_score") is not None]
        if vals:
            vals.sort()
            print(f"  {label:14s} n={len(vals):4d}  median={vals[len(vals)//2]:3d}  "
                  f"min={vals[0]}  max={vals[-1]}  "
                  f">=95: {sum(1 for v in vals if v >= 95)}  "
                  f">=80: {sum(1 for v in vals if v >= 80)}")


if __name__ == "__main__":
    main()
