## Table: headline metrics

| Metric | Free-form | JSON, no CoT | Structured CoT |
|---|---|---|---|
| Scenarios | 600 | 600 | 600 |
| Parsed to a verdict | 600 | 600 | 599 |
| Decision accuracy (%) | 64.5 | 52.3 | 66.3 |
| Decision accuracy 95% CI | (60.6, 68.2) | (48.3, 56.3) | (62.4, 69.9) |
| Rule attribution accuracy (%) | 81.2 | 80.3 | 86.5 |
| Unsafe ACCEPT (count) | 103 | 277 | 141 |
| Unsafe ACCEPT (%) | 17.2 | 46.2 | 23.5 |
|   of which on Rule A denials | 11 | 71 | 6 |
|   of which on FLAG-routed | 92 | 206 | 135 |
| Unparseable output (%) | 0.0 | 0.0 | 0.2 |
| Order-sensitive output (%) | 14.5 | 0.0 | 0.0 |
| Multi-verdict output (%) | 35.7 | - | - |
| Median latency (s) | 2.42 | 0.44 | 2.55 |
| p95 latency (s) | 5.46 | 0.49 | 5.14 |
| Throughput (tok/s) | 64.0 | 66.4 | 63.2 |

## Table: per-rule decision accuracy (%)

| Rule | n | Free-form | JSON, no CoT | Structured CoT |
|---|---|---|---|
| A | 208 | 72.1 | 62.5 | 90.8 |
| B | 202 | 59.4 | 54.5 | 59.9 |
| C | 190 | 61.6 | 38.9 | 46.3 |

## Table: per-rule attribution accuracy (%)

| Rule | Free-form | JSON, no CoT | Structured CoT |
|---|---|---|---|
| A | 76.9 | 63.9 | 92.8 |
| B | 73.3 | 78.7 | 70.3 |
| C | 94.2 | 100.0 | 96.8 |

## Table: by scenario type (%)

| Type | n | Free-form | JSON, no CoT | Structured CoT |
|---|---|---|---|
| standard | 355 | 71.3 | 70.4 | 74.6 |
| adversarial | 155 | 50.3 | 20.0 | 45.8 |
| compound | 60 | 63.3 | 46.7 | 75.0 |
| edge | 30 | 60.0 | 16.7 | 56.7 |

## Table: adversarial techniques (%)

| Technique | n | Free-form | JSON, no CoT | Structured CoT |
|---|---|---|---|
| authority_framing | 21 | 28.6 | 0.0 | 38.1 |
| context_delimiter_spoof | 20 | 50.0 | 30.0 | 60.0 |
| encoding_obfuscation | 20 | 50.0 | 30.0 | 55.0 |
| false_policy_assertion | 18 | 44.4 | 5.6 | 33.3 |
| indirect_tool_output | 18 | 61.1 | 16.7 | 38.9 |
| instruction_override | 21 | 33.3 | 19.0 | 38.1 |
| payload_splitting | 19 | 73.7 | 36.8 | 52.6 |
| urgency_pressure | 18 | 66.7 | 22.2 | 50.0 |

## Rule misattribution (true -> predicted)


**Free-form**: A->A=160, A->B=26, A->C=10, B->A=22, B->B=148, B->C=23, C->A=7, C->C=179

**JSON, no CoT**: A->A=133, A->B=67, A->C=8, B->A=2, B->B=159, B->C=41, C->C=190

**Structured CoT**: A->A=192, A->B=9, A->C=6, B->A=10, B->B=142, B->C=50, C->A=2, C->B=4, C->C=184