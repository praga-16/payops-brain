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
    args = parser.parse_args()
    cfg = model_config('extract')
    print(json.dumps(cfg.public()))
    if args.require_live and cfg.mock:
        print('ERROR: live check requires EXTRACT_API_KEY or MODEL_API_KEY', file=sys.stderr)
        return 1
    fixture = json.loads((ROOT / 'data/disputes/D001.json').read_text())['fields']
    try:
        print('TEXT:', json.dumps(call_json('extract', 'Return {"ok": true}.', fixture={'ok': True})))
        print('IMAGE:', json.dumps(call_json('extract',
              'Extract this notice. Schema: ' + json.dumps(Extraction.model_json_schema()),
              image=ROOT / 'data/disputes/D001.png', fixture=fixture, schema=Extraction), default=str))
        print('PASS: ' + ('OFFLINE FIXTURES ONLY; no API called' if cfg.mock else 'real text and image calls'))
        return 0
    except ModelError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
