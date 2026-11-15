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
