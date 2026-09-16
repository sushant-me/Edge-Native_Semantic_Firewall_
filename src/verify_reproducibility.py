#!/usr/bin/env python3
"""Reproducibility checks for the committed artifacts.

The paper's central methodological claim is that the ground-truth labels follow
from the policy *by construction* rather than from a scorer run over the text,
and that every reported number is derived from the committed raw outputs.  Both
of those are falsifiable, so this script falsifies-or-confirms them:

  1. ``data/corpus.jsonl`` is exactly what ``src/corpus.py`` writes from
     ``SEED = 42``.  Compared byte-for-byte: the corpus holds only strings,
     integers and nulls, so there is no float repr that could drift between
     Python versions and make a byte comparison spurious.

  2. ``results/metrics.json`` is exactly what ``src/analyze.py`` derives from
     the committed ``results/*.jsonl``.  Compared as parsed JSON rather than
     bytes, because the metrics do contain floats and their formatting is not
     a property worth pinning.

Neither check re-runs the model.  The 3,000 generations under ``results/`` are
committed, so the numbers are verifiable without a GPU.

Run:   python src/verify_reproducibility.py
Exit:  0 if both properties hold, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> None:
  """Runs a build step, surfacing its output only when it fails."""
  proc = subprocess.run(
      args, cwd=ROOT, capture_output=True, text=True, check=False
  )
  if proc.returncode != 0:
    sys.stderr.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    raise SystemExit(f'command failed ({proc.returncode}): {" ".join(args)}')


def check_corpus(tmp: Path) -> bool:
  """Confirms the corpus regenerates byte-for-byte from the committed seed."""
  regenerated = tmp / 'corpus.jsonl'
  _run([sys.executable, 'src/corpus.py', '--out', str(regenerated)])

  committed = ROOT / 'data' / 'corpus.jsonl'
  expected = committed.read_bytes()
  actual = regenerated.read_bytes()

  if expected == actual:
    n = actual.count(b'\n')
    print(f'  PASS  data/corpus.jsonl reproduces byte-for-byte ({n} scenarios)')
    return True

  print('  FAIL  data/corpus.jsonl does NOT match src/corpus.py')
  exp_lines = expected.splitlines()
  act_lines = actual.splitlines()
  if len(exp_lines) != len(act_lines):
    print(f'        line count: committed={len(exp_lines)} '
          f'regenerated={len(act_lines)}')

  # Report the field that differs, not a truncated prefix: the scenario text is
  # long and identical across a corpus, so the differing key sits far past any
  # fixed-width excerpt.
  for i, (e, a) in enumerate(zip(exp_lines, act_lines), start=1):
    if e == a:
      continue
    print(f'        first difference at scenario {i}:')
    try:
      exp_obj = json.loads(e)
      act_obj = json.loads(a)
    except json.JSONDecodeError:
      print('          line is not valid JSON in one of the two files')
      break
    for key in sorted(set(exp_obj) | set(act_obj)):
      if exp_obj.get(key) != act_obj.get(key):
        print(f'          field {key!r}:')
        print(f'            committed:   {exp_obj.get(key)!r}')
        print(f'            regenerated: {act_obj.get(key)!r}')
    break
  return False


def check_metrics(tmp: Path) -> bool:
  """Confirms every reported number derives from the committed raw outputs."""
  outdir = tmp / 'analysis'
  outdir.mkdir(parents=True, exist_ok=True)

  _run([
      sys.executable,
      'src/analyze.py',
      '--results', 'results/results_p1.jsonl', 'results/results_av.jsonl',
      '--corpus', 'data/corpus.jsonl',
      '--outdir', str(outdir),
      '--replication', 'results/results_p1.jsonl', 'results/results_p2.jsonl',
  ])

  committed = json.loads(
      (ROOT / 'results' / 'metrics.json').read_text(encoding='utf-8')
  )
  actual = json.loads((outdir / 'metrics.json').read_text(encoding='utf-8'))

  if committed == actual:
    print(f'  PASS  results/metrics.json reproduces from the raw outputs '
          f'({len(committed)} conditions)')
    return True

  print('  FAIL  results/metrics.json does NOT match src/analyze.py output')
  for key in sorted(set(committed) | set(actual)):
    if committed.get(key) != actual.get(key):
      print(f'        differs at condition {key!r}')
  return False


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
      '--only',
      choices=['corpus', 'metrics'],
      help='run a single check instead of both',
  )
  args = parser.parse_args()

  print('Reproducibility checks (no model execution required)')
  results = []
  with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    if args.only in (None, 'corpus'):
      results.append(check_corpus(tmp))
    if args.only in (None, 'metrics'):
      results.append(check_metrics(tmp))

  if all(results):
    print('OK: the committed artifacts reproduce from the committed sources.')
    return 0
  print('FAILED: the committed artifacts do not reproduce.')
  return 1


if __name__ == '__main__':
  raise SystemExit(main())
