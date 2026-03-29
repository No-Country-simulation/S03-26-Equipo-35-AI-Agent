"""Scraper de contenido web para el pipeline RAG.

Arquitectura de dos tiers:
- Tier 1: httpx + trafilatura (rápido, ~1s, mayoría de sitios)
- Tier 2: Playwright headless (fallback para SPAs con JavaScript)

SEGURIDAD: Sanitizar SIEMPRE las URLs (whitelist HTTPS only, prevenir SSRF).
"""

import ipaddress
import socket
import time
from urllib.parse import urlparse

import httpx
import structlog
import trafilatura

from core.rag import ScrapedContent

logger = structlog.get_logger()

# Umbral mínimo de contenido para considerar Tier 1 exitoso
MIN_CONTENT_LENGTH = 100

# Timeout por tier
HTTPX_TIMEOUT = 30.0
PLAYWRIGHT_TIMEOUT = 15000  # ms

# User-Agent descriptivo
USER_AGENT = "AutoStoryBuilder/0.1 (+https://autostory-builder.com; RAG pipeline)"


def _validate_url(url: str) -> str:
    """Valida y sanitiza una URL contra SSRF.

    Verifica que la URL sea HTTPS, no apunte a redes privadas,
    y tenga una longitud razonable.

    Args:
        url: URL a validar.

    Returns:
        URL sanitizada si es válida.

    Raises:
        ValueError: Si la URL es inválida, no HTTPS, o apunta a red interna.
    """
    if len(url) > 2048:
        msg = f"URL demasiado larga ({len(url)} chars, max 2048)"
        raise ValueError(msg)

    parsed = urlparse(url)

    # Solo HTTPS permitido
    if parsed.scheme != "https":
        msg = f"Solo se permiten URLs HTTPS, recibido: {parsed.scheme}://"
        raise ValueError(msg)

    hostname = parsed.hostname
    if not hostname:
        msg = "URL sin hostname válido"
        raise ValueError(msg)

    # Rechazar hostnames internos conocidos
    blocked_hostnames = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}
    if hostname.lower() in blocked_hostnames:
        msg = f"Hostname bloqueado: {hostname}"
        raise ValueError(msg)

    # Rechazar puertos no estándar
    port = parsed.port
    if port is not None and port != 443:
        msg = f"Solo puerto 443 permitido, recibido: {port}"
        raise ValueError(msg)

    # Resolver DNS y verificar que la IP no sea privada
    try:
        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            msg = f"URL resuelve a IP privada/reservada: {ip_str}"
            raise ValueError(msg)
    except socket.gaierror as e:
        msg = f"No se puede resolver el hostname: {hostname}"
        raise ValueError(msg) from e

    return url


async def _scrape_with_httpx(url: str) -> tuple[str, str]:
    """Tier 1: Scraping rápido con httpx + trafilatura.

    Args:
        url: URL HTTPS a scrapear.

    Returns:
        Tupla (texto_extraído, título).
    """
    async with httpx.AsyncClient(
        timeout=HTTPX_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text

    # Trafilatura extrae el contenido principal automáticamente
    text = trafilatura.extract(
        html,
        include_links=False,
        include_comments=False,
        include_tables=True,
    ) or ""

    # Extraer metadata (título)
    metadata = trafilatura.extract_metadata(html)
    title = metadata.title if metadata and metadata.title else ""

    return text, title


async def _scrape_with_playwright(url: str) -> tuple[str, str]:
    """Tier 2: Fallback con Playwright para sitios con JavaScript pesado.

    Lanza Chromium headless, espera a networkidle, y extrae contenido.

    Args:
        url: URL HTTPS a scrapear.

    Returns:
        Tupla (texto_extraído, título).
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT)
            html = await page.content()
            page_title = await page.title()
        finally:
            await browser.close()

    # Pasar el HTML renderizado por trafilatura
    text = trafilatura.extract(
        html,
        include_links=False,
        include_comments=False,
        include_tables=True,
    ) or ""

    # Título: preferir el de trafilatura metadata, fallback al del page
    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata and metadata.title else page_title) or ""

    return text, title


async def scrape_url(url: str, org_id: str) -> ScrapedContent:
    """Extrae contenido de una URL para ingestión en el pipeline RAG.

    Orquesta los dos tiers de scraping:
    1. Intenta httpx + trafilatura (rápido)
    2. Si el contenido es insuficiente (<100 chars), usa Playwright

    Args:
        url: URL a scrapear — debe ser HTTPS. Se sanitiza internamente.
        org_id: ID de la organización propietaria del contenido.

    Returns:
        ScrapedContent con el texto extraído, título y metadata.

    Raises:
        ValueError: Si la URL no es HTTPS o apunta a una dirección prohibida.
        httpx.HTTPStatusError: Si la URL devuelve un error HTTP.
    """
    validated_url = _validate_url(url)
    start_time = time.perf_counter()
    tier_used = "tier1_httpx"

    # Tier 1: httpx + trafilatura
    try:
        text, title = await _scrape_with_httpx(validated_url)
    except Exception as e:
        logger.warning(
            "scraper_tier1_failed",
            url=validated_url,
            error=str(e)[:100],
            org_id=org_id,
        )
        text, title = "", ""

    # Si Tier 1 no extrajo suficiente contenido → Tier 2
    if len(text) < MIN_CONTENT_LENGTH:
        tier_used = "tier2_playwright"
        logger.info(
            "scraper_falling_back_to_playwright",
            url=validated_url,
            tier1_length=len(text),
            org_id=org_id,
        )
        try:
            text, title = await _scrape_with_playwright(validated_url)
        except Exception as e:
            logger.warning(
                "scraper_tier2_failed",
                url=validated_url,
                error=str(e)[:100],
                org_id=org_id,
            )
            # Si ambos tiers fallan, retornar lo que tengamos
            if not text:
                msg = f"No se pudo extraer contenido de {validated_url}"
                raise ValueError(msg) from e

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "scraper_success",
        url=validated_url,
        tier=tier_used,
        content_length=len(text),
        duration_ms=round(duration_ms, 2),
        org_id=org_id,
    )

    return ScrapedContent(
        url=validated_url,
        title=title or validated_url,
        raw_text=text,
        content_type="text/html",
        metadata={"tier": tier_used, "org_id": org_id},
    )
