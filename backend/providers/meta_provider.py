import json
from backend.meta_client import call_json, ModelError
from backend.providers.base import LLMProvider, ProviderError


class MetaProvider(LLMProvider):
    name = 'meta'

    def __init__(self):
        from backend.config import model_config
        self.model=model_config('draft').model

    def generate(self, prompt: str, context: dict | None = None, language: str = 'en') -> dict:
        try:
            return call_json('draft',prompt+' Return JSON {"sentences": [...]} using all supplied '
                             'sentences verbatim, once each. No new claims. DATA: '+json.dumps(context),
                             fixture={'sentences':(context or {}).get('sentences',[])})
        except ModelError:
            raise ProviderError('Meta unavailable; local fallback used') from None
