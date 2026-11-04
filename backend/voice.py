"""Muse Voice file transcription, matching official cookbook utils.py multipart."""
import io
import json
import os
import wave
import httpx
from backend.meta_client import ModelError

MAX_BYTES = 10 * 1024 * 1024
MOCK_TRANSCRIPT = 'Review both debit records before approving a refund. Keep this case pending human review.'


def voice_config():
    key = os.getenv('VOICE_API_KEY') or os.getenv('MODEL_API_KEY') or ''
    return {'model': os.getenv('VOICE_MODEL') or 'muse-voice-transcribe-1.0',
            'base_url': (os.getenv('VOICE_BASE_URL') or os.getenv('MODEL_BASE_URL') or 'https://api.meta.ai/v1').rstrip('/'),
            'api_key': key, 'mode': 'mock' if not key or os.getenv('PAYOPS_MOCK', '').lower() == 'true' else 'live'}


def validate_wav(data):
    if len(data) > MAX_BYTES:
        raise ValueError('Audio exceeds the local 10 MB upload limit')
    try:
        with wave.open(io.BytesIO(data)) as audio:
            if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() not in (16000, 24000):
                raise ValueError('Use mono 16-bit PCM WAV at 16 or 24 kHz')
            duration = audio.getnframes() / audio.getframerate()
            if not 0 < duration <= 120:
                raise ValueError('Use a recording between 0 and 120 seconds')
            if len(audio.readframes(audio.getnframes())) != audio.getnframes() * 2:
                raise ValueError('WAV recording is truncated')
    except (wave.Error, EOFError) as exc:
        raise ValueError('Invalid WAV recording') from exc
    return duration


def transcribe(data):
    duration = validate_wav(data)
    cfg = voice_config()
    if cfg['mode'] == 'mock':
        return {'transcript': MOCK_TRANSCRIPT, 'mode': 'mock', 'model': 'fixed transcript fixture (no speech recognition)',
                'audio_duration_seconds': duration}
    request = {'mode': 'PUSH_TO_TALK', 'model': cfg['model'], 'audioEncoding': 'WAV'}
    try:
        with httpx.Client(timeout=float(os.getenv('MODEL_TIMEOUT') or '60')) as client:
            response = client.post(cfg['base_url'] + '/asr/transcribe',
                headers={'Authorization': f"Bearer {cfg['api_key']}"},
                files={'request': (None, json.dumps(request), 'application/json'),
                       'audio': ('note.wav', data, 'audio/wav')})
        if response.is_error:
            raise ModelError(f"voice: provider HTTP {response.status_code}; check WAV format, model and access")
        transcript = response.json()['transcript']
        if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > 2000:
            raise ValueError('Invalid transcript')
        return {'transcript': transcript, 'mode': 'live', 'model': cfg['model'], 'audio_duration_seconds': duration}
    except httpx.TimeoutException as exc:
        raise ModelError('voice: transcription timed out') from exc
    except httpx.HTTPError as exc:
        raise ModelError('voice: provider connection failed') from exc
    except (KeyError, ValueError, TypeError) as exc:
        raise ModelError('voice: provider returned an invalid or overlong transcript') from exc
