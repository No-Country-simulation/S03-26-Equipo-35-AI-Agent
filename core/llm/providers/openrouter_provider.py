"""Proveedor LLM: OpenRouter (fallback final).

Proveedor de fallback cuando Groq devuelve 429 o timeout.
Usa la API compatible con OpenAI a través de OpenRouter.
Modelo configurable — default: llama-3.3-70b.
"""

import os
import time

import structlog
from dotenv import load_dotenv
from openai import OpenAI

from core.llm import LLMResponse

load_dotenv()

logger = structlog.get_logger()

# Configuración
OPENROUTER_TIMEOUT = 60  # segundos
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _get_client() -> OpenAI:
    """Inicializa y retorna el cliente OpenRouter (API compatible con OpenAI).

    Returns:
        Cliente OpenAI configurado para OpenRouter.

    Raises:
        ValueError: Si OPENROUTER_API_KEY no está configurada.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        msg = (
            "OPENROUTER_API_KEY debe estar configurada en .env. "
            "Obtener en: openrouter.ai"
        )
        raise ValueError(msg)
    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        timeout=OPENROUTER_TIMEOUT,
        default_headers={
            "HTTP-Referer": "https://autostory-builder.com",
            "X-Title": "AutoStory Builder",
        },
    )


async def generate(
    prompt: str,
    system_prompt: str = "",
    model: str = "meta-llama/llama-3.3-70b-instruct",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> LLMResponse:
    """Genera contenido usando OpenRouter como fallback.

    Args:
        prompt: Prompt del usuario a enviar al modelo.
        system_prompt: Instrucciones del sistema (rol, contexto).
        model: Modelo de OpenRouter. Default: llama-3.3-70b-instruct.
        max_tokens: Tokens máximos de respuesta. Default: 4096.
        temperature: Creatividad. Default: 0.7.

    Returns:
        LLMResponse con contenido generado y metadata.

    Raises:
        ValueError: Si OPENROUTER_API_KEY no está configurada.
        Exception: Si la API de OpenRouter falla.
    """
    client = _get_client()
    start_time = time.perf_counter()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000
    content = response.choices[0].message.content or ""
    tokens_used = response.usage.total_tokens if response.usage else 0

    logger.info(
        "openrouter_generate",
        model=model,
        content_length=len(content),
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )

    return LLMResponse(
        content=content,
        provider="openrouter",
        model=model,
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )
