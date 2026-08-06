"""Aggregates every v1 route into one router mounted by ``app.main``.

Registration order matters where paths could collide: routers with a greedy
`{urn:path}` parameter are included after the ones with fixed paths, so a
literal route is never shadowed by a catch-all.
"""

from fastapi import APIRouter

from app.api.v1 import (
    agent,
    datasets,
    domains,
    health,
    lineage,
    owners,
    statistics,
)

api_router = APIRouter()

# Fixed-path routers.
api_router.include_router(health.router)
api_router.include_router(agent.router)
api_router.include_router(owners.router)
api_router.include_router(lineage.router)
api_router.include_router(statistics.router)

# Routers containing `{urn:path}` catch-alls.
api_router.include_router(datasets.router)
api_router.include_router(domains.router)
