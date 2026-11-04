# PayOps Brain

Synthetic payments dispute assistant, built from scratch for the hackathon.
Phase 1 implements the API adapter and deterministic offline fixtures.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe gen_data.py
.\.venv\Scripts\python.exe scripts/check_api.py
```

Copy `.env.example` to `.env` and configure keys locally to test real APIs with
`python scripts/check_api.py --require-live`. No real API success is claimed yet.
