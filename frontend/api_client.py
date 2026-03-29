"""Cliente API para el frontend Streamlit.

Maneja la autenticación con Supabase REST (para obtener el JWT)
y provee llamadas sync con httpx hacia el backend FastAPI.
"""

import os
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_KEY", ""))


def login_with_supabase(email: str, password: str) -> dict[str, Any]:
    """Inicia sesión usando la API REST de Supabase Auth.

    Retorna los datos de sesión (incluyendo access_token).
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Variables de entorno de Supabase faltantes.")

    auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"

    with httpx.Client() as client:
        response = client.post(
            auth_url,
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "password": password
            },
            timeout=10.0
        )

        if response.status_code != 200:
            error_data = response.json()
            raise ValueError(error_data.get("error_description", "Error al iniciar sesión"))

        return response.json()


def fetch_api(
    endpoint: str,
    method: str = "GET",
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
    data: dict[str, Any] | None = None,
) -> Any:
    """Envía un request a la API FastAPI.

    Inyecta automáticamente el JWT desde st.session_state si existe.
    Soporta multipart/form-data enviando los argumentos `files` y `data` a httpx.
    Raises: ValueError si la API devuelve error 4xx/5xx.
    """
    token = st.session_state.get("token")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{API_BASE_URL}{endpoint}"

    with httpx.Client(timeout=180.0) as client:
        try:
            if method == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method == "POST":
                # Si se enviaron archivos o form data puro
                if files or data:
                    response = client.post(url, headers=headers, data=data, files=files, params=params)
                else:
                    response = client.post(url, headers=headers, json=json, params=params)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            if response.status_code >= 400:
                try:
                    err_msg = response.json().get("detail", str(response.text))
                except Exception:
                    err_msg = str(response.text)
                raise ValueError(err_msg)

            return response.json()
        except httpx.RequestError as e:
            raise ValueError(f"Error de conexión con la API: {e}") from e
