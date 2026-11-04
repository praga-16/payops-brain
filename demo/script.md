# PayOps Brain · three-minute demo

Total: 180 seconds. Record at 1920×1080, browser around 100% zoom. Restart the
backend to reset the queue. Start both servers, open http://127.0.0.1:5173, select
D001, prepare a 5–10-second mono PCM WAV or use Record note. Rehearse once.
Recording and export are manual.

If real checks have not passed, show **Offline fixture mode** and use the offline
wording below. Do not imply the fixed transcript recognizes speech or call the
offline eval a vision benchmark. Mark any latency cut visibly as a time cut.

| Time | Screen / action | Narration |
|---|---|---|
| 0:00–0:15 | Queue, then rotated D001 notice | “Disputes start as messy notices. Operators need to connect them to ledger evidence and decide what happens next. PayOps Brain proposes a resolution, checks its claims, and keeps the final decision with a human.” |
| 0:15–0:35 | Synthetic label and notice; record/upload short note | “This is a rotated, entirely synthetic duplicate-debit notice. I'll add a note: review both debit records before approving a refund.” Offline: “Voice is a fixed transcript fixture in this offline demo.” |
| 0:35–1:00 | Confirm transcript; click Run agent | Live: “Muse Voice transcribes the recording, then Muse Spark reads the image.” Offline: “This run uses fixture extraction and drafting, so it works without API keys.” |
| 1:00–1:25 | Extract, Match, Rules trace; model and mode | “LangGraph tracks each step. Matching uses the transaction reference. Policy sees two settled debits with matching amounts and dates, so it recommends a refund. These are explicit demo rules.” |
| 1:25–1:45 | Original vs redacted trace, then reply | “Before drafting, identity fields are dropped and the note is scrubbed. The configured live path uses Muse Spark Open on Baseten here; offline it is a local scrub. The draft contains structured claims; the reply is rendered from checked facts.” |
| 1:45–2:05 | Verifier panel and cited ledger rows | “The verifier checks every ID, transaction, amount, date and status, and checks the action against policy. A citation that merely looks plausible is not enough.” |
| 2:05–2:30 | Challenge the verifier; Inject bad citation | “I inject a nonexistent citation into a copy. This is a deliberate test, not an actual model mistake. The verifier blocks the draft and escalates. The original reviewable result stays unchanged.” |
| 2:30–2:45 | Comment, approve recommendation, recorded decision | “I review the actual evidence and approve. This records my review. It never moves money, and a stale or already-reviewed run cannot be approved again.” |
| 2:45–3:00 | eval_results.md, return briefly to model trace | “Thirty synthetic offline cases: thirty correct actions, thirty-one valid citations, twelve escalations. These test the workflow, not model accuracy. Open weights offer deployment options; hosted Baseten isn't private hosting. Every case still needs a human.” |

## Before recording

* Run `python scripts/check_api.py`, `python scripts/smoke.py`, `python -m pytest`
  and `npm.cmd run build` from the appropriate directories.
* For live claims, run `python scripts/check_api.py --require-live --all` and
  optionally `--voice note.wav`. Confirm the Baseten model ID/base URL. Show real
  trace modes, including any mixed/mock steps.
* Keep populated `.env`, keys, account dashboards and private browser tabs out of
  the recording. All notices, names and payment references must be synthetic.
* Rehearse microphone permission and conversion; upload supported WAV if needed.
  The offline transcript is always a labeled fixed fixture.
* Inspect layout at the recording resolution. Automated visual QA was blocked by
  the local browser/app connection during development.
* Do not claim private hosting, compliance, OCR accuracy from offline numbers,
  real refunds, durable logs, or live API success without separately testing it.
