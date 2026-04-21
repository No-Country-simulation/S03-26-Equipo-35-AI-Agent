"""Router de aprobaciones.

Endpoints para gestionar el flujo de aprobación de historias:
  BORRADOR → EN_REVISION → APROBADO → PUBLICADO
                 ↓
             RECHAZADO → BORRADOR
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import get_current_org
from api.schemas import CurrentUser
from core.approvals.service import execute_transition
from db.repositories.approval_repository import get_history_for_story

router = APIRouter()


class TransitionRequest(BaseModel):
    """Schema de request para transición de estado."""
    story_id: str
    target_status: str


@router.post("/transition")
async def transition_story(
    request: TransitionRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> dict[str, Any]:
    """Ejecuta una transición de estado en una historia.

    Valida que la transición sea válida según el estado actual
    y el rol del usuario.
    """
    try:
        result = await execute_transition(
            story_id=request.story_id,
            target_status=request.target_status,
            org_id=current_user.org_id,
            role=current_user.role,
            user_id=current_user.user_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{story_id}/history")
async def get_approval_history(
    story_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> list[dict[str, Any]]:
    """Obtiene el historial de aprobaciones de una historia."""
    from db.client import get_admin_client
    client = get_admin_client()
    return await get_history_for_story(client, story_id, current_user.org_id)
