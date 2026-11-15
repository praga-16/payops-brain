"""Unified control tower API; original dispute routes remain intact."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend import audit
from backend.decision import AgentAction
from backend.ledger import connect
from backend.review import queue, review_case, kill_switch
from backend.feedback import recalibrate
from backend.merchant import chat
from backend.ledger import records, money
from backend.control_tower import summary, simulator, run_agents

router=APIRouter(prefix='/api')


class SimulatorBody(BaseModel):
    count: int = Field(default=32,ge=16,le=1000)
    seed: int = Field(default=42,ge=0,le=1000000)
    continuous: bool = False
    interval: float = Field(default=5,ge=2,le=60)


@router.get('/dashboard/summary')
def dashboard_summary():
    return summary()


@router.get('/transactions')
def transactions():
    return [r|{'amount':money(r['amount_paise']),'fee':money(r['fee_paise'])} for r in records('transactions')]


@router.get('/settlements')
def settlements():
    return [r|{'amount':money(r['amount_paise'])} for r in records('settlements')]


@router.get('/merchants')
def merchants():
    return records('merchant_profiles')


@router.get('/reconciliation')
def reconciliations():
    return [r for r in queue() if r['agent']=='reconciliation']


@router.post('/simulator/start')
def start_simulator(body: SimulatorBody):
    return guarded(simulator.start,count=body.count,seed_value=body.seed,
                   continuous=body.continuous,interval=body.interval)


@router.post('/simulator/stop')
def stop_simulator():
    return simulator.stop()


@router.get('/simulator/status')
def simulator_status():
    return simulator.status()


@router.post('/agents/run')
def agents_run():
    return run_agents()


@router.get('/agents')
def agents():
    return [{'name':'reconciliation','implementation':'reference rules + gradient boosting','mode':'local'},
            {'name':'dispute','implementation':'evidence checklist + logistic win estimate','mode':'local; provider draft on request'},
            {'name':'fraud','implementation':'Isolation Forest + velocity/refund rules','mode':'local'}]


@router.get('/agents/activity')
def activity():
    import json
    with connect() as conn:
        return [dict(r)|{'payload':json.loads(r['payload'])} for r in conn.execute(
            "SELECT * FROM audit_events WHERE event LIKE 'AGENT_%' OR event IN ('SIMULATION_BATCH','INCIDENT_TRIGGERED') ORDER BY id DESC LIMIT 30")]


@router.post('/review-queue/{case_id}/draft')
def generate_dispute_draft(case_id: str):
    from backend.dispute_intelligence import analyze
    case=case_file(case_id)
    if case['agent']!='dispute':raise HTTPException(422,'Draft generation applies to chargeback cases')
    # Explicit user request is the only bulk-workflow path that calls an LLM.
    # Select only this case before making a provider call.
    from backend.providers.factory import explain
    draft=case['draft']
    refreshed=explain(draft['text'].split('\n'),facts={'evidence':case['decision']['evidence']},
                      task='Compose this verified dispute explanation unchanged.')
    with connect() as conn:
        audit.append(conn,'DISPUTE_DRAFT_GENERATED',case_id,{'provider':refreshed['provider'],
                     'mode':refreshed['mode'],'grounded':refreshed['grounded']})
    return refreshed


class ReviewBody(BaseModel):
    version: int = Field(ge=1)
    comment: str = Field(default='',max_length=2000)
    corrected_action: AgentAction | None = None


class KillBody(BaseModel):
    confirmed: bool = False


class ChatBody(BaseModel):
    merchant_id: str = Field(pattern=r'^SYN-M\d{3}$')
    question: str = Field(min_length=1,max_length=2000)
    language: str = Field(default='en',pattern=r'^(en|hi|ta)$')
    transaction_id: str | None = Field(default=None,max_length=120)


@router.post('/merchant-assistant/chat')
def merchant_chat(body: ChatBody):
    result=chat(body.merchant_id,body.question,body.language,transaction_id=body.transaction_id)
    with connect() as conn:
        audit.append(conn,'MERCHANT_EXPLANATION',body.merchant_id,
                     {'provider':result['provider'],'mode':result['mode'],'language':body.language,
                      'grounded':result['grounded'],'routed_to_analyst':result['routed_to_analyst'],
                      'evidence':(result.get('facts') or {}).get('evidence',[])})
    return result


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


@router.get('/review-queue/{case_id}/evidence')
def case_evidence(case_id: str):
    case=case_file(case_id)
    ids=set(case['decision']['evidence'])
    return [{'table':table,**row} for table in ('transactions','settlements','refunds','fees','disputes')
            for row in records(table) if row['id'] in ids]


@router.get('/configuration')
def public_configuration():
    from backend.providers.factory import get_provider
    p=get_provider()
    return {'provider':p.name,'model':p.model,'mode':'local' if p.name=='local' else 'live configured',
            'synthetic_only':True}


@router.get('/evaluation')
def evaluation_report():
    import json
    from backend.feedback import latest
    with connect() as conn:
        row=conn.execute("SELECT payload FROM model_registry WHERE name='evaluation' ORDER BY id DESC LIMIT 1").fetchone()
        return {'report':json.loads(row[0]) if row else None,'calibration':latest(conn)}


@router.post('/evaluation/run')
def run_eval():
    from backend.evaluation import run_evaluation
    return run_evaluation()


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
