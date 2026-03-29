"""Router de aprobaciones.

Endpoints para gestionar el flujo de aprobación de historias:
  BORRADOR → EN_REVISION → APROBADO → PUBLICADO
                 ↓
             RECHAZADO → BORRADOR
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_current_org, get_current_user_role
from core.approvals.service import execute_transition
from db.client import get_client
from db.repositories.approval_repository import get_history_for_story

router = APIRouter()


class TransitionRequest(BaseModel):
    """Schema de request para transición de estado."""

    story_id: str
    target_status: str


@router.post("/transition")
async def transition_story(
    request: TransitionRequest,
    org_id: str = Depends(get_current_org),
    role: str = Depends(get_current_user_role),
) -> dict[str, Any]:
    """Ejecuta una transición de estado en una historia.

    Valida que la transición sea válida según el estado actual
    y el rol del usuario.
    """
    try:
        # org_id might be a CurrentUser object depending on how Depends is resolved
        oid = org_id.org_id if hasattr(org_id, "org_id") else org_id
        uid = org_id.user_id if hasattr(org_id, "user_id") else "unknown"

        result = await execute_transition(
            story_id=request.story_id,
            target_status=request.target_status,
            org_id=oid,
            role=role,
            user_id=uid
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # InvalidTransitionError is imported dynamically or we catch it as Exception
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{story_id}/history")
async def get_approval_history(
    story_id: str,
    org_id: str = Depends(get_current_org),
) -> list[dict[str, Any]]:
    """Obtiene el historial de aprobaciones de una historia."""
    client = get_client()
    oid = org_id.org_id if hasattr(org_id, "org_id") else org_id
    return await get_history_for_story(client, story_id, oid)
