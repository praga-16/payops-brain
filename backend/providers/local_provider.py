from backend.providers.base import LLMProvider


class LocalProvider(LLMProvider):
    name = 'local'
    model = 'deterministic ledger templates'

    def generate(self, prompt: str, context: dict | None = None, language: str = 'en') -> dict:
        return {'sentences': list((context or {}).get('sentences', []))}
