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
