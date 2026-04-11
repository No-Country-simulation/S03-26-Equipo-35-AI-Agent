"""Servicio de flujo de aprobaciones.

Orquesta la lógica de negocio de las transiciones de estado, verificando
reglas con state_machine y persistiendo los cambios en DB.
"""

from core.approvals.state_machine import transition
from db.repositories.approval_repository import record_transition
from db.repositories.story_repository import get_story_by_id, update_story_status


async def execute_transition(
    story_id: str,
    target_status: str,
    org_id: str,
    role: str,
    user_id: str,
    comment: str = ""
) -> dict:
    """Ejecuta una transición de estado segura.

    1. Verifica existencia de historia.
    2. Valida transición via state_machine.
    3. Actualiza estado.
    4. Registra en historial.
    """
    from db.client import get_admin_client
    client = get_admin_client()

    story = await get_story_by_id(client, story_id, org_id)
    if not story:
        raise ValueError("Historia no encontrada")

    current_status = story.get("status", "borrador")

    # Si target es igual al actual, es un no-op
    if current_status == target_status:
        return {"story": story, "transition": None}

    # Validar transición con state_machine
    new_status = transition(current_status, target_status, role)

    # Actualizar estado de historia
    updated_story = await update_story_status(client, story_id, org_id, new_status)

    # Registrar en historial de aprobaciones
    transition_record = await record_transition(
        client=client,
        story_id=story_id,
        org_id=org_id,
        from_status=current_status,
        to_status=new_status,
        changed_by=user_id,
        comment=comment
    )

    return {"story": updated_story, "transition": transition_record}
