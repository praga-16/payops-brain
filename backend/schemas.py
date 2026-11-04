from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

Action = Literal['REFUND', 'NO_ACTION', 'ESCALATE']


class Extraction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    transaction_id: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    date: date
    reason: str = Field(min_length=1, max_length=500)
    customer_name: str = Field(default='', max_length=100)
    phone: str = Field(default='', max_length=30)
    card: str = Field(default='', max_length=30)
    upi_id: str = Field(default='', max_length=100)


class Claim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ledger_id: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    date: date
    status: Literal['SETTLED', 'FAILED_DEBITED', 'REFUNDED']


class Draft(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Action
    claims: list[Claim]
    # A constrained draft intentionally avoids unverifiable free-text assertions.
    # The reply shown to the human is rendered from verified claims + rule reason.
    confidence: float = Field(ge=0, le=1)


class RunRequest(BaseModel):
    note: str = Field(default='', max_length=2000)


class DecisionRequest(BaseModel):
    decision: Literal['APPROVE', 'REJECT']
    run_id: str
    comment: str = Field(default='', max_length=1000)
