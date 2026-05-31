# ADR-001 — Service Boundaries

**Status:** Accepted (MVP variant of the enterprise ADR-001).

## Context

The enterprise spec splits the system into three deployables (query · retrieval · ingestion)
across a network boundary, pulling distributed-systems and reliability concerns (timeouts,
circuit breakers, serialization contracts) into v1. For a solo-developer portfolio MVP, that
topology is premature: it adds operational cost before the trust-and-eval loop is even proven.

## Decision

Start as a **modular monorepo** with strict internal boundaries. Model query, retrieval,
ingestion, synthesis, verification, eval, and audit as **separate packages** behind abstract
`Protocol` seams (`packages/shared/shared/interfaces.py`). Do **not** force physical
microservices until a real scaling or ownership need appears.

## Rationale

- Preserves clean architecture (dependency inversion): infra is wired only in the composition
  root, so a package can later be lifted into its own service with no logic change.
- Keeps the solo MVP buildable and runnable on one machine / one `docker compose up`.
- Honors the "don't start distributed / Premature Topology Adoption" caution that the
  enterprise spec explicitly traded away — here we keep it, because we are optimizing for a
  shippable, measurable demo rather than independent team ownership.

## Consequences

- One process to run and debug; no network failure modes to handle in v1.
- When retrieval needs independent scaling, promoting `packages/retrieval` to a service is an
  adapter + deployment change, not a rewrite.
- The internal seam (`Retriever`) is identical to what the split-service call would use, so
  the migration path is preserved.
