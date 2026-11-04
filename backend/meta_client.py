"""Small, testable HTTP adapter for Meta Responses and Baseten Chat.

Request contracts and the model-ID discrepancy are documented in docs/api_contracts.md.
No silent live-to-mock fallback; no provider bodies or keys in error messages.
"""
import base64
import json
import mimetypes
import re
from pathlib import Path
import httpx
from backend.config import model_config


class ModelError(RuntimeError):
    pass


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)
    text = re.sub(r'\s*```$', '', text)
    decoder = json.JSONDecoder()
    # Accept prose around ONE JSON object, but reject ambiguous multiple objects.
    objects = []
    for index, char in enumerate(text):
        if char == '{':
            try:
                obj, end = decoder.raw_decode(text[index:])
                if isinstance(obj, dict):
                    objects.append((index, index + end, obj))
            except ValueError:
                continue
    outer = [x for x in objects if not any(y[0] < x[0] and y[1] >= x[1] for y in objects)]
    if len(outer) != 1:
        raise ValueError('Expected exactly one JSON object')
    return outer[0][2]


def image_uri(path):
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or 'image/png'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()


def request_body(config, prompt, image=None):
    if config.protocol == 'responses':
        content = [{'type': 'input_text', 'text': prompt}]
        if image:
            content.append({'type': 'input_image', 'image_url': image_uri(image)})
        return '/responses', {'model': config.model, 'store': False,
                             'input': [{'role': 'user', 'content': content}]}
    if config.protocol == 'chat':
        content = [{'type': 'text', 'text': prompt}]
        if image:
            content.append({'type': 'image_url', 'image_url': {'url': image_uri(image)}})
        return '/chat/completions', {'model': config.model,
                                    'messages': [{'role': 'user', 'content': content}]}
    raise ModelError('Unsupported protocol; choose responses or chat')


def response_text(payload, protocol):
    if protocol == 'chat':
        return payload['choices'][0]['message']['content']
    if payload.get('status') in ('incomplete', 'failed'):
        raise ModelError('Provider returned an incomplete or failed response')
    return '\n'.join(part['text'] for item in payload.get('output', [])
                     if item.get('type') == 'message' for part in item.get('content', [])
                     if part.get('type') == 'output_text')


def call_json(step, prompt, *, image=None, fixture=None, schema=None):
    cfg = model_config(step)
    if cfg.mock:
        if fixture is None:
            raise ModelError(f'{step}: no key configured; no offline fixture supplied')
        result = fixture() if callable(fixture) else fixture
        return schema.model_validate(result).model_dump() if schema else result
    for attempt in range(2):
        suffix, body = request_body(cfg, prompt + '\nReturn only a JSON object.' +
                                    (' Previous output was invalid. Follow the exact schema.' if attempt else ''), image)
        try:
            with httpx.Client(timeout=cfg.timeout) as client:
                response = client.post(cfg.base_url + suffix, json=body,
                                       headers={'Authorization': f'Bearer {cfg.api_key}'})
            if response.is_error:
                raise ModelError(f'{step}: provider HTTP {response.status_code}; check key, model, base URL and access')
            result = parse_json(response_text(response.json(), cfg.protocol))
            return schema.model_validate(result).model_dump() if schema else result
        except httpx.TimeoutException as exc:
            raise ModelError(f'{step}: request timed out after {cfg.timeout:g}s') from exc
        except httpx.HTTPError as exc:
            raise ModelError(f'{step}: provider connection failed') from exc
        except (ValueError, KeyError, IndexError, TypeError):
            if attempt:
                raise ModelError(f'{step}: invalid JSON or schema after one retry') from None
    raise ModelError(f'{step}: unexpected response')
