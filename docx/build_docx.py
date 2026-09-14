#!/usr/bin/env python3
"""
Render the paper into the ETFG-2025 conference template.

Strategy: open the conference template (converted to transitional OOXML so it is
readable) and edit it in place, so every style, the two-column body section, the
page geometry and the ETFG header survive untouched. Only the placeholder text is
replaced.

Inputs : paper_ir.json, results/metrics.json, data/corpus.jsonl, figures, eq.png
Output : Edge-Native_Semantic_Firewall_ETFG2025.docx
"""
from __future__ import annotations

import json
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

BUILD = Path(".")
TEMPLATE = Path("../template/base_transitional.docx")
IR = json.loads((BUILD / "paper_ir.json").read_text())
MET = json.loads((BUILD / "../repo/results/metrics.json").read_text())
OUT = BUILD / "Edge-Native_Semantic_Firewall_ETFG2025.docx"

C = {"naive": "Free-form", "zeroshot": "JSON only", "cot": "Structured CoT",
     "cot_av": "CoT + decl. vector"}
PRETTY = {
    "instruction_override": "Instruction override", "authority_framing": "Authority framing",
    "context_delimiter_spoof": "Context-delimiter spoof", "encoding_obfuscation": "Encoding obfuscation",
    "payload_splitting": "Payload splitting", "false_policy_assertion": "False policy assertion",
    "urgency_pressure": "Urgency pressure", "indirect_tool_output": "Indirect tool output",
}


# ------------------------------------------------------------------ tables --
def tbl_policy():
    return {
        "caption": "TABLE II\nDeterministic Security Policy Framework",
        "header": ["Rule", "Action Vectors", "Threshold", "Decision Logic"],
        "rows": [
            ["A", "Execute System Cmd; Transfer Funds", "—", "DENY unconditionally"],
            ["B", "Modify Codebase", "≥ 95", "ACCEPT, else FLAG"],
            ["C", "Read Database", "≥ 80", "ACCEPT, else FLAG"],
        ],
        "widths": [0.38, 1.42, 0.62, 1.03],
    }


def tbl_corpus():
    return {
        "caption": "TABLE III\nCorpus Composition. Labels Follow from the Policy by Construction.",
        "header": ["Rule", "n", "ACCEPT", "DENY", "FLAG"],
        "rows": [
            ["A (hard denial)", "208", "0", "208", "0"],
            ["B (high threshold)", "202", "78", "0", "124"],
            ["C (standard access)", "190", "73", "0", "117"],
            ["Total", "600", "151", "208", "241"],
        ],
        "widths": [1.32, 0.42, 0.57, 0.55, 0.59],
        "bold_last_row": True,
    }


def tbl_positioning():
    return {
        "caption": "TABLE I\nRuntime Safety Mechanisms for LLM Agents, by Deployment Locus and Enforcement Target",
        "header": ["Mechanism", "Locus", "Enforces", "Policy-param.", "Audit", "Adv. eval."],
        "rows": [
            ["Safety classifiers [17], [18]", "cloud or local", "fixed harm taxonomy", "no", "no", "partially"],
            ["Programmable rails [19]", "local possible", "dialogue flow, custom checks", "yes", "partial", "limited"],
            ["LLM-as-a-Judge [20]", "typically cloud", "free-form rubric", "yes (prompt)", "yes", "rarely"],
            ["Injection benchmarks [8], [9], [10], [11]", "offline", "measurement, not enforcement", "n/a", "n/a", "yes, by construction"],
            ["Design-level defences [13], [14], [15], [16]", "in-pipeline", "capability and flow constraints", "yes", "partial", "yes"],
            ["This work", "local edge", "operator action policy", "yes", "yes", "yes (155 scenarios)"],
        ],
        "widths": [1.02, 0.40, 0.76, 0.44, 0.30, 0.53],
        "font": 6.5,
        "bold_last_row": True,
    }


def tbl_headline():
    rows = [
        ["Scenarios evaluated", "600", "600", "600"],
        ["Parsed to a verdict", "600", "600", "599"],
        ["Unparseable output (%)", "0.0", "0.0", "0.2"],
        ["Order-sensitive output (%)", "14.5", "0.0", "0.0"],
        ["Decision accuracy (%)", "64.5", "52.3", "66.3"],
        ["   95% CI", "(60.6, 68.2)", "(48.3, 56.3)", "(62.4, 69.9)"],
        ["Rule-attribution accuracy (%)", "81.2", "80.3", "86.5"],
        ["Unsafe ACCEPT (count)", "103", "277", "141"],
        ["Unsafe ACCEPT (%)", "17.2", "46.2", "23.5"],
        ["   of which on Rule A denials", "11", "71", "6"],
        ["   of which on FLAG-routed proposals", "92", "206", "135"],
        ["Median latency (s)", "2.42", "0.44", "2.55"],
        ["95th-percentile latency (s)", "5.46", "0.49", "5.14"],
        ["Throughput (tokens/s)", "64.0", "66.4", "63.2"],
    ]
    return {
        "caption": "TABLE IV\nHeadline Results Across the Three Prompting Conditions",
        "header": ["Metric", "Free-form", "JSON only", "Structured CoT"],
        "rows": rows, "widths": [1.52, 0.60, 0.56, 0.77], "font": 7.5,
    }


def tbl_perrule():
    rows = []
    for r, name in (("A", "A"), ("B", "B"), ("C", "C")):
        n = MET["cot"]["per_rule"][r]["n"]
        rows.append([name, str(n)] + [f"{MET[c]['per_rule'][r]['decision_accuracy']:.1f}"
                                      for c in ("naive", "zeroshot", "cot")]
                    + [f"{MET['cot']['per_rule'][r]['rule_attribution_accuracy']:.1f}"])
    return {
        "caption": "TABLE V\nDecision Accuracy (%) by Governing Rule",
        "header": ["Rule", "n", "Free-form", "JSON only", "CoT", "CoT attr."],
        "rows": rows, "widths": [0.44, 0.38, 0.63, 0.62, 0.52, 0.66],
    }


def tbl_adv():
    rows = []
    techs = sorted({t for c in ("naive", "zeroshot", "cot") for t in MET[c]["per_technique"]})
    for t in techs:
        n = MET["cot"]["per_technique"][t]["n"]
        rows.append([PRETTY.get(t, t), str(n)] +
                    [f"{MET[c]['per_technique'].get(t, {}).get('accuracy', 0):.1f}"
                     for c in ("naive", "zeroshot", "cot")])
    for label, key in (("All adversarial", "adversarial"), ("Standard only", "standard"),
                       ("Compound", "compound"), ("Boundary", "edge")):
        n = MET["cot"]["per_tag"][key]["n"]
        rows.append([label, str(n)] + [f"{MET[c]['per_tag'][key]['decision_accuracy']:.1f}"
                                       for c in ("naive", "zeroshot", "cot")])
    return {
        "caption": "TABLE VI\nDecision Accuracy (%) on the 155 Adversarial Scenarios, by Injection Technique",
        "header": ["Technique", "n", "Free-form", "JSON only", "CoT"],
        "rows": rows, "widths": [1.30, 0.32, 0.60, 0.58, 0.65],
        "bold_from": len(techs),
    }


TABLES = [tbl_positioning, tbl_policy, tbl_corpus, tbl_headline, tbl_perrule, tbl_adv]
FIGURES = [
    ("arch.png", "Fig. 1.  Generator–Evaluator pipeline. Actor and Firewall share one model "
                 "instance; the Actor is flushed from memory before the Firewall is instantiated, "
                 "so only one instance is resident. Nothing crosses the host boundary.", 3.1),
    ("../repo/results/figs/fig_accuracy.png",
     "Fig. 2.  (a) Decision accuracy overall and by governing rule. (b) Unsafe-ACCEPT rate. "
     "(c) Free-form output integrity: unparseable and order-sensitive responses.", 3.25),
    ("../repo/results/figs/fig_confusion.png",
     "Fig. 3.  Confusion matrices against policy-derived labels. Rows are ground truth, columns "
     "are the model's verdict. DENY→ACCEPT executes a prohibited action; FLAG→ACCEPT executes one "
     "that should have reached a human first.", 3.25),
]


# ----------------------------------------------------------------- helpers --
def add_runs(par, runs):
    for text, fmt in runs:
        r = par.add_run(text)
        if fmt == "b":
            r.bold = True
        elif fmt == "i":
            r.italic = True
        elif fmt == "tt":
            r.font.name = "Consolas"
            r.font.size = Pt(8.5)
        elif fmt == "sup":
            r.font.superscript = True
        elif fmt == "sub":
            r.font.subscript = True
        elif fmt == "sc":
            r.font.small_caps = True
    return par


def new_par(doc, style, runs=None, align=None):
    p = doc.add_paragraph(style=style)
    if runs:
        add_runs(p, runs)
    if align is not None:
        p.alignment = align
    return p


def make_table(doc, spec):
    hdr = spec["header"]
    t = doc.add_table(rows=1 + len(spec["rows"]), cols=len(hdr))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    widths_tw = [int(w * 1440) for w in spec["widths"]]

    # tblW must precede tblLayout in the CT_TblPrBase sequence, otherwise
    # Word and LibreOffice ignore both and fall back to autofit.
    tblPr = t._tbl.tblPr
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(sum(widths_tw))); tw.set(qn("w:type"), "dxa")
    tblPr.append(tw)
    layout = OxmlElement("w:tblLayout"); layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    # renderers lay out from w:tblGrid, so the grid columns must be set too
    grid = t._tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths_tw):
        gc.set(qn("w:w"), str(w))
    fs = spec.get("font", 8.0)
    for j, h in enumerate(hdr):
        cell = t.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.style = doc.styles["table col head"]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(fs)
    for i, row in enumerate(spec["rows"], start=1):
        for j, val in enumerate(row):
            cell = t.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.style = doc.styles["table copy"]
            r = p.add_run(val)
            r.font.size = Pt(fs)
            if spec.get("bold_last_row") and i == len(spec["rows"]):
                r.bold = True
            if spec.get("bold_from") is not None and (i - 1) >= spec["bold_from"]:
                r.bold = True
    for row in t.rows:
        for j, cell in enumerate(row.cells):
            cell.width = Inches(spec["widths"][j])
    return t


def caption_par(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    lines = text.split("\n")
    r = p.add_run(lines[0]); r.bold = True; r.font.size = Pt(8)
    if len(lines) > 1:
        p.add_run("\n")
        r2 = p.add_run(lines[1]); r2.font.size = Pt(8)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    return p


# -------------------------------------------------------------------- main --
def main():
    doc = docx.Document(str(TEMPLATE))
    b = doc.element.body

    # ---- clear the template's demo table(s) ----
    for t in list(b.findall(qn("w:tbl"))):
        b.remove(t)

    paras = doc.paragraphs
    sect_idx = []
    for i, p in enumerate(paras):
        pPr = p._p.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
            sect_idx.append(i)

    # ---- title / authors (sections 0-2) ----
    def set_text(par, text, bold=None, size=None, italic=None):
        for r in list(par.runs):
            r._r.getparent().remove(r._r)
        r = par.add_run(text)
        if bold is not None: r.bold = bold
        if italic is not None: r.italic = italic
        if size is not None: r.font.size = Pt(size)
        return r

    set_text(paras[0], IR["title"])
    set_text(paras[2], ", ".join(a["name"] for a in IR["authors"]))
    set_text(paras[3], IR["affiliation"])
    set_text(paras[4], ", ".join(a["email"] for a in IR["authors"]), size=9)

    # ---- locate the body region: after the 3rd section break, before the last ----
    body_start = sect_idx[2] + 1          # first paragraph after the 4-column break
    body_end = sect_idx[-1]               # paragraph carrying the 2-column sectPr

    anchor = paras[body_end]._p           # keep this paragraph: it holds the sectPr
    set_text(paras[body_end], "")         # drop the template guidance text

    # delete every paragraph in between
    for p in paras[body_start:body_end]:
        p._p.getparent().remove(p._p)

    # ---- build the paper content ----
    ti = fi = 0
    built = []

    for kind, payload in IR["blocks"]:
        if kind == "abstract":
            par = new_par(doc, "Abstract")
            r = par.add_run("Abstract\u2014"); r.bold = True; r.italic = True
            add_runs(par, payload)
            built.append(par)
        elif kind == "keywords":
            par = new_par(doc, "Keywords")
            r = par.add_run("Keywords\u2014"); r.bold = True; r.italic = True
            add_runs(par, payload)
            built.append(par)
        elif kind == "h1":
            built.append(new_par(doc, "Heading 1", payload))
        elif kind == "h2":
            built.append(new_par(doc, "Heading 2", payload))
        elif kind == "p" and isinstance(payload, str):
            if payload == "@@TABLE@@":
                spec = TABLES[ti](); ti += 1
                built.append(caption_par(doc, spec["caption"]))
                built.append(make_table(doc, spec))
                sp = doc.add_paragraph(); sp.paragraph_format.space_after = Pt(0)
                built.append(sp)
            elif payload == "@@FIGURE@@":
                src, cap, width = FIGURES[fi]; fi += 1
                fp = doc.add_paragraph(); fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                fp.add_run().add_picture(str(BUILD / src), width=Inches(width))
                cp = doc.add_paragraph(style="figure caption"); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cp.add_run(cap)
                built.append(fp); built.append(cp)
            elif payload == "@@EQUATION@@":
                ep = doc.add_paragraph(style="equation")
                ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = ep.add_run()
                run.add_picture(str(BUILD / "eq.png"), width=Inches(2.15))
                rn = ep.add_run("\t(1)")
                rn.font.size = Pt(9)
                built.append(ep)
            else:
                built.append(new_par(doc, "Body Text", payload))
        elif kind == "p":
            # narrative paragraph: payload is a list of (text, fmt) runs
            built.append(new_par(doc, "Body Text", payload))
        elif kind == "bullets":
            for item in payload:
                par = new_par(doc, "bullet list", item)
                par.paragraph_format.left_indent = Inches(0.2)
                built.append(par)

    # ---- references ----
    built.append(new_par(doc, "Heading 5", [("References", None)]))
    for ref in IR["references"]:
        par = new_par(doc, "references", ref["runs"])
        par.paragraph_format.space_after = Pt(2)
        built.append(par)

    # move everything in front of the anchor paragraph, preserving order
    for el in built:
        anchor.addprevious(el._p if hasattr(el, "_p") else el._tbl)

    doc.save(str(OUT))
    print(f"wrote {OUT}")
    print(f"  tables inserted : {ti}")
    print(f"  figures inserted: {fi}")
    print(f"  references      : {len(IR['references'])}")
    print(f"  content blocks  : {len(built)}")


if __name__ == "__main__":
    main()
