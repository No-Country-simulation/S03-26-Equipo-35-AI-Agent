"""Router de autenticación.

Endpoints para login y gestión de tokens JWT.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class LoginRequest(BaseModel):
    """Schema de request para login."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Schema de response con token JWT."""

    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Autentica un usuario y retorna un JWT.

    El JWT contendrá el org_id del usuario para aislamiento de datos.
    """
    # TODO: Implementar autenticación con Supabase Auth
    raise NotImplementedError
