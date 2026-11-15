"""Unified control tower API; original dispute routes remain intact."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend import audit
from backend.decision import AgentAction
from backend.ledger import connect
from backend.review import queue, review_case, kill_switch
from backend.feedback import recalibrate

router=APIRouter(prefix='/api')


class ReviewBody(BaseModel):
    version: int = Field(ge=1)
    comment: str = Field(default='',max_length=2000)
    corrected_action: AgentAction | None = None


class KillBody(BaseModel):
    confirmed: bool = False


def guarded(fn, *args, **kwargs):
    try:
        return fn(*args,**kwargs)
    except LookupError as exc:
        raise HTTPException(404,str(exc)) from None
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from None


@router.get('/review-queue')
def review_queue():
    return queue()


@router.get('/review-queue/{case_id}')
def case_file(case_id: str):
    result=next((r for r in queue() if r['decision']['case_id']==case_id),None)
    if result is None:
        raise HTTPException(404,'Case not found')
    return result


@router.post('/review-queue/{case_id}/approve')
def approve_case(case_id: str, body: ReviewBody):
    return guarded(review_case,case_id,'APPROVE',version=body.version,comment=body.comment)


@router.post('/review-queue/{case_id}/reject')
def reject_case(case_id: str, body: ReviewBody):
    return guarded(review_case,case_id,'REJECT',version=body.version,comment=body.comment)


@router.post('/review-queue/{case_id}/edit')
def edit_case(case_id: str, body: ReviewBody):
    return guarded(review_case,case_id,'EDIT',version=body.version,comment=body.comment,
                   corrected_action=body.corrected_action)


@router.post('/feedback/recalibrate')
def recalibrate_model():
    return recalibrate()


@router.get('/feedback')
def feedback_records():
    import json
    from backend.feedback import latest
    with connect() as conn:
        return {'records':[dict(r) for r in conn.execute('SELECT * FROM human_feedback ORDER BY id')],
                'model':latest(conn)}


@router.get('/audit')
def audit_log(limit: int = 100):
    import json
    with connect() as conn:
        events=[dict(r) for r in conn.execute('SELECT * FROM audit_events ORDER BY id DESC LIMIT ?',
                                             (max(1,min(limit,500)),))]
        for e in events:e['payload']=json.loads(e['payload'])
        return {'integrity':audit.verify(conn),'events':events}


@router.get('/fraud/alerts')
def alerts():
    with connect() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM fraud_alerts ORDER BY risk DESC')]


@router.post('/fraud/{case_id}/suggest-kill-switch')
def suggest_kill(case_id: str):
    return guarded(kill_switch,case_id,approve=False)


@router.post('/fraud/{case_id}/approve-kill-switch')
def approve_kill(case_id: str, body: KillBody):
    return guarded(kill_switch,case_id,approve=True,confirmed=body.confirmed)
