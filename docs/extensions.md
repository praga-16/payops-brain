# Synthetic operations extension validation

Baseline: 118 passed, one opt-in Docker skip; repository clean at 163cc47.
.env is unchanged. Existing API contracts and original tests are retained.

Phase 1: additive lifecycle/payment-details tables; explicit synthetic historical
snapshot provenance, net-of-fee three-way checks, rail/merchant exposure summaries.
120 Python tests passed, one Docker skip; lifecycle Playwright passed, build and
original smoke passed. Schema initialization/backfill are idempotent.
