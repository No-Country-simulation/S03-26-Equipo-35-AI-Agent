"""Scraper de contexto para publicaciones.

Extrae texto de una URL externa para usarlo como contexto de referencia
al generar contenido. NO persiste nada en la base de datos ni genera
embeddings — es efímero, para una sola generación.

IMPORTANTE: Este módulo es independiente del pipeline RAG.
- RAG scraper (core/rag/scraper.py) → ingesta marca → Supabase + embeddings
- Context scraper (este archivo)     → referencia puntual → se inyecta al Analista

Reutiliza la validación SSRF y la lógica de extracción del RAG scraper
pero sin ninguna dependencia de base de datos.
"""

import time

import httpx
import structlog
import trafilatura

logger = structlog.get_logger()

HTTPX_TIMEOUT = 20.0
USER_AGENT = "AutoStoryBuilder/0.1 (+https://autostory-builder.com; context-research)"
MAX_TEXT_LENGTH = 8000  # Limitar para no saturar el prompt del Analista


async def scrape_for_context(url: str) -> dict[str, str]:
    """Extrae el texto principal de una URL para usarlo como contexto de publicación.

    Solo extrae texto — no almacena, no chunka, no embeddea.
    El resultado se inyecta al Agente Analista como contexto de investigación.

    Args:
        url: URL HTTPS del artículo, informe o página de referencia.

    Returns:
        Dict con:
        - "title": título de la página.
        - "text": texto extraído (truncado a MAX_TEXT_LENGTH).
        - "url": URL original.
        - "char_count": cantidad de caracteres extraídos.

    Raises:
        ValueError: Si la URL no es válida, no es HTTPS, o no se pudo extraer contenido.
    """
    # Reutilizar la validación SSRF del RAG scraper
    from core.rag.scraper import _validate_url

    validated_url = _validate_url(url)
    start = time.perf_counter()

    logger.info("context_scrape_start", url=validated_url)

    try:
        async with httpx.AsyncClient(
            timeout=HTTPX_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(validated_url)
            response.raise_for_status()
            html = response.text

    except httpx.HTTPStatusError as e:
        msg = f"La página devolvió error {e.response.status_code}: {validated_url}"
        raise ValueError(msg) from e
    except httpx.RequestError as e:
        msg = f"No se pudo acceder a la URL: {validated_url}"
        raise ValueError(msg) from e

    # Extraer contenido con trafilatura
    text = trafilatura.extract(
        html,
        include_links=False,
        include_comments=False,
        include_tables=True,
    ) or ""

    if len(text) < 50:
        msg = (
            f"No se pudo extraer suficiente contenido de {validated_url}. "
            "La página puede requerir JavaScript o estar bloqueada."
        )
        raise ValueError(msg)

    # Extraer título
    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata and metadata.title else "") or validated_url

    # Truncar si es muy largo para no saturar el prompt
    truncated = text[:MAX_TEXT_LENGTH]
    if len(text) > MAX_TEXT_LENGTH:
        truncated += "\n\n[... contenido truncado por longitud ...]"

    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "context_scrape_done",
        url=validated_url,
        title=title[:50],
        char_count=len(truncated),
        duration_ms=round(duration_ms, 2),
    )

    return {
        "title": title,
        "text": truncated,
        "url": validated_url,
        "char_count": len(truncated),
    }
