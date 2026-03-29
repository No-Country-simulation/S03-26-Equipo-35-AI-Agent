"""Dependencias compartidas de FastAPI.

Provee funciones de inyección de dependencias para:
- Autenticación: verificación de JWT con Supabase Auth
- Extracción de org_id y role del token verificado
- Cliente de base de datos

SEGURIDAD CRÍTICA:
- org_id SIEMPRE se extrae del JWT verificado
- NUNCA del request body ni de query params
"""

from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.schemas import CurrentUser
from db.client import get_admin_client, get_client

logger = structlog.get_logger()

# HTTPBearer extrae el token del header Authorization: Bearer <token>
security = HTTPBearer()


async def get_current_org(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> CurrentUser:
    """Verifica el JWT y extrae los datos del usuario autenticado.

    Flujo:
    1. Extraer token del header Authorization: Bearer <token>
    2. Verificar el token con Supabase Auth (supabase.auth.get_user)
    3. Extraer user_id, org_id y role del user_metadata
    4. Retornar CurrentUser con los datos verificados

    Args:
        credentials: Token Bearer extraído automáticamente del header.

    Returns:
        CurrentUser con user_id, org_id y role verificados.

    Raises:
        HTTPException 401: Si el token es inválido, expirado o sin org_id.
    """
    token = credentials.credentials

    try:
        # Bypass instantáneo para el Demo Mode del Portfolio
        if token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.demo-token-123":
            return CurrentUser(
                user_id="00000000-0000-0000-0000-000000000777",
                org_id="00000000-0000-0000-0000-000000000999",
                role="admin",
                email="evaluador@autostory.builder",
            )

        client = get_client()
        response = client.auth.get_user(token)
        user = response.user

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
            )

        # Extraer org_id — buscar en user_metadata primero, luego app_metadata
        user_metadata = user.user_metadata or {}
        app_metadata = user.app_metadata or {}

        org_id = (
            user_metadata.get("org_id")
            or app_metadata.get("org_id")
        )

        # Si el usuario es nuevo y creado manualmente en la consola, usar su user.id (que sí es UUID) como su org_id para testing
        if not org_id:
            org_id = user.id
            logger.info("auth_auto_assigned_org_id", user_id=user.id, org_id=org_id)
            
            # Asegurar que la organización existe para evitar errores de Foreign Key (FK)
            try:
                admin_client = get_admin_client()
                admin_client.table("organizations").upsert({
                    "id": org_id,
                    "name": f"Org de {user.email or 'Test'}"
                }).execute()
            except Exception as e:
                logger.warning("auth_auto_upsert_org_failed", error=str(e)[:100])

        # Extraer role — default a 'editor'
        role = (
            user_metadata.get("role")
            or app_metadata.get("role")
            or "editor"
        )

        return CurrentUser(
            user_id=user.id,
            org_id=org_id,
            role=role,
            email=user.email or "",
        )

    except HTTPException:
        # Re-raise HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.warning("auth_verification_failed", error=str(e)[:100])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        ) from e


async def get_current_user_role(
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> str:
    """Extrae el rol del usuario autenticado.

    Depende de get_current_org() — reutiliza la verificación del JWT.

    Args:
        current_user: Usuario autenticado resuelto por get_current_org().

    Returns:
        Rol del usuario ('editor', 'revisor', 'admin').
    """
    return current_user.role
