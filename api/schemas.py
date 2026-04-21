"""Modelos Pydantic base para la API de AutoStory Builder.

Schemas reutilizables en toda la capa HTTP:
- CurrentUser: datos del usuario autenticado extraídos del JWT
- HealthResponse: respuesta del health check
"""

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Datos del usuario autenticado extraídos del JWT.

    SEGURIDAD: org_id siempre viene del JWT verificado,
    nunca del request body.
    """

    user_id: str
    org_id: str
    role: str = "editor"
    email: str = ""


class HealthResponse(BaseModel):
    """Respuesta del endpoint /health."""

    status: str = "ok"
    version: str = "0.1.0"
    supabase: str = "unknown"
    redis: str = "not_configured"
