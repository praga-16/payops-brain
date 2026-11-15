"""Feature-flagged Sarvam speech adapters; no fixed transcript success fallback."""
from __future__ import annotations
import base64
import os
import httpx
from backend.providers.base import ProviderError
from backend.voice import validate_wav,MAX_BYTES
from backend.security import mask_text

LANGUAGES={'en':'en-IN','hi':'hi-IN','ta':'ta-IN'}


def status() -> dict:
    enabled=os.getenv('PAYOPS_SARVAM_VOICE','').lower()=='true'
    configured=bool(os.getenv('SARVAM_API_KEY'))
    return {'enabled':enabled and configured and os.getenv('PAYOPS_MOCK','').lower()!='true',
            'feature_flag':enabled,'credentials_configured':configured,'microphone_verified':False,
            'stt_model':os.getenv('SARVAM_STT_MODEL') or 'saaras:v3','tts_model':os.getenv('SARVAM_TTS_MODEL') or 'bulbul:v3',
            'note':'Disabled by default. Physical microphone is unverified. File-based API verification is separate.'}


def require_enabled() -> None:
    if not status()['enabled']:raise ProviderError('Sarvam voice is disabled or unavailable; use text input.')


def send(endpoint: str,**kwargs) -> dict:
    require_enabled()
    try:
        with httpx.Client(timeout=float(os.getenv('SARVAM_TIMEOUT') or '30')) as client:
            r=client.post((os.getenv('SARVAM_VOICE_BASE_URL') or 'https://api.sarvam.ai').rstrip('/')+endpoint,
                          headers={'api-subscription-key':os.environ['SARVAM_API_KEY']},**kwargs)
        if r.is_error:raise ProviderError(f'Sarvam speech HTTP {r.status_code}; use text input.')
        return r.json()
    except (httpx.HTTPError,ValueError,KeyError):
        raise ProviderError('Sarvam speech unavailable or invalid; use text input.') from None


def transcribe(data: bytes) -> dict:
    require_enabled()
    duration=validate_wav(data)
    if duration>30:raise ValueError('Sarvam synchronous transcription accepts at most 30 seconds locally')
    r=send('/speech-to-text',files={'file':('synthetic.wav',data,'audio/wav')},
           data={'model':status()['stt_model'],'mode':'transcribe','language_code':'unknown'})
    text=r.get('transcript');code=r.get('language_code')
    if not isinstance(text,str) or not text.strip() or len(text)>2000:raise ProviderError('Speech transcript was invalid')
    language=next((k for k,v in LANGUAGES.items() if v==code),None)
    if language is None:raise ProviderError('Detected language is unsupported; choose English, Hindi or Tamil text input.')
    return {'transcript':mask_text(text),'language':language,'detected_language_code':code,'provider':'sarvam',
            'mode':'live','audio_seconds':duration,'audio_persisted':False}


def synthesize(text: str,language: str) -> dict:
    require_enabled()
    if language not in LANGUAGES or not 0<len(text)<=2500:raise ValueError('Unsupported speech language or text length')
    r=send('/text-to-speech',json={'text':text,'language_code':LANGUAGES[language],
           'model':status()['tts_model'],'speech_sample_rate':16000,'output_audio_codec':'wav'})
    audios=r.get('audios')
    try:
        if not isinstance(audios,list) or len(audios)!=1:raise ValueError('Invalid audio response')
        data=base64.b64decode(audios[0],validate=True)
        if not data or len(data)>MAX_BYTES:raise ValueError('Invalid audio size')
        validate_wav(data)
    except (ValueError,TypeError):raise ProviderError('Speech audio response was invalid') from None
    return {'audio_base64':audios[0],'media_type':'audio/wav','provider':'sarvam','mode':'live','language':language,'audio_persisted':False}
