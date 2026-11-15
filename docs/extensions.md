# Synthetic operations extension validation

Baseline: 118 passed, one opt-in Docker skip; repository clean at 163cc47.
.env is unchanged. Existing API contracts and original tests are retained.

Phase 1: additive lifecycle/payment-details tables; explicit synthetic historical
snapshot provenance, net-of-fee three-way checks, rail/merchant exposure summaries.
120 Python tests passed, one Docker skip; lifecycle Playwright passed, build and
original smoke passed. Schema initialization/backfill are idempotent.

Phase 2: pricing snapshots, margin attribution/rankings, fee-audit Decisions through
the existing gate/audit and constrained multilingual margin explanations.
125 Python tests passed, one Docker skip; 2 extension browser tests, build and
original smoke passed. Fee excess is counted once; loss/recovery is not inferred
from an analyst approval. Statistical fee flags show sample size and z-score.

Phase 3: reporting-only rupee impact, label coverage, recovery ledger, expected recovery and explicit workload/scaling assumptions. 126 Python tests passed (one Docker skip), 3 extension Playwright tests, build and original smoke passed.

Phase 4: four append-only incident scenarios, routed by existing agents/gate with incident audit/activity events. 130 Python tests passed (one Docker skip), 4 extension browser tests, build and smoke passed. Duplicate-file reference generation was corrected after an invariant test found hidden duplicates.

Phase 5: immutable original 512/608 holdout replay and threshold curve, mandatory gates and Wilson intervals. 131 Python tests passed (one Docker skip), 5 extension browser tests, build and smoke passed. No policy or operational audit data changes during replay.

Phase 6: tokenized synthetic BIN/issuer diagnostics, Fisher tests and minimum samples; contextual LinUCB with bounded shifts and human-only ROUTING_CHANGE Decisions. 133 Python tests passed (one Docker skip), 6 extension browser tests, build and smoke passed. Statistical outlier test uses 512 payments to meet the unchanged sample guardrail.

Phase 7: review/holdout quality, Wilson-aware proposals, transactional human-approved type limits and review/evaluation-triggered safer-only rollback. 134 Python tests passed (one Docker skip), 7 extension browser tests, build and smoke passed. Historical predictions remain unchanged; restricted actions never become automatic. Report reads were batched after a slow browser lookup was observed.

Phase 8 and final steps: masked/tokenized card references, grouped PAN rejection and JSON/log masking, DB/log/API scans; default-off Sarvam STT/TTS with three-language synthetic live loopback. 142 host tests passed with Docker acceptance enabled; 141 passed and one opt-in skip in the rebuilt Linux container. All 12 browser tests passed on Vite and nginx. Make test/demo/eval, original 30-case evaluation and new measured extension reports passed. Physical microphone/playback remain unverified. The lifecycle mismatch test was strengthened so a clearing gap cannot be labeled CLEAN. No .env contents changed. See EXTENSION_STATUS.md and DEMO_SCRIPT.md.
