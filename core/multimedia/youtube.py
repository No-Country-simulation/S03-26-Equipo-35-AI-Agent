"""Extractor de transcripciones de YouTube.

Extrae los subtítulos/transcripción de un video de YouTube dado su URL.
Usa la API de subtítulos de YouTube (sin API key, sin descarga de video).

Prioridad de idiomas: español → inglés → cualquier disponible.
"""

import re

import structlog
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = structlog.get_logger()

# Idiomas en orden de preferencia
PREFERRED_LANGUAGES = ["es", "en"]


def extract_video_id(url: str) -> str | None:
    """Extrae el video ID de una URL de YouTube.

    Soporta formatos:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID&t=123
    - https://www.youtube.com/shorts/VIDEO_ID

    Args:
        url: URL del video de YouTube.

    Returns:
        El video ID (11 caracteres) o None si la URL no es válida.
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def get_transcript(url: str) -> dict[str, str]:
    """Extrae la transcripción de texto de un video de YouTube.

    Intenta obtener subtítulos en español, luego inglés,
    luego cualquier idioma disponible.

    Args:
        url: URL completa del video de YouTube.

    Returns:
        Dict con:
        - "text": transcripción concatenada del video.
        - "language": idioma de la transcripción obtenida.
        - "video_id": ID del video.

    Raises:
        ValueError: Si la URL no es válida o no se pudo extraer transcripción.
    """
    video_id = extract_video_id(url)
    if not video_id:
        msg = f"URL de YouTube no válida: {url}"
        raise ValueError(msg)

    logger.info("youtube_transcript_start", video_id=video_id)

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Intentar idiomas preferidos (manual primero, luego auto-generado)
        transcript = None
        language_used = ""

        for lang in PREFERRED_LANGUAGES:
            try:
                transcript = transcript_list.find_transcript([lang])
                language_used = lang
                break
            except NoTranscriptFound:
                continue

        # Si no encontró en idiomas preferidos, tomar el primero disponible
        if transcript is None:
            for t in transcript_list:
                transcript = t
                language_used = t.language_code
                break

        if transcript is None:
            msg = f"No se encontraron subtítulos para el video {video_id}"
            raise ValueError(msg)

        # Obtener los fragmentos y concatenar
        fragments = transcript.fetch()
        full_text = " ".join(
            fragment.text for fragment in fragments if fragment.text.strip()
        )

        logger.info(
            "youtube_transcript_done",
            video_id=video_id,
            language=language_used,
            text_length=len(full_text),
        )

        return {
            "text": full_text,
            "language": language_used,
            "video_id": video_id,
        }

    except TranscriptsDisabled as e:
        logger.warning("youtube_transcripts_disabled", video_id=video_id)
        msg = (
            f"Los subtítulos están desactivados para este video ({video_id}). "
            "Probá subiendo el archivo de video directamente."
        )
        raise ValueError(msg) from e

    except VideoUnavailable as e:
        logger.warning("youtube_video_unavailable", video_id=video_id)
        msg = f"El video {video_id} no está disponible o es privado."
        raise ValueError(msg) from e

    except NoTranscriptFound as e:
        logger.warning("youtube_no_transcript", video_id=video_id)
        msg = (
            f"No se encontraron subtítulos para el video ({video_id}). "
            "Probá subiendo el archivo de video directamente."
        )
        raise ValueError(msg) from e
