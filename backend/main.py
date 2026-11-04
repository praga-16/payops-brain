import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from backend.config import ROOT, model_config
from backend.graph import read_data, run_case
from backend.schemas import RunRequest, DecisionRequest
from backend.voice import transcribe, MAX_BYTES, voice_config
from backend.meta_client import ModelError
from backend.verify import verify_draft, render_reply

app = FastAPI(title='PayOps Brain', version='0.2.0')
app.add_middleware(CORSMiddleware, allow_origins=(os.getenv('CORS_ORIGINS') or
                   'http://localhost:5173,http://127.0.0.1:5173').split(','),
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
# Only generated PNGs are served; sidecars and labels are never static resources.
lock = threading.RLock()
cases = {d['id']: {**d, 'status': 'QUEUED', 'result': None, 'decisions': [], 'running': False} for d in read_data('disputes.json')}


def get_case(did):
    if did not in cases:
        raise HTTPException(404, 'Dispute not found')
    return cases[did]


@app.get('/health')
def health():
    vc = voice_config()
    return {'ok': True, 'synthetic_only': True, 'voice': {k: vc[k] for k in ('model', 'mode')},
            'models': {s: model_config(s).public() for s in ('extract', 'redact', 'draft')}}


@app.get('/disputes')
def queue():
    with lock:
        return [{k: deepcopy(v) for k, v in c.items() if k not in ('result', 'decisions')}
                | {'action': c['result']['action'] if c['result'] else None} for c in cases.values()]


@app.get('/disputes/{did}')
def detail(did: str):
    with lock:
        return deepcopy(get_case(did))


@app.get('/notices/{filename}')
def notice(filename: str):
    from fastapi.responses import FileResponse
    if not filename.endswith('.png') or filename[:-4] not in cases:
        raise HTTPException(404, 'Notice not found')
    return FileResponse(ROOT / 'data/disputes' / filename, media_type='image/png')


@app.post('/disputes/{did}/run')
def run(did: str, body: RunRequest):
    with lock:
        case = get_case(did)
        if case['running']:
            raise HTTPException(409, 'This case is already running')
        if case['status'] in ('APPROVED', 'REJECTED'):
            raise HTTPException(409, 'Reviewed cases are closed for this session')
        case['running'] = True
        snapshot = {k: deepcopy(case[k]) for k in ('id', 'title', 'rail', 'amount', 'received_date', 'image')}
        voice = deepcopy(case.get('voice'))
    try:
        note = body.note if body.note is not None else voice['transcript'] if voice else ''
        result = run_case(snapshot, note=note)
        if voice and note == voice['transcript']:
            result['trace'].insert(0, {'step': 'voice', 'model': voice['model'], 'mode': voice['mode'],
                                      'status': 'completed', 'duration_ms': 0,
                                      'detail': {'transcript': voice['transcript'], 'source': 'previous audio upload'}})
        with lock:
            case.update(result=result, status='AWAITING_REVIEW')
        return result
    finally:
        with lock:
            case['running'] = False


@app.post('/disputes/{did}/decision')
def decision(did: str, body: DecisionRequest):
    with lock:
        case = get_case(did)
        if case['running'] or case['status'] != 'AWAITING_REVIEW' or not case['result']:
            raise HTTPException(409, 'Run the agent and review its latest result first')
        if case['result']['run_id'] != body.run_id:
            raise HTTPException(409, 'Stale result; refresh and review the latest run')
        event = {**body.model_dump(), 'at': datetime.now(timezone.utc).isoformat(),
                 'action': case['result']['action'], 'payment_executed': False}
        case['decisions'].append(event)
        case['status'] = 'APPROVED' if body.decision == 'APPROVE' else 'REJECTED'
        return {'status': case['status'], 'event': event}


@app.post('/disputes/{did}/voice')
def voice_note(did: str, audio: UploadFile = File(...)):
    with lock:
        case = get_case(did)
        if case['running'] or case['status'] in ('APPROVED', 'REJECTED'):
            raise HTTPException(409, 'Case is running or already reviewed')
    try:
        data = audio.file.read(MAX_BYTES + 1)
        voice = transcribe(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ModelError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        audio.file.close()
    with lock:
        if case['running'] or case['status'] in ('APPROVED', 'REJECTED'):
            raise HTTPException(409, 'Case changed during transcription; retry after refreshing')
        case['voice'] = voice
    return voice


@app.post('/disputes/{did}/verify-demo')
def verify_demo(did: str):
    """Check an injected bad citation on a copy. Never alters the reviewable run."""
    with lock:
        result = deepcopy(get_case(did)['result'])
    if not result or not result.get('draft'):
        raise HTTPException(409, 'Complete a run with a draft first')
    draft = result['draft']
    if draft['claims']:
        draft['claims'][0]['ledger_id'] = 'INJECTED-NONEXISTENT-ID'
    else:
        draft['claims'] = [{'ledger_id': 'INJECTED-NONEXISTENT-ID', 'amount': '1.00',
                            'date': '2026-11-01', 'status': 'SETTLED'}]
    verification = verify_draft(draft, read_data('ledger.json'), result['matched'], result['rule'])
    return {'demo': True, 'injection': 'nonexistent ledger ID on a copy', 'draft': draft,
            'verification': verification, 'action': 'ESCALATE',
            'reply': render_reply(draft, result['rule'], verification), 'original_run_unchanged': True}
