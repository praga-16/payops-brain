# Current synthetic operations extension status

Validated 2026-11-15, Asia/Calcutta. This report supersedes the feature inventory
in the historical build-163cc47 report. “FULLY WORKING” means the documented
synthetic prototype behavior, not production financial processing or real-world
model accuracy.

| Feature | Status | Evidence |
|---|---|---|
| Existing dispute workflow and original APIs | FULLY WORKING | Original tests retained; smoke, 30-notice offline evaluation and original browser flow pass |
| Lifecycle tracker and three-way checks | FULLY WORKING | `test_moneyflow.py`; browser lookup; 288/288 clean checks and 96/96 injected gaps in measured report |
| Idempotent additive migration/backfill | FULLY WORKING | Repeated initialization test; existing Docker volume upgraded without clearing data; historical stage provenance displayed |
| Profit/margin rankings and ledger reasons | FULLY WORKING | `test_margins.py`; merchant/rail/BIN tables and reasons exercised in browser |
| Dedicated fee-audit agent | FULLY WORKING | Shared Decision/gate/audit; RAISE_CLAIM is expert-only; 64/64 measured discrepancies, no extra claims in sample |
| Multilingual margin explanations | FULLY WORKING | English/Hindi/Tamil approved-fact tests through existing exact-sentence gate |
| Rupee impact and per-100,000 normalization | FULLY WORKING | `test_impact.py`; arithmetic, recovery-entry separation, assumptions and browser view |
| Four live synthetic incident scenarios | FULLY WORKING | Parametrized scenario API/invariant tests; browser triggers new outage cases; agents/gate/activity process records |
| What-if autonomy replay | FULLY WORKING | Read-only audit-state test, original 512/608 denominator, mandatory gates, Wilson intervals and slider browser test |
| BIN/issuer diagnostics and outliers | FULLY WORKING | Success/decline/dispute/fraud/cost aggregations, Fisher/sample tests, browser view; historical authorizations explicitly inferred |
| Contextual-bandit routing advice | FULLY WORKING | LinUCB with min samples/maximum shift; approval does not change routes; outage trial measured from 256 observations per arm |
| Earned-autonomy proposals and application | FULLY WORKING | Approval required, stale-state checks, measured review/holdout quality; `test_earned_autonomy.py` |
| Automatic safer rollback | FULLY WORKING | Review-triggered test tightens .94 to .99 after poor reviews; no automatic increase in autonomy |
| Sarvam STT/TTS with language detection | PARTIAL | Mocked unit/API contracts and live generated-speech loopback passed en/hi/ta; physical microphone and speaker playback unverified; feature off by default |
| Card-reference security checks | FULLY WORKING | DB/captured-log/JSON response scans, grouped PAN input rejection, log filtering, masked fixtures and browser security scan |
| Guided demo, evaluation and Docker | FULLY WORKING | Make test/demo/eval, guided browser links, Compose health/HTTP checks, container suite and nginx browser suite |
| Real bank/route/refund/arbitration execution | NOT IMPLEMENTED | Intentionally no financial-network execution; approvals record suggestions except explicitly approved synthetic autonomy limits |
| Live Meta/Baseten/Muse Voice verification | PARTIAL | Adapters retained; offline modes pass; no new live verification claimed |

## Exact validation commands and counts

Run from `D:\payops\payops-brain` unless marked frontend:

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest --tb=short` | **141 passed, 1 skipped** (Docker HTTP acceptance is opt-in) |
| `$env:PAYOPS_DOCKER_TEST='1'; .venv\Scripts\python.exe -m pytest --tb=short` | **142 passed**, including running-stack acceptance |
| `.venv\Scripts\python.exe scripts/smoke.py` | Original offline flow passed |
| `.venv\Scripts\python.exe scripts/eval.py` | 30/30 actions, 31/31 cited IDs, 30/30 verifier passes; fixtures, not OCR accuracy |
| `.venv\Scripts\python.exe scripts/eval_control_tower.py` | Original held-out results reproduced with 512 transactions / 608 cases |
| `.venv\Scripts\python.exe scripts/eval_extensions.py` | Measured extension report saved with counts and Wilson intervals |
| `.venv\Scripts\python.exe scripts/check_sarvam_speech.py --live` | 3/3 generated synthetic TTS→STT checks passed; en/hi/ta detected correctly |
| GNU Make 4.2.1: `mingw32-make NPM=npm.cmd test demo eval` with Node/.venv on PATH | All targets passed; no human approvals, recoveries or policy relaxations fabricated by demo |
| Frontend: `npx.cmd playwright test` | **12 passed** against Vite |
| Frontend: `$env:PAYOPS_UI_URL='http://127.0.0.1:8080'; npx.cmd playwright test` | **12 passed** against Docker nginx |
| Frontend: `npm.cmd run build` | Production build passed |
| `BACKEND_PORT=8001 FRONTEND_PORT=8080 docker compose -p payops-brain-validation up --build -d` (PowerShell environment equivalents used) | Rebuilt images; backend healthy and frontend running |
| `docker compose -p payops-brain-validation exec -T backend python -m pytest --tb=short` | **141 passed, 1 skipped** in Linux container |
| `.venv\Scripts\python.exe scripts/check_stack.py --backend http://127.0.0.1:8001` | HTTP/proxy, audit integrity and original evaluation acceptance passed |
| `.venv\Scripts\python.exe -m pip check` | No broken requirements |

## Measured results and limits

See [extensions_eval.md](../reports/extensions_eval.md) and its JSON counterpart.
The 95% Wilson lower bounds are approximately .9868 for 288/288 clean checks,
.9615 for 96/96 gap detections, and .9434 for 64/64 fee precision/recall. These
are finite synthetic samples, not proof of zero risk. The outage report's bounded
10% traffic-shift proposal has .063671875 estimated success-rate uplift, using
256 synthetic trials per route. No route was changed or real uplift measured.

Pricing is an explicit synthetic contract, not bank invoice data. Pending exposure
is not cash loss; approvals do not create recovery entries. Expected recovery and
hours saved are model/assumption-based estimates. BIN history is synthetic/inferred
where stated. Review agreement is a noisy correctness label. Simulated route trials
share generator assumptions and do not establish production improvement.

Card references were masked in existing fixture JSON and regenerated notice PNGs;
financial amounts, case labels and original routes were retained. The original
30-case fixture evaluation passed after regeneration. Pattern scans exclude
embedded hashes/IDs and decimal fractions and are not comprehensive DLP or PCI
certification. The old live Meta report is historical and does not verify the
regenerated images.

No `.env` contents were changed. No keys or audio are committed. Speech is disabled
unless the operator explicitly enables `PAYOPS_SARVAM_VOICE` in the process
environment. New speech requests preserve the existing fact gate. No physical
microphone, speaker output, real payment/customer data or production deployment
was used or validated.

Open the running guided walkthrough at
http://localhost:8080/?view=Guided%20Demo and follow [DEMO_SCRIPT.md](DEMO_SCRIPT.md).
