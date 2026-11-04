"""Phase gate: exercise offline HTTP flow without a running server."""
import os
os.environ['PAYOPS_MOCK'] = 'true'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.main import app

with TestClient(app) as client:
    assert client.get('/health').status_code == 200
    queue = client.get('/disputes').json()
    assert len(queue) >= 7
    result = client.post('/disputes/D001/run', json={'note': 'Review the duplicate debit.'}).json()
    assert result['action'] == 'REFUND', result
    assert result['verification']['passed'], result
    assert len(result['trace']) >= 5
    decision = client.post('/disputes/D001/decision', json={'decision': 'APPROVE', 'run_id': result['run_id']})
    assert decision.status_code == 200, decision.text
    assert not decision.json()['event']['payment_executed']
    assert client.get('/notices/D001.png').status_code == 200
    print('PASS: queue, notice, agent trace, verifier and human decision (offline)')
