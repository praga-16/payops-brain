# Two-minute synthetic operations demo

Prepare with `make demo` (Windows: GNU Make with `NPM=npm.cmd`), or
`python -m backend.demo`. Start the local servers or `docker compose up --build`.
Open `http://localhost:8080/?view=Guided%20Demo` (Vite: port 5173).
Use synthetic data only. Do not show environment files or keys.

| Time | Tested action / honest narration |
|---|---|
| 0:00–0:15 | Guided Demo → Money Flow. Copy an ID from Transactions and track it. “These authorization/clearing snapshots are synthetic. Settlement is net of fees, and a pending gap is not automatically a realized loss.” |
| 0:15–0:30 | Profit & Margin. Switch merchant/rail/BIN ranking and expand a loss reason. “Pricing is snapshotted. Fee cost and leakage come from ledger records, not an LLM calculation.” |
| 0:30–0:40 | Rupee Impact. “Recorded recovery is separate from potential exposure and modeled expected recovery. Per-100,000 scaling and minutes-per-touch are explicit assumptions.” |
| 0:40–0:55 | Live Incidents → UPI bank outage. Wait for completion; show new queue/activity entries. “The simulator creates new synthetic cases and agents investigate them. No bank or payment setting changed.” |
| 0:55–1:10 | BIN & Routing. Expand the outage context, inspect sample counts and bounded uplift, queue routing suggestions. “LinUCB proposes a limited shift from synthetic trial results. It cannot change a route; approval records advice only.” |
| 1:10–1:25 | What-if Autonomy. Move the slider. “This replays 512 transactions / 608 original agent cases without changing policy. Restricted actions remain human-only. Zero observed errors does not prove zero risk.” |
| 1:25–1:40 | Earned Autonomy → Assess. Open a proposal in Review Queue and inspect its basis. Approve only after review. “More autonomy requires approval and sufficient evidence. A quality drop automatically tightens an approved limit. The full rollback behavior is unit-tested; do not pretend a drop occurred in this short run.” |
| 1:40–1:50 | Security → scan. “References are tokenized or masked. Pattern checks cover DB values, logs and JSON APIs, with known limitations. This is not PCI certification.” |
| 1:50–2:00 | Merchant Assistant, choose a response language. “English, Hindi and Tamil explanations pass a fact gate. Synthetic TTS/STT loopback passed in all three; the physical microphone is unverified and speech stays off by default.” |

For a longer walkthrough, submit an actual analyst correction, recalibrate and show
the measured before/after scores without promising improvement. Follow the original
notice workflow from Disputes if desired; it remains mock extraction without Meta
credentials. Mark latency edits as visible time cuts. No video was recorded.
