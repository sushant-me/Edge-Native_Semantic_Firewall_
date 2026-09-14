# Edge-Native Semantic Firewall for Autonomous LLM Agents

**A Structured Chain-of-Thought Verification Framework**

Sushant Poudel · Rakhee Pandey · Aashika Pandey
Department of Computer Science and Engineering, Nepal Engineering College, Bhaktapur, Nepal

---

An autonomous agent that executes actions rather than proposing them sits outside the reach of
role-based access control, which authenticates an identity but has nothing to say about whether a
given action should happen. This repository contains the full system, the evaluation corpus, all
raw model outputs, and the camera-ready paper for a study of whether a small, locally served
language model can act as that missing verification layer.

Everything here was produced by running [Phi-3-mini-4k-instruct](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
(3.8B parameters, 4-bit quantized) on a single consumer laptop inside a 4.2 GiB VRAM budget.
**No cloud inference was used at any point.**

---

## The headline result is not the one we expected

We compared three ways of asking the same model to evaluate a proposed action against a written
policy: unconstrained free-form text, JSON-constrained output with no reasoning field, and JSON
output with a mandated Chain-of-Thought field order (rule → reasoning → confidence → decision).

**Constraining the output format without requiring the reasoning step produced the least safe
evaluator of the three.** The JSON-only arm approved **46.2%** of proposals the policy would have
blocked or sent to human review — markedly worse than unconstrained free-form at 17.2%. It
approved hard-denial commands such as `echo 'app ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers` at 95%
confidence. Structured output on its own removes the deliberation and keeps the verdict.

The full schema fixes most of that gap and improves the metric that matters most:

| Metric | Free-form | JSON only | Structured CoT |
|---|---|---|---|
| Decision accuracy | 64.5% | 52.3% | **66.3%** |
| Rule-attribution accuracy | 81.2% | 80.3% | **86.5%** |
| Unsafe ACCEPT (count) | 103 | 277 | 141 |
| Unsafe ACCEPT (%) | **17.2%** | 46.2% | 23.5% |
| — of which on **Rule A hard denials** | 11 | 71 | **6** |
| Rule A decision accuracy | 72.1% | 62.5% | **90.8%** |
| Adversarial subset accuracy | 50.3% | 20.0% | 45.8% |
| Median latency | 2.42 s | 0.44 s | 2.55 s |

600 scenarios per condition, all executed on the model at temperature 0. Peak device memory:
**3,947 MiB**, inside the stated 4.2 GiB ceiling, at 96% GPU utilisation.

### And it is not enough

The best configuration still approved **6 of 208** irreversible hard-denial actions, and it was
*more permissive than free-form* on ambiguous proposals that should have reached a human. Roughly
one verdict in ten changes between identical runs. We report all of this in the paper rather than
rounding it away, and we withdraw three claims made in an earlier version of the work that the
measurements falsified:

- **"100% policy adherence"** — removed. Measured accuracy is 66.3%.
- **The null-confidence defence** — the design claimed Rule A yields a null confidence score,
  removing the score as an attack surface. It never happens: zero null scores in 599 parseable
  outputs, and median confidence was 90 whether the rule attribution was right or wrong.
- **The original corpus figures** — derived from a keyword evaluator sharing vocabulary with the
  model. Deleted; every label now follows from the policy by construction.

The concluding position is that a model of this size can serve as **one layer** of a
defence-in-depth stack, and that the evidence does not support using it as a sole control.

---

## Repository layout

```
paper/
  main.pdf                    camera-ready manuscript (10 pp, IEEEtran conference)
  main.tex                    LaTeX source
  results_macros.tex          generated numeric macros — do not edit by hand
  adv_table.tex               generated table body — do not edit by hand
  response_to_reviewers.md    point-by-point response to the two reviews
  original_submission.pdf     the pre-revision version, kept for provenance
src/
  corpus.py                   deterministic 600-scenario generator (seed 42)
  run_eval.py                 evaluation harness — four prompting conditions
  analyze.py                  metrics, markdown tables, vector figures
  variance.py                 run-to-run agreement between two passes
  make_macros.py              metrics.json -> LaTeX macros
  examples.py                 pulls qualitative failure traces
  Modelfile                   Ollama model definition (num_ctx 4096, temp 0)
data/
  corpus.jsonl                the 600 scenarios with construction-derived labels
results/
  results_p1.jsonl            1,800 generations — free-form, JSON-only, CoT
  results_av.jsonl              600 generations — CoT with declared action vector
  results_p2.jsonl              600 generations — replication subset (200 x 3)
  metrics.json                every reported metric
  tables.md                   the same metrics as markdown tables
  figs/                       vector figures used by the manuscript
docs/
  FINDINGS.md                 extended analysis narrative
  DATA_SCHEMA.md              field-by-field documentation of the JSONL files
```

---

## Reproducing

Requires Python 3.10+, [Ollama](https://ollama.com) with a CUDA-capable GPU (or CPU, much slower),
and a TeX engine for the paper ([tectonic](https://tectonic-typesetting.github.io) is what we used).

```bash
pip install -r requirements.txt

# 1. Fetch the model (2.39 GB) and register it
curl -L -o Phi-3-mini-4k-instruct-q4.gguf \
  https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
# point the FROM line in src/Modelfile at that file, then:
ollama create phi3-mini-firewall -f src/Modelfile
ollama serve

# 2. Generate the corpus (deterministic; asserts every marginal before writing)
python src/corpus.py --out data/corpus.jsonl

# 3. Evaluate — 3 conditions x 600 scenarios, ~85 min on an RTX 4050
python src/run_eval.py --out results/results_p1.jsonl

# 4. Ablation and replication subset
python src/run_eval.py --out results/results_av.jsonl --conditions cot_av
python src/run_eval.py --out results/results_p2.jsonl --limit 200

# 5. Analysis
python src/analyze.py \
  --results results/results_p1.jsonl results/results_av.jsonl \
  --outdir results \
  --replication results/results_p1.jsonl results/results_p2.jsonl

# 6. Paper
python src/make_macros.py --metrics results/metrics.json --outdir paper
cd paper && tectonic -X compile main.tex
```

`make help` lists these as targets.

Raw outputs are committed, so **steps 3–4 can be skipped** and the analysis and paper rebuilt from
the checked-in data alone.

### Environment used

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 4050 Laptop, 6 GiB physical, 3,947 MiB peak measured |
| CPU / RAM | AMD Ryzen 5, 16 GB |
| Runtime | Ollama 0.34.0 (CUDA 13) |
| Model | Phi-3-mini-4k-instruct, Q4_K_M GGUF, 2.39 GB |
| Decoding | temperature 0, top-p 1, top-k 1, seed 42, num_ctx 4096, num_predict 400 |

---

## Two design decisions worth understanding

**Ground-truth labels are assigned by construction, not by a scorer.** Rule A scenarios are DENY
unconditionally. Rules B and C are ACCEPT only when the authored justification is complete enough
that a competent reviewer would clear the threshold, otherwise FLAG. No adversarial scenario can be
ACCEPT by construction. `corpus.py` asserts every marginal before it writes a single scenario, so
the label distribution in the paper's Table III cannot drift from the design. This matters because
an earlier version labelled scenarios with a keyword scorer whose vocabulary overlapped the
evaluator's, which meant the resulting accuracy measured the agreement of two copies of the same
heuristic rather than the behaviour of the model.

**The free-form condition has no output contract**, so its accuracy depends on a parsing
convention. The harness records every verdict mention, and the analysis reports both an
*unparseable* rate (no verdict found) and an *order-sensitive* rate (first and last verdict tokens
disagree). The paper's free-form numbers use last-mention extraction and say so explicitly. 14.5%
of free-form responses were order-sensitive, which is itself an argument for constrained output in
a security path.

---

## Citation

If you use this code, corpus, or results, please cite the paper. `CITATION.cff` is included, so
GitHub's **Cite this repository** button will produce a BibTeX entry.

```bibtex
@inproceedings{poudel2026edgenative,
  title     = {Edge-Native Semantic Firewall for Autonomous {LLM} Agents:
               A Structured Chain-of-Thought Verification Framework},
  author    = {Poudel, Sushant and Pandey, Rakhee and Pandey, Aashika},
  booktitle = {Department of Computer Science and Engineering, Nepal Engineering College},
  year      = {2026}
}
```

---

## License

- **Source code** (`src/`) — MIT, see [LICENSE](LICENSE).
- **Paper, corpus, and results** (`paper/`, `data/`, `results/`, `docs/`) — Creative Commons
  Attribution 4.0 International, see [LICENSE-paper](LICENSE-paper).

## Responsible use

The corpus contains synthetic operational scenarios including destructive shell commands and
simulated funds transfers, written for evaluating a safety mechanism. They are inert strings; the
pipeline never executes anything, and every verdict is recorded rather than enforced. The
adversarial prompts are included because they are the evidence for the paper's failure analysis.
