"""Security-only scenario simulator control."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import scenario
from ..auth import Principal, require_security

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


@router.post("/start")
async def start(_: Principal = Depends(require_security)):
    return await scenario.start()


@router.post("/stop")
async def stop(_: Principal = Depends(require_security)):
    return await scenario.stop()


@router.post("/reset")
async def reset(_: Principal = Depends(require_security)):
    """Clear all demo data and restore safe default zone statuses. Security-only."""
    return await scenario.reset()


@router.get("/status")
def status(_: Principal = Depends(require_security)):
    return scenario.status()
