"""Phase gate: exercise offline HTTP flow without a running server."""
import os
import io
import wave
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
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b'\0\0' * 2400)
    voice = client.post('/disputes/D001/voice', files={'audio': ('note.wav', buffer.getvalue(), 'audio/wav')})
    assert voice.status_code == 200, voice.text
    assert voice.json()['mode'] == 'mock'
    result = client.post('/disputes/D001/run', json={'note': voice.json()['transcript']}).json()
    assert result['action'] == 'REFUND', result
    assert result['verification']['passed'], result
    assert [t['step'] for t in result['trace']] == ['voice','extract','match','rules','redact','draft','verify']
    assert 'customer_name' not in result['redacted']
    bad = client.post('/disputes/D001/verify-demo').json()
    assert bad['action'] == 'ESCALATE' and not bad['verification']['passed'], bad
    assert client.get('/disputes/D001').json()['result']['verification']['passed']
    decision = client.post('/disputes/D001/decision', json={'decision': 'APPROVE', 'run_id': result['run_id']})
    assert decision.status_code == 200, decision.text
    assert not decision.json()['event']['payment_executed']
    assert client.get('/notices/D001.png').status_code == 200
    print('PASS: queue, WAV upload, mock voice, redaction, agent trace, bad-citation demo and human decision (offline)')
