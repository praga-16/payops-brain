import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import ROOT, model_config
from backend.graph import read_data, run_case
from backend.schemas import RunRequest, DecisionRequest

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
    return {'ok': True, 'synthetic_only': True, 'models': {s: model_config(s).public() for s in ('extract', 'redact', 'draft')}}


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
    try:
        result = run_case(snapshot, note=body.note)
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
