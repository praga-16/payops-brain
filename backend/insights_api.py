"""Additive synthetic intelligence routes; no existing API is replaced."""
from fastapi import APIRouter,Query
from pydantic import BaseModel,Field
from backend.api import guarded
from backend.moneyflow import flow, flow_summary

router=APIRouter(prefix='/api')


@router.get('/autonomy/replay')
def autonomy_replay(threshold: float = Query(default=.95,ge=.70,le=.99)):
    from backend.autonomy_replay import replay
    return replay(threshold)


class IncidentBody(BaseModel):
    count: int = Field(default=16,ge=16,le=128)
    seed: int | None = Field(default=None,ge=0,le=1000000)


@router.get('/incidents')
def incident_history():
    from backend.incidents import history
    return history()


@router.post('/incidents/{scenario}')
def trigger_incident(scenario: str, body: IncidentBody):
    from backend.incidents import trigger
    return guarded(trigger,scenario,count=body.count,seed_value=body.seed)


@router.get('/impact')
def rupee_impact():
    from backend.impact import impact_report
    return guarded(impact_report)


@router.get('/profit')
def profit():
    from backend.margins import profit_summary
    return profit_summary()


@router.post('/fee-audit/run')
def fee_audit_run():
    from backend.margins import fee_audit
    from backend.review import persist
    return {'synthetic':True,'created':persist(fee_audit()),'claim_filed':False}


@router.get('/money-flow/summary')
def money_flow_summary():
    return flow_summary()


@router.get('/money-flow/{transaction_id}')
def transaction_flow(transaction_id: str):
    return guarded(flow,transaction_id)
