"""Tests de autenticación JWT.

🟡 IMPORTANTE
Verifica que los endpoints rechazan requests sin JWT válido.
"""

import pytest


class TestAuthJWT:
    """Tests de autenticación basada en JWT."""

    def test_endpoint_rejects_missing_token(self) -> None:
        """Endpoints protegidos rechazan requests sin token.

        Arrange: Request sin header Authorization
        Act: Llamar a endpoint protegido
        Assert: HTTP 401 Unauthorized
        """
        # TODO: Usar TestClient de FastAPI
        # from fastapi.testclient import TestClient
        # from api.main import app
        # client = TestClient(app)
        # response = client.get("/stories/")
        # assert response.status_code == 401
        pytest.skip("TODO: Implementar con TestClient")

    def test_endpoint_rejects_invalid_token(self) -> None:
        """Endpoints protegidos rechazan tokens JWT inválidos.

        Arrange: Request con token JWT malformado
        Act: Llamar a endpoint protegido
        Assert: HTTP 401 Unauthorized
        """
        pytest.skip("TODO: Implementar con TestClient")

    def test_endpoint_rejects_expired_token(self) -> None:
        """Endpoints protegidos rechazan tokens JWT expirados.

        Arrange: Request con token JWT expirado
        Act: Llamar a endpoint protegido
        Assert: HTTP 401 Unauthorized
        """
        pytest.skip("TODO: Implementar con TestClient y python-jose")

    def test_valid_token_extracts_org_id(self) -> None:
        """Token válido permite extraer org_id correctamente.

        Arrange: JWT válido con org_id en payload
        Act: Llamar a get_current_org()
        Assert: Retorna el org_id del JWT
        """
        pytest.skip("TODO: Implementar cuando get_current_org esté completo")
