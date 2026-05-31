# Evaluation

Evaluation is **first-class**, not an afterthought — "CI for agent behavior." Most people
build RAG apps; very few show how their RAG system *performs*. This is the portfolio
differentiator.

## Golden dataset

Advisor-curated (never purely synthetic for the deploy gate), 50–100 questions, stored as
JSONL at [data/golden_questions/golden.jsonl](../data/golden_questions/golden.jsonl). Schema
([shared.schemas.GoldenQuestion](../packages/shared/shared/schemas.py)):

```json
{"id": "eval_001", "query": "...", "expected_sources": ["..."],
 "expected_sections": ["..."], "expected_behavior": "answer|abstain",
 "difficulty": "easy|medium|hard", "category": "...", "ticker": "AAPL"}
```

**Mandatory edge cases** (already seeded): out-of-corpus (abstain), personalized-advice
(abstain), prompt-injection (abstain/block), plus normal lookups. To add later:
ambiguous-ticker and stale-vs-current conflicts.

## Metrics + deploy gate (D8 — all hard-block)

Defined in [packages/evals/evals/metrics.py](../packages/evals/evals/metrics.py):

| Metric | Measures | Bar |
|---|---|---|
| Groundedness | every claim supported by a cited span | ≥ 0.98 |
| **False-confident rate** | high-confidence AND wrong | **= 0 (kill metric)** |
| Hallucination rate | any unsupported claim | ≤ 0.02 |
| Citation validity | cited source exists in retrieved set (deterministic) | = 1.0 |
| Recall@10 | correct report/section in top-k | ≥ 0.90 |
| Correctness | vs. advisor-labeled expected | ≥ 0.85 |
| Abstention precision | "not found" is actually correct | ≥ 0.95 |

The bar is **asymmetric on purpose**: a false-confident answer is the cardinal failure, so it
is the kill metric. Bars are advisor-retunable during a pilot but every one hard-blocks
deploy.

## Three levels

- **Component:** retrieval recall/precision · chunker · citation verifier · judge calibration
  (must reach ≥80% human agreement before the judge is trusted).
- **Integration:** end-to-end golden Q → answer → sources; groundedness; correctness;
  confidence calibration (reliability diagram / ECE).
- **Production:** continuous eval on sampled queries; drift/staleness detection; degradation
  alert; advisor disputes feed back into the golden set (trust-build loop).

## Running

```bash
python scripts/run_eval.py
```

Phase 1 loads the golden set and prints the deploy bars. Phase 7 wires the runner that drives
the live pipeline against each question, computes the seven metrics, applies the gate, and
feeds the dashboard (`GET /eval/results`).

## Dashboard (Phase 7)

Will show: golden size, overall pass rate, each metric vs. its bar, false-confident count,
average latency/cost, and breakdowns by company and question type.
