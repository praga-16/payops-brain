"""Additive synthetic intelligence routes; no existing API is replaced."""
from fastapi import APIRouter,Query,UploadFile,File,HTTPException
from pydantic import BaseModel,Field
from backend.api import guarded
from backend.moneyflow import flow, flow_summary

router=APIRouter(prefix='/api')


@router.get('/security/status')
def security_status():
    from backend.security import scan_database
    return scan_database()


@router.get('/merchant-assistant/voice/status')
def voice_status():
    from backend.sarvam_voice import status
    return status()


def speech_guard(fn,*args,**kwargs):
    from backend.providers.base import ProviderError
    try:return fn(*args,**kwargs)
    except ProviderError as exc:raise HTTPException(503,str(exc)) from None
    except ValueError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/merchant-assistant/voice/transcribe')
def merchant_transcription(audio: UploadFile = File(...)):
    from backend.sarvam_voice import transcribe
    from backend.voice import MAX_BYTES
    try:
        result=speech_guard(transcribe,audio.file.read(MAX_BYTES+1))
        from backend import audit
        from backend.ledger import connect
        with connect() as c:audit.append(c,'SPEECH_TRANSCRIBED','voice-input',{'language':result['language'],'provider':'sarvam','mode':'live','audio_persisted':False})
        return result
    finally:audio.file.close()


from backend.api import ChatBody,merchant_chat


@router.post('/merchant-assistant/voice/speak')
def merchant_speech(body: ChatBody):
    from backend.sarvam_voice import require_enabled,synthesize
    speech_guard(require_enabled)
    # The client cannot supply spoken financial text; regenerate from the ledger
    # and the existing exact-sentence gate before speech synthesis.
    answer=merchant_chat(body)
    audio=speech_guard(synthesize,answer['text'],body.language)
    from backend import audit
    from backend.ledger import connect
    with connect() as c:audit.append(c,'SPEECH_SYNTHESIZED',body.merchant_id,{'language':body.language,'provider':'sarvam','grounded':answer['grounded'],'audio_persisted':False})
    return {'answer':answer,**audio}


@router.get('/autonomy/ramp')
def autonomy_ramp():
    from backend.earned_autonomy import history
    return history()


@router.post('/autonomy/assess')
def assess_autonomy():
    from backend.earned_autonomy import assess
    return guarded(assess)


@router.get('/bin-intelligence')
def bins():
    from backend.routing import bin_report
    return bin_report()


@router.get('/routing')
def routing():
    from backend.routing import routing_report
    return routing_report()


@router.post('/routing/suggest')
def suggest_routing():
    from backend.routing import routing_report
    from backend.review import persist
    return {'synthetic':True,'created':persist(routing_report()['proposals']),'routing_executed':False}


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
