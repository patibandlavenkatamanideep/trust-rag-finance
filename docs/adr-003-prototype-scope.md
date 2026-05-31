# ADR-003 — Prototype Scope

**Status:** Accepted.

## Context

The system could span many asset classes, multi-report synthesis, compliance workflows, and
multi-agent behavior. Building all of that before the core trust loop works proves the wrong
thing and blows the timeline.

## Decision

The thinnest provable slice: **public US equity documents, single-company / single-ticker
lookups** (rating / revenue / risk-factor / strategy questions). Defer other asset classes,
multi-report synthesis, and the full compliance platform.

**Cardinal guards stay IN even in the prototype:** citation grounding, deterministic citation
verification, groundedness eval, abstention, and the conservative confidence flag. Cutting
them would demo a normal RAG chatbot, not this system.

## Rationale

- Single-ticker lookups are the highest-volume, simplest path — the right first slice.
- Keeping the guards in is the entire point: the differentiator is *knowing when not to
  answer*, measured against a golden set.
- Success is measured **vs. the advisor's manual baseline** (portal → search → read → answer),
  not against perfection. Headline metric: **time-to-cited-answer** + an adoption signal.

## Consequences

- Fixed-income, options, and multi-report synthesis are explicitly out of scope for the MVP
  (each needs its own chunking, terminology, and golden slice).
- The golden dataset and eval harness are scoped to equity single-ticker questions first,
  with out-of-corpus / personalized-advice / prompt-injection edge cases included from day one.
