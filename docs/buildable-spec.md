# Wealth-Advisor Research RAG — Buildable Spec

> **What this is:** a buildable design spec for an advisor-facing research assistant,
> inspired by OpenAI FDE's Morgan Stanley engagement. Produced with the agentic-swe-kit
> method: *read the wiki → surface insights → propose → human pushes back → freeze as
> spec/ADR.* Each section (S1–S11) is one design step; together they form the spec we
> build from.
>
> **Status:** COMPLETE. S1–S11 all frozen. 33 decisions (D1–D33) resolved. 3 ADRs.
>
> This document is the *enterprise* design. The repo's MVP (see top-level `CLAUDE.md` and
> `docs/architecture.md`) deliberately defers the heavy infra (split services, OpenSearch,
> Bedrock-in-VPC, hash-chained ledger, OTel→Langfuse, withdrawal webhook) behind seams so a
> solo developer can ship a working, measurable demo. The three repo ADRs are the MVP
> variants of ADR-001/002/003 below.

---

## System in one sentence

An **advisor-facing, read-only** assistant that, given a wealth advisor's question,
retrieves the firm's research reports, synthesizes a **grounded, fully-cited** answer,
scores its own confidence, and routes low-confidence cases to a verification step — so
every advisor has the firm's best research at their fingertips, and **no answer reaches a
client without an advisor in the loop.**

---

## The design spine — the one idea everything serves

> *A confident wrong answer is the cardinal failure* (S1). Guards: citations (D5) ·
> ≥0.98 groundedness deploy-gate (D8) · structural injection kill-switch (D25) ·
> conservative confidence flag (D12) · groundedness-drift PAGE alert (D30).

## 3 ADRs

- **ADR-001** (S2) — Split services: 3 deployables (query · retrieval · ingestion).
- **ADR-002** (S4) — Hybrid retrieval (BM25 + dense + RRF + rerank) on OpenSearch; polyglot stores.
- **ADR-003** (S11) — Prototype: equity→fixed-income thin slice, measured vs advisor baseline.

## The concrete stack (enterprise target)

| Layer | Choice |
|---|---|
| Services | query-service · retrieval-service · ingestion-job — 3 deployables (D13) |
| Retrieval | OpenSearch: BM25 + dense kNN + RRF + filter (D17) + cross-encoder rerank (D18) |
| Models (all Bedrock in-VPC, D20) | Haiku classify · Sonnet-4.6 synth (Opus escalate) · Opus judge · dedicated embedder (D9) |
| Data | Postgres: report metadata · hash-chained append-only audit (D24) · eval results |
| Output contract | Pydantic schema — every claim → ≥1 citation or abstain (D19) |
| PII / guardrails | Bedrock Guardrails (D26) + redact-before-block |
| Observability | OTel → self-hosted Langfuse (D30) |

## Suggested build order

1. Eval harness + golden seed (S3) — *eval before pipeline*.
2. Ingestion job → OpenSearch indexes (S6 / S4).
3. Retrieval-service (hybrid + rerank).
4. Query-service: synthesis + structured output + citation-verify (S4 / S5).
5. Confidence scoring + HITL verification widget (S9).
6. Security: RBAC + audit ledger + guardrails (S7).
7. Observability + cost wiring (S10).
8. Run the prototype slice, parallel-run, measure vs baseline (S11).

---

## Decision register (33 decisions)

| # | Decision | Resolution | Where |
|---|---|---|---|
| D1 | Autonomy level | Assistive / read-only. No client-facing send, no personalized advice, no actuation. | S1 |
| D2 | Corpus boundary (v1) | Internal wealth-research reports only. | S1 |
| D3 | Entitlements | Uniform — all advisors see all research. Access control = authentication only. | S1 |
| D4 | Agent vs pipeline | Pure linear deterministic RAG pipeline. Retry dropped; low confidence routes to HITL. | S1, S2 |
| D13 | Architecture style (ADR-001) | Split services: 3 deployables. Internal boundary query↔retrieval. | S2 |
| D14 | Retrieval strategy | Hybrid BM25 + dense + RRF, structure-aware chunking. | S2 |
| D15 | Confidence signal | Retrieval-agreement + groundedness + calibrated LLM-as-judge. | S2 |
| D5 | Citation granularity | Two-level: display = section+page; verification = span/sentence (≥0.98 groundedness). | S4 |
| D6 | Chunking strategy | Structure-aware by section (~500–1000 tok, tables intact, disclosures tagged, version). | S4 |
| D17 | Retrieval engine | OpenSearch — BM25 + dense kNN + RRF + filtering in one engine. | S4 |
| D18 | Reranker | Include cross-encoder rerank (top-N→top-k). | S4 |
| D7 | Freshness SLA | Asymmetric: publish/update = nightly batch; withdrawal = webhook, near-real-time. | S6 |
| D21 | Ingestion architecture | Nightly batch reconcile + webhook withdraw; idempotent (deterministic chunk IDs). | S6 |
| D22 | Source interface | Push/webhook available — withdrawals now; extensible to full push. | S6 |
| D23 | Security posture | Threat model w/ 5 named adversaries; flat RBAC; injection defense-in-depth; in-VPC. | S7 |
| D24 | Audit tamper-evidence | Hash-chained append-only ledger — each row hashes prior. | S7 |
| D25 | Injection defense depth | Structural (instruction hierarchy + citation-validity) + sanitization. | S7 |
| D26 | PII detection | Managed Bedrock Guardrails — ingestion + output. | S7 |
| D8 | Eval metrics + pass bar | 7 metrics, asymmetric bar; ALL hard-block deploy; advisor-curated set. | S3 |
| D16 | Golden dataset bootstrap | Hybrid by phase: synthetic-seed-then-advisor-review → pure advisor-curated. | S3 |
| D9 | Model routing | Haiku classify · Sonnet-4.6 synth (Opus escalate) · Opus judge (swaps to Sonnet) · embedder. | S5 |
| D19 | Structured-output schema | Pydantic-validated; every claim → ≥1 citation or abstain; carries confidence band. | S5 |
| D20 | Model hosting | All via AWS Bedrock in-VPC. | S5 |
| D10 | Compliance regime | Internal / pilot only — formal regulatory controls deferred to graduation checklist. | S8 |
| D27 | Retention policy | Keep all audit+answers through pilot (tiny; refs not doc copies). | S8 |
| D28 | Graduation posture | Design audit-store seam now, defer build (AuditStore interface + Postgres adapter). | S8 |
| D11 | Trust-build pilot plan | Small+deep cohort (5–15 design partners), parallel-run, ~4-mo trust-build. | S9 |
| D12 | Confidence threshold | Tunable band cutoffs, conservative to start; calibrated w/ D15 judge. | S9 |
| D29 | Escalation routing | Advisor-only: flag + widget; no senior queue. | S9 |
| D30 | Observability stack | OTel → Langfuse, self-hosted in-VPC. | S10 |
| D31 | Caching in v1 | Defer caching, instrument cost only. | S10 |
| D32 | Prototype slice (ADR-003) | Equity THEN fixed-income, single-instrument lookups, 5–15 cohort. | S11 |
| D33 | Headline metric | Time-to-cited-answer vs manual baseline + adoption as trust signal. | S11 |

---

## Eval metrics + deploy gate (D8) — asymmetric, per S1 cardinal failure

| Metric | Measures | Pass-bar |
|---|---|---|
| Groundedness / faithfulness | every claim supported by cited span | ≥ 0.98 (cardinal guard) |
| False-confident rate | high-confidence AND wrong | = 0 (kill metric) |
| Hallucination rate | any unsupported claim | ≤ 1–2% |
| Citation validity | cited source exists in retrieved set (deterministic) | 100% |
| Retrieval recall@10 | correct report/section in top-k | ≥ 0.90 |
| Answer correctness | vs advisor-labeled expected | ≥ 0.85 |
| Abstention precision | "not found" is actually correct | ≥ 0.95 |

---

## Design steps S1–S11 (summary)

- **S1 Cognitive Design** — This is a pipeline, not an agent. Read-only, assistive.
  Confidence ≠ accuracy. "Agents recommend, humans implement." Asymmetric failure tolerance.
- **S2 System Architecture + ADR-001** — Split services; hybrid retrieval; structure-aware
  chunking; citation grounding + verification; confidence from retrieval agreement.
- **S3 Golden Dataset & Eval** — Eval is always-on infra. Advisor-curated golden set
  (100–500, never synthetic for the gate). JudgeOverfitting guard (judge ≠ synth). All bars
  hard-block.
- **S4 RAG / Memory Pipeline + ADR-002** — Memory tiers; OpenSearch; two-level citations;
  cross-encoder rerank; version-aware retrieval.
- **S5 LLM & Reasoning** — Model routing (Haiku/Sonnet/Opus); Pydantic structured output;
  context budget; prompt versioning; guardrails; all Bedrock in-VPC.
- **S6 Ingestion & Freshness** — Asymmetric: nightly batch publish + webhook withdraw.
  Idempotent (deterministic chunk IDs); schema evolution; derived-data re-derive; no KG.
- **S7 Security** — Threat model (5 adversaries); injection defense-in-depth incl. structural
  kill-switch; flat RBAC; hash-chained append-only audit; in-VPC isolation.
- **S8 Governance** — Internal/pilot only; explainability via citations + confidence; audit-
  store seam designed now; graduation checklist for FINRA/SEC/GDPR triggers.
- **S9 HITL / Trust** — Verification widget; confidence-banded escalation; conservative
  threshold (D12); feedback routes corrections to eval; small+deep pilot cohort.
- **S10 Observability + Economics** — Per-span latency/tokens/cost; groundedness-drift PAGE
  alert; OTel→self-hosted Langfuse; defer caching, instrument cost.
- **S11 Prototype Scope + ADR-003** — Thinnest slice: US equity single-ticker lookups, 5–15
  cohort; cardinal guards retained; measured vs advisor baseline; ~30-day build.

> For the full frozen text of each step (wiki sources, load-bearing insights, gates, and
> pushback resolutions), see the original `09-wealth-rag-buildable-spec.md` source document.
