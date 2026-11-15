# Implementation inventory and phase log

Baseline: commit 47a50dc, main. No existing local reconciliation or Docker files
were found, including untracked workspace files. Original modules and API
contracts are retained.

| Area | Inventory |
|---|---|
| Dispute graph, Meta adapters, rules, verifier, voice | REUSE |
| Decision schemas, approval, React workspace | EXTEND |
| SQLite, simulator, audit, reconciliation, fraud, feedback | NEW |
| Sarvam provider and multilingual merchant assistant | NEW |
| Real Meta/Baseten/Sarvam/voice verification | BLOCKED: credentials absent |

## Original baseline

Python 3.12.3; isolated .venv. Original test files: 68 passed. Original smoke and
offline API checks passed. Original Vite production build passed and dev server
returned HTTP 200. Uvicorn started on 127.0.0.1:8000. No credentialed requests made.
Existing reports are historical artifacts, not fresh live verification.

## Phase 1

SQLite uses foreign keys, indexed references, integer paise and UTC timestamps.
Simulator appends idempotent deterministic batches across CARD/UPI/NET_BANKING.
Seven injected anomaly types have direct ledger invariant tests. Evaluation
labels are in a separate sibling .truth.sqlite3, unavailable through ledger APIs.
The common Decision contract, configurable policy and append-only hash-chained
audit foundation are included. Only bookkeeping/no-action may auto-resolve;
restricted actions require a person and no integration moves money.

## Phase 2

Exact and normalized reference matching precede guarded fuzzy/gradient-boosted
scoring. Numeric reference identity, merchant, rail, amount and timing constrain
candidates; ambiguous candidates are reviewed. Seven break classes use ledger
invariants. Prediction persistence verifies cited IDs and ledger amounts before
creating queue/audit rows. 91 tests passed; original smoke passed; /health remained
available. No operational ground-truth labels are read by inference.

## Phase 3

Original LangGraph gains an additive intelligence result without changing its
six-step evidence trace. Unified chargebacks have reason codes, weighted evidence
checklists, deadlines, fight/accept recommendations and a logistic win model
trained on 2,000 separate synthetic outcomes (seed 732). Evidence confidence and
win probability are distinct. Checklist weights are .20 reference, .18 settlement,
.16 authentication, .16 delivery, .12 deadline, .18 signed receipt; the last is
explicitly missing. No score is forced for the demo. Sarvam/Meta/local provider
selection composes only approved sentences and falls back safely. 100 tests passed,
including stubbed rate-limit/error/hallucination paths; original smoke passed.

## Phase 4

Fraud combines an Isolation Forest trained on 800 separate synthetic normal
feature vectors (seed 991) with per-merchant 60-second velocity, refund ratio,
device risk and merchant amount deviations. Alerts cite transactions/refunds and
never disable processing. 102 tests passed; original smoke and health passed.

## Phase 5

Persistent queue APIs use transactional version checks. Original predictions are
immutable; corrections store original/corrected decisions, reason, features and
UTC timestamp. Approvals/rejections/edits and legacy dispute decisions append
audit events. Kill-switch suggestions require a separate explicit human approval
and record no processing execution. Logistic confidence recalibration uses a
300-sample synthetic prior (seed 661) plus weighted analyst feedback, evaluates a
separate 300-sample synthetic holdout (seed 662), and reports before/after Brier
scores and review estimates without claiming improvement. Future decisions use
the recorded calibrator; historical cases are not silently rewritten.
107 tests passed; original smoke passed; backend restarted successfully.

Sarvam live text integration check succeeded on 2026-11-15 using sarvam-105b.
The key remains only in ignored .env. Ordinary pytest continues in mock mode.

## Phase 6

Merchant assistant computes scoped gross/fees/net, missing/short/duplicate counts
and dispute counts in Python before provider composition. English, Hindi and
Tamil templates share the same computed fact object. Unknown merchants, unsupported
questions and settlement-time predictions route to an analyst. Free-form financial
generation is deliberately unavailable. 111 tests passed; original smoke passed.

## Phase 7

Control tower retains the original dispute workspace and adds operational
navigation, Python-computed metrics, exception bars, ledger table, simulator
batches/continuous mode, activity, evidence case files, review edits, fraud
recommendations, audit and multilingual assistant. Vite preserves /api on new
routes while forwarding original routes compatibly. Bulk agent runs use local
drafts; live provider drafts require an explicit request. 114 Python tests,
2 Playwright browser tests and production build passed. Browser tests exercised
simulation, chargeback approval, correction, calibration, audit, original notice
workflow and mobile viewport overflow. A browser-only badge rendering crash was
found and fixed before proceeding.

## Phase 8

Separate held-out ledger seed 916 contains 512 transactions and 608 agent cases.
Rules-only/assisted auto-match rates: .625/.8125; classification: .6875/1.0;
win AUC: .5/.6745 (32 outcomes); fraud precision .5 and recall 1.0 for both;
human review .7368/.6316; false auto-resolution observed 0 for both. Reports
contain sample counts, Wilson intervals, exact training provenance and generator
limitations. 115 tests passed. The simulator now includes normalized and noisy
references to exercise assisted matching; Windows SQLite handle cleanup was fixed.
Optional routing/KYC/credit agents are not implemented; they are outside the
required eight phases and add no validated value to this demo.

## Final packaging and validation

Compose serves FastAPI plus nginx/React with a persistent volume, healthcheck,
runtime-only environment keys and an unprivileged backend user. A locked Python
environment and optional ignored wheel cache handle slow package downloads.
Make install/test/seed/demo/eval targets were executed with GNU Make 4.2.1.
Local ordinary suite: 118 passed, 1 Docker opt-in skip. Docker-enabled host suite:
119 passed. Container ordinary suite: 118 passed, 1 skipped. Three Playwright
tests passed against both Vite and Docker nginx. Live Sarvam grounded checks passed
in English, Hindi and Tamil. Both evaluations, smoke, pip check and HTTP acceptance
checks passed. Meta/Baseten/real voice remain unverified. See implementation-report.md.
