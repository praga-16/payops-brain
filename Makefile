PYTHON ?= python
NPM ?= npm
.PHONY: install test seed demo eval run frontend
install:
	$(PYTHON) -m pip install -r requirements.txt
	cd frontend && $(NPM) ci
test:
	$(PYTHON) -m pytest
	$(PYTHON) scripts/smoke.py
	cd frontend && $(NPM) run build
seed:
	$(PYTHON) -m backend.simulator
demo:
	$(PYTHON) -m backend.demo
eval:
	$(PYTHON) scripts/eval.py
	$(PYTHON) scripts/eval_control_tower.py
run:
	$(PYTHON) -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
frontend:
	cd frontend && $(NPM) run dev
