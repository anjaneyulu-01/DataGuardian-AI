"""Aggregates every v1 route into one router mounted by ``app.main``.

Feature routers (assets, findings, lineage, agent runs) get included here as
they are built, so ``main.py`` never needs to change again.
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
