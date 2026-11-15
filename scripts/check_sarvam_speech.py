"""Explicit synthetic TTS-to-STT loopback; does not verify a physical microphone."""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import ROOT
from backend.sarvam_voice import synthesize,transcribe


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live:print('Not run. --live explicitly opts into synthetic speech provider calls.');return 0
    os.environ['PAYOPS_SARVAM_VOICE']='true';os.environ['PAYOPS_MOCK']='false'
    phrases={'en':'Why is my synthetic settlement short?',
             'hi':'मेरा सिंथेटिक भुगतान कम क्यों है?',
             'ta':'எனது செயற்கை பணம் ஏன் குறைவாக உள்ளது?'}
    results=[]
    for language,text in phrases.items():
        try:
            audio=synthesize(text,language)
            result=transcribe(base64.b64decode(audio['audio_base64']))
            row={'language':language,'detected':result['language'],'passed':result['language']==language,
                 'source':'generated synthetic speech; no microphone','audio_persisted':False}
        except Exception as exc:
            from backend.providers.base import ProviderError
            row={'language':language,'passed':False,'reason':str(exc) if isinstance(exc,(ProviderError,ValueError)) else type(exc).__name__,
                 'source':'generated synthetic speech; no microphone'}
        results.append(row);print(row)
    report={'synthetic':True,'physical_microphone_verified':False,'results':results}
    (ROOT/'reports'/'speech_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if all(r['passed'] for r in results) else 1


if __name__=='__main__':raise SystemExit(main())
