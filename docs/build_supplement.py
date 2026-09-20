#!/usr/bin/env python3
"""Build the supplementary document from the artifacts in this repository.

The submission portal asks for a supplementary file, and everything it should
contain was already here — `docs/FINDINGS.md`, `docs/DATA_SCHEMA.md` and
`results/tables.md` — but nothing assembled them, so the field stayed empty. This
does, so the file is generated from the repository rather than maintained beside it.

Two properties matter, and both come from this repository's own habits:

  * **The numbers cannot drift.** The reproducibility block is not prose; the
    verifier is executed at build time and its output is embedded verbatim. If the
    artifacts stop reproducing, the supplement says so.
  * **The provenance is stated.** `data/corpus.jsonl` and `results/metrics.json`
    are hashed into the document, so a reader can check that the supplement
    describes the same bytes they downloaded.

    uv run --with markdown python3 docs/build_supplement.py
    uv run --with markdown python3 docs/build_supplement.py --pdf

Writes `docs/supplementary.html`, and `docs/supplementary.pdf` with `--pdf` (needs
a Chromium/Chrome binary; the HTML is self-contained and prints correctly without
one, so a machine without a browser still produces the document).
"""

from __future__ import annotations

import argparse
import hashlib
import html
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
CITATION = ROOT / "CITATION.cff"


def read(path: pathlib.Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def citation_facts() -> tuple[str, list[tuple[str, str]]]:
    """Title and (name, affiliation) from CITATION.cff.

    Parsed by hand rather than with a YAML library so the build needs one
    dependency instead of two. The format is fixed by the CFF schema and is
    asserted below, so a restructure fails loudly instead of producing a document
    with an empty title.
    """
    text = read(CITATION)
    title = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
    if not title:
        raise SystemExit("CITATION.cff has no title")

    people: list[tuple[str, str]] = []
    family = given = affiliation = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- family-names:"):
            if family:
                people.append((f"{given} {family}", affiliation or ""))
            family = stripped.split(":", 1)[1].strip().strip('"')
            given = affiliation = None
        elif stripped.startswith("given-names:"):
            given = stripped.split(":", 1)[1].strip().strip('"')
        elif stripped.startswith("affiliation:"):
            affiliation = stripped.split(":", 1)[1].strip().strip('"')
    if family:
        people.append((f"{given} {family}", affiliation or ""))
    if not people:
        raise SystemExit("CITATION.cff lists no authors")
    return title.group(1).strip(), people


def verify_output() -> tuple[str, bool]:
    """Run this repository's own reproducibility checker and keep its output."""
    script = ROOT / "src" / "verify_reproducibility.py"
    if not script.exists():
        return "src/verify_reproducibility.py is missing from this checkout.", False
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT,
                            capture_output=True, text=True, timeout=900, check=False)
    combined = (result.stdout + result.stderr).strip()
    return combined or "(the checker produced no output)", result.returncode == 0


def digest(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        return "missing"
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            sha.update(block)
    return f"{sha.hexdigest()[:16]}…  ({path.stat().st_size:,} bytes)"


def demote(markdown_text: str) -> str:
    """Push every heading down one level so it sits under the supplement's sections."""
    return re.sub(r"^(#{1,5}) ", lambda m: "#" * (len(m.group(1)) + 1) + " ",
                  markdown_text, flags=re.MULTILINE)


def to_html(markdown_text: str) -> str:
    import markdown  # noqa: PLC0415  (a build dependency, declared in the docstring)

    return markdown.markdown(markdown_text, extensions=["tables", "fenced_code", "sane_lists"])


CSS = """
:root{--ink:#14181f;--muted:#5b6472;--rule:#d7dce4;--accent:#0b3d91;--accent2:#0d6b5f}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;color:var(--ink);background:#fff;
     font:10pt/1.42 "Inter","Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.page{max-width:210mm;margin:0 auto;padding:13mm 14mm 10mm}
h1{font-size:16pt;margin:0 0 2px;letter-spacing:-.3pt;font-weight:800;line-height:1.22}
h1+ p{margin-top:2px}
h2{font-size:9pt;text-transform:uppercase;letter-spacing:1.4pt;font-weight:800;color:var(--accent);
   margin:15px 0 5px;padding-bottom:3px;border-bottom:1px solid var(--rule);page-break-after:avoid}
h3{font-size:11pt;margin:11px 0 3px;font-weight:750;page-break-after:avoid}
h4{font-size:9.8pt;margin:9px 0 2px;font-weight:700;color:var(--accent2);page-break-after:avoid}
h5{font-size:9.4pt;margin:8px 0 2px;font-weight:700;page-break-after:avoid}
p{margin:4px 0}
ul,ol{margin:4px 0 0;padding-left:17px}
li{margin:1.6px 0}
a{color:var(--accent);text-decoration:none;word-break:break-word}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:8.5pt;
     background:#eef2f8;padding:0 3px;border-radius:2px}
pre{background:#f6f8fb;border:1px solid var(--rule);border-radius:4px;padding:7px 9px;
    overflow-x:auto;font-size:8.3pt;line-height:1.35;page-break-inside:avoid}
pre code{background:none;padding:0}
table{width:100%;border-collapse:collapse;margin:6px 0;font-size:8.7pt;page-break-inside:avoid}
th,td{border-bottom:1px solid #eef1f6;padding:3px 5px;text-align:left;vertical-align:top}
th{background:#f5f8fc;font-weight:700;border-bottom:1px solid var(--rule)}
td:first-child{white-space:nowrap}
blockquote{margin:6px 0;padding:5px 10px;border-left:3px solid var(--rule);color:var(--muted)}
header{border-bottom:2.2px solid var(--ink);padding-bottom:8px;margin-bottom:4px}
.authors{margin:4px 0 0;font-size:9.4pt}
.affil{margin:1px 0 0;font-size:8.6pt;color:var(--muted)}
.meta{margin:5px 0 0;font-size:8.6pt;color:var(--muted)}
.meta b{color:var(--ink)}
.box{background:#f5f8fc;border:1px solid #dbe3ef;border-radius:4px;padding:7px 10px;margin:7px 0 0}
.box p{margin:2px 0}
.ok{color:var(--accent2);font-weight:700}
hr{border:none;border-top:1px solid var(--rule);margin:12px 0}
@page{size:A4;margin:0}
@media print{body{font-size:9.4pt}.page{padding:11mm 13mm 9mm}}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true",
                        help="also render a PDF (needs a Chromium/Chrome binary)")
    args = parser.parse_args(argv)

    title, people = citation_facts()
    verification, ok = verify_output()

    authors = "; ".join(f"<b>{html.escape(name)}</b>" for name, _ in people)
    affiliations = people[0][1] if people else ""

    body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Supplementary material — {html.escape(title)}</title>
<style>{CSS}</style>
</head><body><div class="page">

<header>
  <h1>{html.escape(title)}</h1>
  <p class="authors">{authors}</p>
  <p class="affil">{html.escape(affiliations)}</p>
  <p class="meta"><b>Supplementary material</b> &middot; repository:
    <a href="https://github.com/sushant-me/Edge-Native_Semantic_Firewall_">
    github.com/sushant-me/Edge-Native_Semantic_Firewall_</a></p>
</header>

<h2>What this supplement contains</h2>
<p>This is the material the page limit kept out of the paper: the full result set, the
failure taxonomy, the ablation, the data schema that a reuser needs, and the exact
commands that regenerate every number. It is generated from the repository by
<code>docs/build_supplement.py</code>, so it cannot describe a different revision of
the artifacts than the one it was built from.</p>

<h2>Reproducibility</h2>
<p>The repository ships the corpus generator, the raw model output for every condition,
and a checker. The output below is that checker's, run at build time on the commit this
document was generated from &mdash; it is embedded, not summarised:</p>
<pre>{html.escape(verification)}</pre>
<p class="{'ok' if ok else ''}">{'All artifact checks pass.' if ok else
   'The checker did not pass, so this document should not be submitted.'}
   Re-running it needs no model execution:</p>
<pre>make verify        # corpus regenerates byte-for-byte; metrics recompute from raw outputs
make analyze       # regenerates results/tables.md and results/metrics.json</pre>

<h2>Artifact inventory</h2>
<table>
  <tr><th>artifact</th><th>sha256 (first 16) and size</th></tr>
  <tr><td><code>data/corpus.jsonl</code></td><td>{digest('data/corpus.jsonl')}</td></tr>
  <tr><td><code>results/metrics.json</code></td><td>{digest('results/metrics.json')}</td></tr>
  <tr><td><code>results/results_p1.jsonl</code></td><td>{digest('results/results_p1.jsonl')}</td></tr>
  <tr><td><code>results/results_p2.jsonl</code></td><td>{digest('results/results_p2.jsonl')}</td></tr>
  <tr><td><code>results/results_av.jsonl</code></td><td>{digest('results/results_av.jsonl')}</td></tr>
</table>
<p>The corpus is 600 scenarios, each labelled by construction rather than by a scorer, and
the generators use a fixed seed, so the file above is byte-identical on any machine. The
<code>results_*.jsonl</code> files are the unedited generations; every metric in the paper
is computed from them.</p>

<h2>Extended findings</h2>
{to_html(demote(read(ROOT / 'docs' / 'FINDINGS.md')))}

<h2>Data schema</h2>
{to_html(demote(read(ROOT / 'docs' / 'DATA_SCHEMA.md')))}

<h2>Full result tables</h2>
{to_html(read(ROOT / 'results' / 'tables.md'))}

<hr>
<p class="meta">Every number in this supplement is computed from the committed artifacts
listed above, and the reproducibility block is the output of this repository's own checker.
If any of it stops holding, <code>make verify</code> fails.</p>

</div></body></html>"""

    out_html = HERE / "supplementary.html"
    out_html.write_text(body, encoding="utf-8")
    print(f"wrote {out_html.relative_to(ROOT)}  ({len(body):,} bytes)")

    if args.pdf:
        chrome = next((c for c in ("chromium", "chromium-browser", "google-chrome",
                                   "google-chrome-stable") if shutil.which(c)), None)
        if not chrome:
            print("no Chromium/Chrome found; the HTML prints correctly from any browser",
                  file=sys.stderr)
            return 0
        out_pdf = HERE / "supplementary.pdf"
        subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                        "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}",
                        out_html.as_uri()], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out_pdf.exists():
            print(f"wrote {out_pdf.relative_to(ROOT)}  ({out_pdf.stat().st_size:,} bytes)")
        else:
            print("chromium did not produce a PDF", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
