# PayOps Brain implementation report

Validation date: 2026-11-15 (Asia/Calcutta). Scope: a local synthetic prototype,
not production payments, regulatory validation or a real-world ML benchmark.
Existing work started at 47a50dc on main with a clean tree. Original routes,
tests, fixture data and dispute workspace were retained. Phase commits are in Git;
no commits have been pushed remotely.

| Feature | Status | Evidence |
|---|---|---|
| Existing dispute workflow | PARTIALLY WORKING | Original 68 tests, smoke, 30-case fixture evaluation and browser flow pass; live Meta/Baseten/voice not verified in this session |
| Synthetic simulator | FULLY WORKING | CARD/UPI/NET_BANKING batches/continuous worker; seven anomaly invariant tests; browser batch controls |
| Unified ledger | FULLY WORKING | Integer-paise SQLite, foreign keys, indexes, additive initialization, persistent Docker volume; labels in separate DB |
| Reconciliation agent | FULLY WORKING | Exact/normalized/fuzzy GB matching, learned break classifier, invariant agreement, transaction-bound evidence checks |
| Confidence gate | FULLY WORKING | Boundary/override tests, high-value/expert rules, restricted actions never auto-execute |
| Audit log | FULLY WORKING | Same-transaction events, SQL update/delete guards, hash-chain verification/tamper tests, audit browser screen |
| Dispute intelligence | FULLY WORKING | Reason codes, weighted checklist, deadlines, logistic synthetic win estimate, fight/accept, grounded drafts |
| Fraud agent | FULLY WORKING | Isolation Forest + device/velocity/refund/merchant rules; explicit suggestion/approval workflow; no network execution |
| Human review | FULLY WORKING | Approve/reject/edit APIs and UI, stale versions, concurrent approval test, original prediction retained |
| Feedback and recalibration | FULLY WORKING | Labeled corrections, logistic recalibration, independent synthetic holdout Brier scores, review estimates, persisted model parameters |
| Sarvam integration | FULLY WORKING | Official V1 contract, configurable model/key/timeout, JSON mode, low reasoning, stubbed failure tests; live en/hi/ta checks passed |
| Merchant assistant | FULLY WORKING | Python ledger facts, exact-sentence gate, English/Hindi/Tamil, unknown scope/time routed to analyst |
| Dashboard | FULLY WORKING | Ten navigation views, backend metrics, evidence/review/audit/simulator/activity/evaluation, desktop/mobile browser checks |
| Evaluation | FULLY WORKING | Reproducible 512-transaction/608-case holdout, rules/assisted results, counts, Wilson intervals and confusion matrix |
| Docker | FULLY WORKING | Compose backend health + nginx frontend startup; HTTP/proxy checks; container Python suite; browser tests against nginx |
| Optional routing/fee/KYC/credit agents | NOT IMPLEMENTED | Intentionally outside the required eight phases; fee mismatches are covered by reconciliation |

“FULLY WORKING” refers to the documented synthetic-demo behavior only. It does
not imply real financial execution, unrestricted language generation, production
security, production ML calibration or verified Meta model entitlement.

## Exact executed validation

From `D:\payops\payops-brain`, using Python 3.12.3 in `.venv`:

| Command | Observed result |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_eval.py tests/test_models.py tests/test_rules.py tests/test_verify.py` | Original baseline: **68 passed** |
| `.venv\Scripts\python.exe -m pytest --tb=short` | Final ordinary suite: **118 passed, 1 skipped** (Docker HTTP test is opt-in) |
| `$env:PAYOPS_DOCKER_TEST='1'; .venv\Scripts\python.exe -m pytest --tb=short` | **119 passed**, including running-stack HTTP test |
| `.venv\Scripts\python.exe scripts/smoke.py` | Passed: original HTTP flow, fixture voice, redaction, verification, human decision |
| `.venv\Scripts\python.exe scripts/check_api.py` | Passed explicitly as offline fixtures, not live Meta |
| `.venv\Scripts\python.exe scripts/check_sarvam.py --require-live` | **3/3 live grounded checks**: en, hi, ta; provider sarvam, model sarvam-105b |
| `.venv\Scripts\python.exe scripts/eval.py` | **30/30** actions, **31/31** valid IDs, **30/30** verifier passes, 12 escalations, zero agent errors |
| `.venv\Scripts\python.exe scripts/eval_control_tower.py` | 512 held-out transactions, 608 agent cases; report saved under reports/ |
| `.venv\Scripts\python.exe -m backend.demo` | Seed + agents + queue + evaluation completed; repeated seed preserved prior history |
| `.venv\Scripts\python.exe -m pip check` | No broken requirements |
| `npm.cmd ci`, `npm.cmd run build` (frontend directory) | Passed; production assets compiled |
| `npx.cmd playwright test` (frontend directory) | **3 passed** against Vite |
| `$env:PAYOPS_UI_URL='http://127.0.0.1:8080'; npx.cmd playwright test` | **3 passed** against Docker nginx |
| `docker compose config --quiet` | Configuration validated without printing environment secrets |
| `$env:BACKEND_PORT='8001'; $env:FRONTEND_PORT='8080'; docker compose -p payops-brain-validation up --build -d` | Images built, backend healthy, frontend started |
| `docker compose -p payops-brain-validation exec -T backend python -m pytest --tb=short` | Linux container: **118 passed, 1 skipped** |
| `.venv\Scripts\python.exe scripts/check_stack.py --backend http://127.0.0.1:8001` | Backend/frontend HTTP 200, legacy/new proxy paths passed, audit chain valid, evaluation present |
| `"C:\Program Files\CodeBlocks\MinGW\bin\mingw32-make.exe" NPM=npm.cmd install test seed demo eval` (activated .venv and Node PATH) | All five Make targets passed; test target: **118 passed, 1 skipped**, smoke/build passed |
| `"C:\Program Files\CodeBlocks\MinGW\bin\mingw32-make.exe" run` | Uvicorn started successfully on 127.0.0.1:8000; /health passed |

The browser suite exercises simulator generation, all three rails, UPI checklist
and approval, analyst correction and recalibration, audit integrity, the original
notice workflow, mobile overflow, explicit fraud suggestion/approval and evaluation
refresh. It does not test physical microphone input or invoke live providers.

## Measured evaluation

See [full report](../reports/control_tower_eval.md) and
[machine-readable report](../reports/control_tower_eval.json).

| Metric | Rules-only | Assisted |
|---|---|---|
| Auto-match rate | 62.50% (320/512) | 81.25% (416/512) |
| Break classification accuracy | 68.75% (352/512) | 100.00% (512/512) |
| Dispute-win AUC | .5000 | .6745 (32 outcomes) |
| Fraud precision | 50% (32/64) | 50% (32/64) |
| Fraud recall | 100% (32/32) | 100% (32/32) |
| Human-review rate | 73.68% (448/608) | 63.16% (384/608) |
| False bookkeeping auto-resolutions observed | 0/160 | 0/224 |

No fraud improvement is claimed. Zero observed false auto-resolutions has a
nonzero confidence-interval upper bound. Training and test seeds differ but share
synthetic assumptions. These results are not OCR/redaction/LLM accuracy or
real-world payment outcomes. Feedback recalibration is measured separately; a
change may worsen the holdout score and the UI reports that rather than claiming
an improvement.

## Important boundaries

- The local Sarvam key is in ignored `.env`; it is never committed or baked into
  either image. Configuration and provider errors expose no key values.
- Providers may only compose approved fact sentences. This protects unsupported
  money/status/root-cause claims at the cost of creative language generation.
- Bulk agent runs draft locally. Provider generation is explicit, to avoid
  unsolicited paid calls. Ordinary tests need no credentials.
- No real customer, card, account or transaction data is used. Original mock
  extraction reads sidecars; fixed voice transcripts do not recognize speech.
- Live Meta extraction/drafting, requested Baseten model ID, real voice and
  physical microphone remain unverified. No such live success is claimed.
- Unified decisions/reviews/audit persist; original notice-session queue resets
  on restart. Use one backend process. No authentication or production deployment.
- The hash chain is protected against ordinary application updates/deletes, not
  against an administrator rewriting the complete database and chain.
- Kill-switch approval is an audit record; it does not disable real processing.
  Arbitration, refunds, write-offs and policy changes are not executed by agents.
- No optional routing, fee-audit, KYC or credit agent and no recorded demo video.

## Build notes

The first Docker dependency download timed out. Versions were locked to the
validated environment and a local ignored `.wheelhouse` of official PyPI Linux
wheels completed the same Docker build. Docker uses that cache when present and
otherwise downloads the lock normally. Keys are excluded from the build context.
The cache and runtime databases are not committed.

An initial `make install` attempt hit Windows' esbuild file lock while Vite was
running. Stopping the owned dev servers and rerunning completed successfully.

Final restart-persistence acceptance retained **2 human-reviewed cases** and
**246 unchanged historical audit hashes**; chain integrity passed after the
backend restart. Final rerun: host **119 passed**, container **118 passed, 1 skipped**.
The image filesystem contains no `/app/.env`; credentials are runtime environment
configuration. The staged-source secret scan covered 149 tracked files and passed.

The running validation stack uses http://localhost:8080 and backend docs at
http://localhost:8001/docs to avoid the local backend port. Its project name is
`payops-brain-validation`; stop it without deleting data using
`docker compose -p payops-brain-validation down`.
