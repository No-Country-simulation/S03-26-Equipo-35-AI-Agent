"""Máquina de estados para el flujo de aprobación de contenido.

Define las transiciones válidas entre estados y los roles autorizados
para cada transición. Este es un módulo crítico con lógica real implementada.

Flujo de aprobación:
    BORRADOR → EN_REVISION → APROBADO → PUBLICADO
                   ↓
               RECHAZADO → BORRADOR

Roles:
    - editor:  Crea borradores, envía a revisión
    - revisor: Aprueba o rechaza contenido en revisión
    - admin:   Publica contenido aprobado, puede hacer cualquier transición
"""


class InvalidTransitionError(Exception):
    """Error cuando se intenta una transición de estado no válida."""

    def __init__(self, current: str, target: str, role: str) -> None:
        self.current = current
        self.target = target
        self.role = role
        super().__init__(
            f"Transición inválida: '{current}' → '{target}' "
            f"para rol '{role}'"
        )


# Estados válidos del sistema
VALID_STATES: set[str] = {
    "borrador",
    "en_revision",
    "aprobado",
    "rechazado",
    "publicado",
}

# Transiciones válidas: estado_actual → {estado_destino: [roles_autorizados]}
VALID_TRANSITIONS: dict[str, dict[str, list[str]]] = {
    "borrador": {
        "en_revision": ["editor", "admin"],
    },
    "en_revision": {
        "aprobado": ["revisor", "admin"],
        "rechazado": ["revisor", "admin"],
    },
    "aprobado": {
        "publicado": ["admin"],
    },
    "rechazado": {
        "borrador": ["editor", "admin"],
    },
    "publicado": {
        # Estado terminal — no hay transiciones de salida
    },
}


def transition(current: str, target: str, role: str) -> str:
    """Ejecuta una transición de estado si es válida para el rol dado.

    Verifica que:
    1. El estado actual sea válido
    2. El estado destino sea válido
    3. La transición current → target esté permitida
    4. El rol del usuario esté autorizado para esa transición

    Args:
        current: Estado actual de la historia.
        target: Estado destino deseado.
        role: Rol del usuario que solicita la transición
              ('editor', 'revisor', 'admin').

    Returns:
        El estado destino si la transición es válida.

    Raises:
        InvalidTransitionError: Si la transición no está permitida
                                 o el rol no está autorizado.
        ValueError: Si alguno de los estados o el rol no son válidos.
    """
    # Validar que los estados existan
    if current not in VALID_STATES:
        msg = f"Estado actual no válido: '{current}'. Válidos: {VALID_STATES}"
        raise ValueError(msg)

    if target not in VALID_STATES:
        msg = f"Estado destino no válido: '{target}'. Válidos: {VALID_STATES}"
        raise ValueError(msg)

    valid_roles = {"editor", "revisor", "admin"}
    if role not in valid_roles:
        msg = f"Rol no válido: '{role}'. Válidos: {valid_roles}"
        raise ValueError(msg)

    # Obtener transiciones válidas desde el estado actual
    transitions_from_current = VALID_TRANSITIONS.get(current, {})

    # Verificar que la transición sea válida
    if target not in transitions_from_current:
        raise InvalidTransitionError(current, target, role)

    # Verificar que el rol esté autorizado
    authorized_roles = transitions_from_current[target]
    if role not in authorized_roles:
        raise InvalidTransitionError(current, target, role)

    return target


def get_available_transitions(current: str, role: str) -> list[str]:
    """Obtiene los estados a los que se puede transicionar desde el estado actual.

    Args:
        current: Estado actual de la historia.
        role: Rol del usuario consultando.

    Returns:
        Lista de estados destino disponibles para ese rol.

    Raises:
        ValueError: Si el estado actual o el rol no son válidos.
    """
    if current not in VALID_STATES:
        msg = f"Estado no válido: '{current}'. Válidos: {VALID_STATES}"
        raise ValueError(msg)

    valid_roles = {"editor", "revisor", "admin"}
    if role not in valid_roles:
        msg = f"Rol no válido: '{role}'. Válidos: {valid_roles}"
        raise ValueError(msg)

    transitions_from_current = VALID_TRANSITIONS.get(current, {})

    return [
        target
        for target, authorized_roles in transitions_from_current.items()
        if role in authorized_roles
    ]
