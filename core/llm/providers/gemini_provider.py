"""Proveedor LLM: Google Gemini.

Proveedor para preprocesamiento, clasificación y routing de tareas.
Modelo: gemini-2.0-flash
Fortaleza: Multimodal, contexto largo, inferencia rápida.
"""

import os
import time

import google.generativeai as genai
import structlog
from dotenv import load_dotenv

from core.llm import LLMResponse

load_dotenv()

logger = structlog.get_logger()


def _get_client() -> None:
    """Configura el cliente Gemini con la API key.

    Raises:
        ValueError: Si GOOGLE_API_KEY no está configurada.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        msg = (
            "GOOGLE_API_KEY debe estar configurada en .env. "
            "Obtener en: aistudio.google.com"
        )
        raise ValueError(msg)
    genai.configure(api_key=api_key)


async def generate(
    prompt: str,
    system_prompt: str = "",
    model: str = "gemini-2.0-flash",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> LLMResponse:
    """Genera contenido usando Google Gemini.

    Args:
        prompt: Prompt del usuario a enviar al modelo.
        system_prompt: Instrucciones del sistema (rol, contexto).
        model: Modelo de Gemini. Default: gemini-2.0-flash.
        max_tokens: Tokens máximos de respuesta. Default: 4096.
        temperature: Creatividad (0.0=determinístico, 1.0=creativo).
                     Default: 0.3 para clasificación.

    Returns:
        LLMResponse con contenido generado y metadata.

    Raises:
        ValueError: Si GOOGLE_API_KEY no está configurada.
        Exception: Si la API de Gemini falla.
    """
    _get_client()
    start_time = time.perf_counter()

    generative_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt or None,
        generation_config=genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )

    response = generative_model.generate_content(prompt)

    latency_ms = (time.perf_counter() - start_time) * 1000
    content = response.text or ""

    # Estimar tokens (Gemini no siempre reporta usage)
    tokens_used = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        tokens_used = (
            getattr(response.usage_metadata, "total_token_count", 0) or 0
        )

    logger.info(
        "gemini_generate",
        model=model,
        content_length=len(content),
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )

    return LLMResponse(
        content=content,
        provider="gemini",
        model=model,
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )


async def analyze_asset(
    file_bytes: bytes,
    content_type: str,
    model: str = "gemini-2.0-flash"
) -> str:
    """Extrae contexto, métricas y detalles de un archivo visual usando Gemini.

    Args:
        file_bytes: Los bytes puros de la imagen/pdf.
        content_type: El tipo MIME (ej. 'image/png').
        model: El modelo a usar. Mantenemos gemini-2.0-flash para multimodality rápida.

    Returns:
        Un string descriptivo masivo generado por Gemini sobre el archivo.
    """
    _get_client()

    generative_model = genai.GenerativeModel(model)

    prompt = (
        "Ejerce como un analista de datos y director de arte. Analiza este archivo visual en pleno detalle. "
        "1. Extrae literalmente todos los textos, tablas y métricas que leas.\n"
        "2. Describe qué se ve en la imagen y su propósito o sentimiento.\n"
        "3. Estructura el resultado para que un redactor ciego pueda entender de qué trata el archivo y usar la data para escribir una historia."
    )

    blob = {
        "mime_type": content_type,
        "data": file_bytes,
    }

    try:
        response = await generative_model.generate_content_async([prompt, blob])
        return response.text or "Sin descripción válida del archivo."
    except Exception as e:
        logger.error("gemini_analyze_asset_failed", error=str(e)[:100])
        return f"[Archivo ilegible o error al extraer contexto visual: {str(e)[:50]}]"
