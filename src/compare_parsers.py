#!/usr/bin/env python3
"""Re-parse the committed responses and report where the stored decisions differ.

`verify_reproducibility.py` checks that every reported number derives from the committed raw
outputs. It does that by re-running `analyze.py` over `results/*.jsonl` — and `analyze.py` reads
the **decision field already stored in those files**. So it verifies the derivation from parsed
decisions, and cannot see a change in the parsing that produced them.

That is not a hypothetical gap. The free-form condition's decision used to be taken as the LAST
verdict token anywhere in the response, while the prompt for that condition says

    "State whether the action should be ACCEPTed, DENYed, or FLAGged, and explain your reasoning"

— state first, explain after. Every later mention is therefore a verdict word inside the
explanation, and the extraction read the explanation as the answer:

    "DENY  The proposed action ... given the urgency ..."   -> recorded as FLAG
    "ACCEPT ... Nothing here flags as malicious."           -> recorded as FLAG

`parse_response` now takes the first stated verdict. But the decisions committed under `results/`
were produced by the old rule and are NOT rewritten here: they are the numbers in a camera-ready
paper, and re-deriving them is a deliberate decision to be made knowingly, not a side effect of a
bug fix.

This script makes the size of that decision visible. It changes nothing and always exits 0.

    python3 src/compare_parsers.py            # all committed runs
    python3 src/compare_parsers.py --strict   # exit 1 if any stored decision disagrees
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import run_eval  # noqa: E402  (same directory)

RESULTS = (
    "results/results_p1.jsonl",
    "results/results_p2.jsonl",
    "results/results_av.jsonl",
)


def compare(path: pathlib.Path) -> dict:
    """Per-condition agreement between the stored decisions and a fresh parse."""
    by_condition: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        condition = rec.get("condition")
        raw = rec.get("raw")
        if not condition or not raw or rec.get("error"):
            continue
        stats = by_condition.setdefault(condition, {
            "n": 0, "disagree": 0, "before": collections.Counter(), "after": collections.Counter(),
            "examples": [],
        })
        parsed, ok, _ = run_eval.parse_response(raw, condition)
        if not ok:
            continue
        stored = (rec.get("parsed") or {}).get("decision") or rec.get("decision")
        fresh = parsed.get("decision")
        stats["n"] += 1
        stats["before"][stored] += 1
        stats["after"][fresh] += 1
        if stored != fresh:
            stats["disagree"] += 1
            if len(stats["examples"]) < 2:
                stats["examples"].append((rec.get("id"), stored, fresh, raw[:110].replace("\n", " ")))
    return by_condition


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when any stored decision disagrees with a fresh parse")
    args = ap.parse_args()

    total_disagree = 0
    for rel in RESULTS:
        path = ROOT / rel
        if not path.exists():
            continue
        print(f"\n{rel}")
        for condition, s in sorted(compare(path).items()):
            pct = 100 * s["disagree"] / s["n"] if s["n"] else 0.0
            total_disagree += s["disagree"]
            print(f"  {condition:<12} n={s['n']:<4} disagree={s['disagree']:<4} ({pct:.1f}%)")
            if s["disagree"]:
                print(f"     stored: {dict(s['before'])}")
                print(f"     fresh : {dict(s['after'])}")
                for rid, stored, fresh, snippet in s["examples"]:
                    print(f"     e.g. {rid}: stored={stored} fresh={fresh}  {snippet!r}")

    print(f"\n{total_disagree} stored decision(s) do not match a fresh parse.")
    print("Nothing was modified. `make analyze paper` will pick up the new decisions only "
          "once the results files are regenerated deliberately.")
    if args.strict and total_disagree:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
