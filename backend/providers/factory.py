from __future__ import annotations

import os
from backend.config import model_config
from backend.providers.base import LLMProvider, ProviderError
from backend.providers.local_provider import LocalProvider
from backend.providers.meta_provider import MetaProvider
from backend.providers.sarvam_provider import SarvamProvider


def get_provider() -> LLMProvider:
    if os.getenv('PAYOPS_MOCK','').lower()=='true':
        return LocalProvider()
    selected=os.getenv('LLM_PROVIDER') or 'sarvam'
    if selected=='sarvam' and os.getenv('SARVAM_API_KEY'):
        return SarvamProvider()
    if selected=='meta' and not model_config('draft').mock:
        return MetaProvider()
    return LocalProvider()


def explain(sentences: list[str], *, facts: dict, language: str = 'en', task: str = '', use_provider: bool = True) -> dict:
    provider=get_provider() if use_provider else LocalProvider()
    context={'sentences':sentences,'computed_facts':facts}
    fallback=None
    try:
        output=provider.generate(task,context,language)
        selected=output.get('sentences')
        # An exact sentence multiset gate also blocks invented nonnumeric facts,
        # changed dates, promises and statuses; numeric token checks alone cannot.
        if not isinstance(selected,list) or not all(isinstance(s,str) for s in selected) or sorted(selected)!=sorted(sentences):
            raise ProviderError('Unsupported generated claim rejected')
    except ProviderError as exc:
        selected=sentences
        fallback=str(exc)
    return {'text':' '.join(selected),'provider':provider.name if not fallback else 'local',
            'requested_provider':provider.name,'model':provider.model if not fallback else LocalProvider.model,
            'mode':'local' if provider.name=='local' or fallback else 'live',
            'fallback_reason':fallback,'grounded':True,'generation_scope':'verbatim grounded sentence composition'}
