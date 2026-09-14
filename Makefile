# Makefile — reproduction targets for the Edge-Native Semantic Firewall study.
#
# Raw model outputs are committed under results/, so `make analyze paper` rebuilds
# every reported number and the PDF from the checked-in data alone. The `model`,
# `corpus`, `eval`, `ablation` and `replicate` targets re-run the study from scratch
# and need a GPU (or a lot of patience on CPU).

PY      ?= python3
OLLAMA  ?= ollama
MODEL   ?= phi3-mini-firewall
GGUF    ?= Phi-3-mini-4k-instruct-q4.gguf
GGUF_URL:= https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

.PHONY: help model serve corpus eval ablation replicate analyze figures paper paper-single all clean distclean

help:
	@echo "Targets"
	@echo "  model      download the GGUF (2.39 GB) and register it with Ollama"
	@echo "  serve      start the Ollama server"
	@echo "  corpus     generate the 600-scenario corpus  -> data/corpus.jsonl"
	@echo "  eval       full 3-condition evaluation       -> results/results_p1.jsonl  (~85 min)"
	@echo "  ablation   declared-action-vector condition  -> results/results_av.jsonl"
	@echo "  replicate  200-scenario replication subset   -> results/results_p2.jsonl"
	@echo "  analyze    metrics, tables and figures       -> results/"
	@echo "  paper      regenerate LaTeX macros and compile the two-column PDF"
	@echo "  paper-single  compile the single-column Times version"
	@echo "  all        analyze + paper, from the committed raw outputs"
	@echo "  clean      remove LaTeX build artefacts"

model:
	@test -f $(GGUF) || curl -L -o $(GGUF) $(GGUF_URL)
	$(OLLAMA) create $(MODEL) -f src/Modelfile

serve:
	$(OLLAMA) serve

corpus:
	$(PY) src/corpus.py --out data/corpus.jsonl

eval:
	$(PY) src/run_eval.py --corpus data/corpus.jsonl --out results/results_p1.jsonl

ablation:
	$(PY) src/run_eval.py --corpus data/corpus.jsonl --out results/results_av.jsonl --conditions cot_av

replicate:
	$(PY) src/run_eval.py --corpus data/corpus.jsonl --out results/results_p2.jsonl --limit 200

analyze:
	$(PY) src/analyze.py \
	  --results results/results_p1.jsonl results/results_av.jsonl \
	  --corpus data/corpus.jsonl \
	  --outdir results \
	  --replication results/results_p1.jsonl results/results_p2.jsonl

figures: analyze

paper: analyze
	$(PY) src/make_macros.py --metrics results/metrics.json --outdir paper
	cd paper && tectonic -X compile main.tex

paper-single: analyze
	$(PY) src/make_macros.py --metrics results/metrics.json --outdir paper
	cd paper && tectonic -X compile main_singlecolumn.tex

all: paper

clean:
	rm -f paper/*.aux paper/*.log paper/*.out paper/*.xdv
	rm -rf src/__pycache__

distclean: clean
	rm -f $(GGUF) results/results_p1.jsonl results/results_av.jsonl results/results_p2.jsonl
