"""No credentials are exposed through the public configuration summary."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


@dataclass(frozen=True)
class ModelConfig:
    model: str
    base_url: str
    api_key: str
    protocol: str
    timeout: float

    @property
    def mock(self):
        return os.getenv('PAYOPS_MOCK', '').lower() == 'true' or not self.api_key

    def public(self):
        return {'model': self.model, 'protocol': self.protocol,
                'mode': 'mock' if self.mock else 'live'}


def model_config(step: str) -> ModelConfig:
    prefix = step.upper()
    baseten = step == 'redact' and bool(os.getenv('BASETEN_BASE_URL'))
    def get(suffix, default):
        return os.getenv(f'{prefix}_{suffix}') or default
    return ModelConfig(
        get('MODEL', 'meta-models/muse-spark-open-1026' if baseten else
            os.getenv('MODEL_MODEL') or 'muse-spark-1.3'),
        get('BASE_URL', os.getenv('BASETEN_BASE_URL') if baseten else
            os.getenv('MODEL_BASE_URL') or 'https://api.meta.ai/v1').rstrip('/'),
        get('API_KEY', (os.getenv('BASETEN_API_KEY') or '') if baseten else
            os.getenv('MODEL_API_KEY') or ''),
        get('PROTOCOL', 'chat' if baseten else os.getenv('MODEL_PROTOCOL') or 'responses'),
        float(os.getenv('MODEL_TIMEOUT') or '60'),
    )
