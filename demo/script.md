# PayOps Brain: three-minute control tower demo

Start with `docker compose up --build` (http://localhost:8080), or run
`python -m backend.demo`, Uvicorn and Vite. Use a fresh synthetic seed if earlier
reviews are closed. Keep credentials and private browser tabs off-screen.
All displayed totals and results come from real application behavior.

| Time | Action and narration |
|---|---|
| 0:00–0:15 | Overview: “One synthetic ledger, three payment rails, three reviewable agents. No money moves.” |
| 0:15–0:30 | Enter a new seed, batch size 32, start a batch. Open Transactions and show CARD, UPI, NET_BANKING. Continuous mode is optional; stop it before the rest of the demo. |
| 0:30–0:50 | Reconciliation: open missing, short and duplicate cases. Show actual settlement evidence and explain exact/normalized/fuzzy matching. Eligible bookkeeping closes automatically; financial actions do not execute. |
| 0:50–1:20 | Disputes: open an OPEN UPI chargeback with available authentication/delivery evidence. Show checklist, missing signed receipt, deadline, fight/accept and win estimate. Evidence confidence near .82 appears only when the documented checks support it. Click Generate provider draft and show its actual provider/mode. |
| 1:20–1:35 | Enter a comment and approve. Audit Trail: show HUMAN APPROVE, immutable prediction, evidence, UTC time and hash-chain integrity. |
| 1:35–1:55 | Review Queue: edit a different OPEN case, choose corrected action and give a reason. Recalibrate from feedback. Show before/after holdout Brier and review estimates; say whether quality improved or worsened, based on the displayed numbers. |
| 1:55–2:10 | Evaluation: show measured rules/assisted scoreboard, sample counts and synthetic limits. Fraud precision is 50% in the saved run; do not claim an ML gain. |
| 2:10–2:35 | Merchant Assistant: choose a synthetic merchant, ask “Why is my settlement short?” in English, Hindi and Tamil response modes. Show computed ledger facts and provider/mode. If Sarvam is unavailable, identify local fallback honestly. |
| 2:35–2:50 | Fraud: open burst alert and show velocity/refund evidence. Suggest a kill switch. Explain that explicit human approval is required and that even approval only records a recommendation in this demo. |
| 2:50–3:00 | Return to Overview: “Synthetic-data validation, grounded explanations and an inspectable audit. Humans retain financial control.” |

## Rehearsal checks

- Run Pytest, original smoke and both evaluations; build the frontend.
- Confirm the configured provider on the status badge and a live merchant response.
- Prepare an OPEN chargeback and a separate OPEN correction case.
- Rehearse at 1440×1000 or 1920×1080. Mark any latency cut as a time cut.
- Original notice workflow remains under Disputes → Open original notice workflow.
  Its extraction/draft are fixtures without Meta credentials; do not imply OCR.
- Voice is optional and unverified live. Omit it from this script until verified.
- Do not claim regulatory compliance, production ML accuracy, private hosting,
  actual refunds, arbitration, payment restrictions, or a recorded video.
