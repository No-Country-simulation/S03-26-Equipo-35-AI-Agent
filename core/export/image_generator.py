"""Generador de imágenes con Hugging Face Inference API.

Genera imágenes ilustrativas para historias usando modelos de difusión
(FLUX.1-schnell o Stable Diffusion XL) a través de la API de inferencia
gratuita de Hugging Face.

Fallback: Si HuggingFace falla, genera una tarjeta estática con Pillow.

Requiere: HUGGINGFACE_API_KEY en .env (free tier: ~1000 req/mes)
"""

import os
import re
from io import BytesIO

import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger()

# Modelos en orden de preferencia (FLUX.1-schnell es más rápido)
HF_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
]

HF_TIMEOUT = 120  # segundos — los modelos de imagen pueden tardar




def _build_image_prompt(title: str, story_type: str, content: str = "") -> str:
    """Construye un prompt optimizado para generación de imagen.

    Genera un prompt en inglés (mejor para modelos de difusión)
    basado en el contenido real de la historia, NO en las instrucciones del prompt.

    Args:
        title: Título de la historia (puede contener instrucciones si no se limpió bien).
        story_type: Tipo de contenido (blog, social, press, etc).
        content: Contenido generado de la historia (USAR ESTO preferentemente).

    Returns:
        Prompt optimizado para el modelo de imagen.
    """
    style_hints = {
        "blog": "modern digital illustration, clean design, professional",
        "social": "vibrant social media graphic, eye-catching, modern",
        "instagram": "aesthetic instagram post, vibrant colors, lifestyle",
        "twitter": "minimalist tech illustration, clean lines",
        "youtube": "cinematic thumbnail, dramatic lighting, bold",
        "tiktok": "trendy dynamic graphic, neon accents, Gen-Z style",
        "linkedin": "corporate professional illustration, elegant, business",
        "facebook": "warm community image, inviting, friendly",
        "internal": "corporate office illustration, teamwork, professional",
        "press": "journalistic photo-realistic, press conference, formal",
        "email": "clean marketing visual, call-to-action, modern",
    }

    style = style_hints.get(story_type, "modern digital illustration, professional")

    # ── Extraer el tema real del contenido generado ──
    # Usar el contenido es más confiable que el título (que puede tener instrucciones)
    topic_from_content = ""
    if content:
        # Limpiar markdown y extraer primera línea significativa
        clean_content = re.sub(r'[#*_>]', '', content).strip()
        lines = [l.strip() for l in clean_content.split('\n') if l.strip()]

        # Buscar la primera línea que no sea "ROL" ni instrucciones
        for line in lines[:5]:
            line_lower = line.lower()
            if any(bad in line_lower for bad in ['eres un', 'rol:', 'actua como', 'instrucciones', 'gestor', 'community manager']):
                continue
            if len(line) > 10:  # Línea sustancial
                topic_from_content = line
                break

        # Si no encontramos nada, usar las primeras palabras del contenido
        if not topic_from_content:
            words = clean_content.split()[:8]
            topic_from_content = ' '.join(words)

    # ── Limpiar el título como fallback ──
    clean_title = title
    if " - " in clean_title:
        clean_title = clean_title.split(" - ", 1)[1]

    # Remover stopwords del título
    stopwords = [
        "escribe", "crea", "un post", "una publicacion", "sobre",
        "post de", "publicacion sobre", "hilo de", "articulo",
        "resumen de", "redacta", "genera", "elabora", "desarrolla",
        "#", "rol", "gestor", "community", "manager"
    ]
    clean_title_lower = clean_title.lower()
    for w in stopwords:
        clean_title_lower = clean_title_lower.replace(w, "")
    clean_title = clean_title_lower.strip()

    # ── Decidir qué usar como tema ──
    # Preferir el tema extraído del contenido sobre el título
    if topic_from_content and len(topic_from_content) > 5:
        # Limpiar el tema del contenido
        clean_topic = topic_from_content[:100]  # Limitar longitud
    elif clean_title and len(clean_title) > 3:
        clean_topic = clean_title
    else:
        clean_topic = "social media content"

    # ── Extraer frase hook para el texto de la imagen ──
    text_to_draw = ""
    if content:
        # Buscar una frase corta impactante (hook) del contenido real
        clean_content = re.sub(r'[#*_>\-\"\']', '', content).strip()

        # Buscar líneas cortas que podrían ser hooks (3-6 palabras)
        lines = [l.strip() for l in clean_content.split('\n') if l.strip()]
        for line in lines:
            words = line.split()
            if 3 <= len(words) <= 8:
                # Evitar líneas con palabras de instrucciones
                line_lower = line.lower()
                if not any(bad in line_lower for bad in ['eres', 'rol:', 'gestor', 'debes', 'tarea']):
                    text_to_draw = line[:50]  # Limitar a 50 chars
                    break

        # Si no encontramos hook, usar primeras 4 palabras del contenido limpio
        if not text_to_draw:
            words = [w for w in clean_content.split() if len(w) > 2][:4]
            if words:
                text_to_draw = ' '.join(words)

    prompt = (
        f"Create a high-quality illustration for: {clean_topic}. "
        f"Style: {style}. "
    )

    if text_to_draw:
        prompt += f'Include the text "{text_to_draw}" prominently in the image as a headline, using bold readable typography. '
    else:
        prompt += "No text overlay, pure illustration only. "

    prompt += "High resolution, professional quality, well-composed, 4K."
    logger.info("image_prompt_built", topic=clean_topic[:50], text=text_to_draw[:30] if text_to_draw else "none")
    return prompt


async def generate_with_huggingface(
    title: str,
    story_type: str = "blog",
    content: str = "",
) -> bytes:
    """Genera una imagen usando Hugging Face Inference API.

    Intenta con FLUX.1-schnell primero, luego SDXL como fallback.

    Args:
        title: Título de la historia (se usa para el prompt).
        story_type: Tipo de contenido (para ajustar el estilo).
        content: Contenido generado de la historia (para extraer resumen).

    Returns:
        Bytes de la imagen PNG generada.

    Raises:
        ValueError: Si HUGGINGFACE_API_KEY no está configurada.
        RuntimeError: Si todos los modelos fallan.
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        msg = (
            "HUGGINGFACE_API_KEY debe estar configurada en .env. "
            "Obtener gratis en: https://huggingface.co/settings/tokens"
        )
        raise ValueError(msg)

    prompt = _build_image_prompt(title, story_type, content)

    import httpx

    errors: list[str] = []

    for model in HF_MODELS:
        api_url = f"https://router.huggingface.co/hf-inference/models/{model}"

        try:
            logger.info(
                "hf_image_request",
                model=model,
                prompt_length=len(prompt),
            )

            async with httpx.AsyncClient(timeout=HF_TIMEOUT) as client:
                response = await client.post(
                    api_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"inputs": prompt},
                )

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "image" in content_type:
                        logger.info(
                            "hf_image_success",
                            model=model,
                            size_bytes=len(response.content),
                        )
                        return response.content

                    # Si retornó JSON (error)
                    error_msg = response.text[:200]
                    errors.append(f"{model}: {error_msg}")
                    logger.warning("hf_image_json_response", model=model, response=error_msg)
                    continue

                elif response.status_code == 503:
                    # Modelo cargando — esperable en cold start
                    error_msg = response.text[:200]
                    errors.append(f"{model}: model loading (503)")
                    logger.warning("hf_model_loading", model=model)
                    continue

                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                    errors.append(f"{model}: {error_msg}")
                    logger.warning("hf_image_error", model=model, status=response.status_code)
                    continue

        except Exception as e:
            errors.append(f"{model}: {e!s}")
            logger.error("hf_image_exception", model=model, error=str(e)[:100])
            continue

    # Si todos los modelos de HF fallaron → fallback Pillow
    logger.warning("hf_all_models_failed", errors=errors[:3])
    return _generate_fallback_image(title, story_type)


def _generate_fallback_image(title: str, story_type: str) -> bytes:
    """Genera una tarjeta de imagen estática con Pillow como fallback.

    Se usa cuando Hugging Face no está disponible.

    Args:
        title: Título de la historia.
        story_type: Tipo de contenido.

    Returns:
        Bytes de la imagen PNG.
    """
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1080, 1080

    # Fondo con gradiente sutil
    img = Image.new("RGB", (width, height), color=(25, 25, 35))
    draw = ImageDraw.Draw(img)

    # Gradiente inferior sutil
    for y in range(height // 2, height):
        intensity = int(25 + (y - height // 2) * 0.05)
        draw.line([(0, y), (width, y)], fill=(intensity, intensity, intensity + 10))

    # Acento dorado
    draw.rectangle([(60, 60), (width - 60, 64)], fill=(186, 117, 23))

    # Título — usar fuente default (cross-platform)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 42)
        font_meta = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 22)
        font_brand = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 18)
    except OSError:
        font_title = ImageFont.load_default()
        font_meta = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # Texto del título (con word wrap)
    import textwrap
    wrapped_title = textwrap.fill(title, width=30)
    draw.multiline_text(
        (80, 120),
        wrapped_title,
        fill=(255, 255, 255),
        font=font_title,
        spacing=12,
    )

    # Tipo de contenido
    draw.text(
        (80, height - 140),
        story_type.upper(),
        fill=(186, 117, 23),
        font=font_meta,
    )

    # Branding
    draw.text(
        (80, height - 90),
        "AutoStory Builder",
        fill=(120, 120, 130),
        font=font_brand,
    )

    # Línea inferior dorada
    draw.rectangle([(60, height - 60), (width - 60, height - 56)], fill=(186, 117, 23))

    # Output
    buffer = BytesIO()
    img.save(buffer, format="PNG", quality=95)
    buffer.seek(0)

    logger.info("fallback_image_generated", title=title[:30])
    return buffer.getvalue()
