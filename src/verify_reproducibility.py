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

# Macros in the manuscript that are *recorded measurements* rather than values
# computable from the committed generations. Peak device memory is an
# observation about the machine, not a function of the model outputs, so it
# cannot be derived - but it must not be joined by anything that could be.
#
# This list is a ratchet: the check below builds the macros twice from two
# different metrics files and reports every macro that did not move. A new
# constant therefore fails the build until it is either derived or added here
# deliberately.
KNOWN_RECORDED_MACROS = frozenset({"VRAMPeak"})


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
      # No figures: they are the only part that needs a third-party package, and
      # this check is about the numbers. Passing it keeps `make verify` runnable
      # on a clean clone with nothing installed.
      '--no-figs',
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


def _macros_from(metrics_path: Path, outdir: Path) -> dict[str, str]:
  """Generates results_macros.tex and parses it into {macro name: value}."""
  outdir.mkdir(parents=True, exist_ok=True)
  _run([
      sys.executable, 'src/make_macros.py',
      '--metrics', str(metrics_path), '--outdir', str(outdir),
  ])
  macros: dict[str, str] = {}
  for line in (outdir / 'results_macros.tex').read_text().splitlines():
    if not line.startswith('\\newcommand{'):
      continue
    name = line[len('\\newcommand{'):].split('}', 1)[0].lstrip('\\')
    macros[name] = line.rsplit('}{', 1)[-1].rstrip('}')
  return macros


def _with_every_number_moved(value):
  """Shifts every number in a metrics tree, leaving structure and strings alone."""
  if isinstance(value, bool):
    return value
  if isinstance(value, (int, float)):
    return value + 1
  if isinstance(value, dict):
    return {k: _with_every_number_moved(v) for k, v in value.items()}
  if isinstance(value, list):
    return [_with_every_number_moved(v) for v in value]
  return value


def check_macro_provenance(tmp: Path) -> bool:
  """Reports which manuscript macros are not derived from the metrics.

  The manuscript's numbers should move when the metrics move. Building the
  macros twice - once from the real metrics, once from a copy with every number
  shifted - and diffing the two identifies every macro that stayed put, which is
  exactly the set that could not have come from the evidence.
  """
  real = json.loads(
      (ROOT / 'results' / 'metrics.json').read_text(encoding='utf-8')
  )
  perturbed_path = tmp / 'metrics-shifted.json'
  perturbed_path.write_text(
      json.dumps(_with_every_number_moved(real)), encoding='utf-8'
  )

  real_macros = _macros_from(ROOT / 'results' / 'metrics.json', tmp / 'm-real')
  moved_macros = _macros_from(perturbed_path, tmp / 'm-shifted')

  shared = set(real_macros) & set(moved_macros)
  fixed = {name for name in shared if real_macros[name] == moved_macros[name]}
  new = fixed - KNOWN_RECORDED_MACROS
  gone = KNOWN_RECORDED_MACROS - fixed

  if not new and not gone:
    listed = ', '.join(sorted(fixed)) or 'none'
    print(f'  PASS  every macro derives from metrics.json '
          f'({len(shared) - len(fixed)} derived); recorded constants '
          f'declared: {listed}')
    return True

  print('  FAIL  the set of non-derived macros changed')
  if new:
    print(f'        new constant(s): {sorted(new)}')
    print('        Either derive them from results/metrics.json, or add them')
    print('        to KNOWN_RECORDED_MACROS with a note on where they came from.')
  if gone:
    print(f'        declared constant(s) now derived: {sorted(gone)}')
    print('        Remove them from KNOWN_RECORDED_MACROS.')
  return False


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
      '--only',
      choices=['corpus', 'metrics', 'macros'],
      help='run a single check instead of all of them',
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
    if args.only in (None, 'macros'):
      results.append(check_macro_provenance(tmp))

  if all(results):
    print('OK: the committed artifacts reproduce from the committed sources.')
    return 0
  print('FAILED: the committed artifacts do not reproduce.')
  return 1


if __name__ == '__main__':
  raise SystemExit(main())
