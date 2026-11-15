"""Additive synthetic intelligence routes; no existing API is replaced."""
from fastapi import APIRouter
from backend.api import guarded
from backend.moneyflow import flow, flow_summary

router=APIRouter(prefix='/api')


@router.get('/money-flow/summary')
def money_flow_summary():
    return flow_summary()


@router.get('/money-flow/{transaction_id}')
def transaction_flow(transaction_id: str):
    return guarded(flow,transaction_id)
