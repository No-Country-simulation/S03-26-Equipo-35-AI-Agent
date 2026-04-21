"""Proveedor LLM: Groq (Llama 3.3 70B).

Proveedor principal para composición narrativa.
Modelo: llama-3.3-70b-versatile
Fortaleza: Inferencia de texto ultra rápida.
"""

import os
import time

import structlog
from dotenv import load_dotenv
from groq import Groq

from core.llm import LLMResponse

load_dotenv()

logger = structlog.get_logger()

# Configuración
GROQ_TIMEOUT = 60  # segundos


def _get_client() -> Groq:
    """Inicializa y retorna el cliente Groq.

    Returns:
        Cliente Groq configurado.

    Raises:
        ValueError: Si GROQ_API_KEY no está configurada.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        msg = (
            "GROQ_API_KEY debe estar configurada en .env. "
            "Obtener en: console.groq.com"
        )
        raise ValueError(msg)
    return Groq(api_key=api_key, timeout=GROQ_TIMEOUT)


async def generate(
    prompt: str,
    system_prompt: str = "",
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> LLMResponse:
    """Genera contenido usando Groq.

    Args:
        prompt: Prompt del usuario a enviar al modelo.
        system_prompt: Instrucciones del sistema (rol, contexto).
        model: Modelo de Groq. Default: llama-3.3-70b-versatile.
        max_tokens: Tokens máximos de respuesta. Default: 4096.
        temperature: Creatividad. Default: 0.7 (creativo para narrativa).

    Returns:
        LLMResponse con contenido generado y metadata.

    Raises:
        ValueError: Si GROQ_API_KEY no está configurada.
        RateLimitError: Si Groq devuelve 429 (el router hace fallback).
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
        "groq_generate",
        model=model,
        content_length=len(content),
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )

    return LLMResponse(
        content=content,
        provider="groq",
        model=model,
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )
