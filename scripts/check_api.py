"""No-key runs are labelled fixtures, never a live API success."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.config import ROOT, model_config
from backend.meta_client import call_json, ModelError
from backend.schemas import Extraction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-live', action='store_true')
    parser.add_argument('--all', action='store_true', help='Also run all graph model steps on D001')
    parser.add_argument('--voice', type=Path, help='Also transcribe a mono 16/24kHz PCM WAV')
    args = parser.parse_args()
    cfg = model_config('extract')
    print(json.dumps(cfg.public()))
    if args.require_live and cfg.mock:
        print('ERROR: live check requires EXTRACT_API_KEY or MODEL_API_KEY', file=sys.stderr)
        return 1
    fixture = json.loads((ROOT / 'data/disputes/D001.json').read_text())['fields']
    try:
        result = call_json('extract', 'Return {"ok": true}.', fixture={'ok': True})
        if result.get('ok') is not True:
            raise ModelError('Text response did not return ok=true')
        print('TEXT:', json.dumps(result))
        print('IMAGE:', json.dumps(call_json('extract',
              'Extract this notice. Schema: ' + json.dumps(Extraction.model_json_schema()),
              image=ROOT / 'data/disputes/D001.png', fixture=fixture, schema=Extraction), default=str))
        if args.all:
            from backend.graph import run_case, read_data
            if args.require_live and any(model_config(s).mock for s in ('redact', 'draft')):
                raise ModelError('All-step live check requires redact and draft credentials too')
            state = run_case(read_data('disputes.json')[0])
            print('GRAPH:', json.dumps(state, default=str))
            if not state['verification']['passed']:
                raise ModelError('Graph verification failed; inspect GRAPH output')
        if args.voice:
            from backend.voice import transcribe, voice_config
            if args.require_live and voice_config()['mode'] == 'mock':
                raise ModelError('Voice live check requires VOICE_API_KEY or MODEL_API_KEY')
            print('VOICE:', json.dumps(transcribe(args.voice.read_bytes())))
        print('PASS: ' + ('OFFLINE FIXTURES ONLY; no API called' if cfg.mock else 'real text and image calls; other modes shown in output'))
        return 0
    except (ModelError, OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
