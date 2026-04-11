"""Constructor de prompts para generación de historias.

Construye prompts con la estructura de 5 ejes:
  [ROL] [CONTEXTO DE MARCA — RAG] [TAREA] [RESTRICCIONES] [FORMATO DE SALIDA]

Los prompts del sistema se almacenan como archivos .md externos
en core/llm/prompts/. Este módulo los combina con el contexto RAG
y la tarea del usuario.

Incluye diccionarios de personalización dinámica para tono, audiencia,
longitud y creatividad.
"""

from pathlib import Path

import structlog

from core.rag import RAGContext

logger = structlog.get_logger()

# Directorio de prompts
PROMPTS_DIR = Path(__file__).parent / "prompts"

# ── Diccionarios de personalización dinámica ──

TONE_INSTRUCTIONS: dict[str, str] = {
    "profesional": "Usa lenguaje profesional pero accesible, tercera persona, equilibrio entre datos y narrativa.",
    "formal": "Usa lenguaje formal, tercera persona, oraciones largas y precisas.",
    "cercano": "Usa lenguaje conversacional, segunda persona (tú), oraciones cortas.",
    "innovador": "Usa lenguaje moderno, referencias a tendencias, tono visionario y orientado al futuro.",
    "inspirador": "Usa metáforas, verbos de acción, frases que evoquen emoción y propósito.",
    "urgente": "Usa frases cortas, datos concretos, verbos imperativos y sentido de urgencia.",
    "persuasivo": "Usa argumentos sólidos, beneficios claros, prueba social y llamados a la acción directos.",
    "emotivo": "Usa lenguaje sensible y empático, apelando directamente a los sentimientos y valores humanos para conectar profundamente.",
}

AUDIENCE_INSTRUCTIONS: dict[str, str] = {
    "clientes": "El lector evalúa si confiar en la empresa. Enfocá el contenido en beneficios tangibles y credibilidad.",
    "donantes": "El lector es un donante que busca impacto verificable con su contribución. Mostrá resultados concretos.",
    "comunidad": "El lector es parte de la comunidad que se beneficia del trabajo. Usá lenguaje inclusivo y cercano.",
    "socios": "El lector es un socio estratégico o partner. Enfocá en resultados conjuntos y oportunidades de colaboración.",
    "inversores": "El lector evalúa tracción, métricas y potencial de crecimiento. Incluí números y proyecciones.",
}

LENGTH_INSTRUCTIONS: dict[str, str] = {
    "corto": "Máximo 150 palabras. Ve directo al punto, sin introducción extensa.",
    "medio": "Entre 300 y 500 palabras. Introducción, desarrollo y cierre.",
    "largo": "Entre 700 y 1000 palabras. Estructura completa con subtítulos.",
}

CREATIVITY_TEMPERATURE: dict[str, float] = {
    "conservador": 0.3,
    "balanceado": 0.6,
    "creativo": 0.9,
}

# Mapeo de story_type a archivo de prompt
_PROMPT_MAP: dict[str, str] = {
    "blog": "story_generator",
    "internal": "story_generator",
    "press": "story_generator",
    "email": "story_generator",
    "youtube": "youtube_script",
    "instagram": "instagram_caption",
    "facebook": "facebook_post",
    "twitter": "twitter_thread",
    "tiktok": "tiktok_script",
    "linkedin": "linkedin_post",
}


def resolve_temperature(creativity: str) -> float:
    """Resuelve el valor de temperature a partir del nivel de creatividad.

    Args:
        creativity: Nivel de creatividad ('conservador', 'balanceado', 'creativo').

    Returns:
        Valor float de temperature para el LLM.
    """
    return CREATIVITY_TEMPERATURE.get(creativity, 0.6)


def build_story_prompt(
    context: RAGContext,
    task: str,
    tone: str = "profesional",
    visual_context: str = "",
    audience: str = "clientes",
    length: str = "medio",
    story_type: str = "blog",
    analytics_data: str = "",
) -> tuple[str, str]:
    """Construye el prompt completo para generación de una historia.

    Combina el contexto de marca (RAG), la tarea del usuario, las
    instrucciones de personalización (tono, audiencia, longitud) y
    opcionalmente los datos analíticos en un prompt estructurado.

    Args:
        context: Contexto RAG con chunks de marca de la organización.
        task: Tarea específica del usuario (ej: 'escribe un blog post sobre X').
        tone: Tono unificado de escritura. Default: 'profesional'.
        visual_context: Contexto visual pre-procesado por Gemini. Default: ''.
        audience: Audiencia destino del contenido. Default: 'clientes'.
        length: Longitud deseada del contenido. Default: 'medio'.
        story_type: Tipo de contenido o red social. Default: 'blog'.
        analytics_data: Datos numéricos/KPIs del usuario. Default: ''.

    Returns:
        Tupla (system_prompt, user_prompt) listos para enviar al LLM.

    Raises:
        ValueError: Si la tarea está vacía.
    """
    if not task.strip():
        msg = "La tarea no puede estar vacía"
        raise ValueError(msg)

    # Cargar system prompt base según tipo de contenido
    system_prompt = _select_system_prompt(story_type)

    # Concatenar instrucciones de impact_reporter si hay datos analíticos
    if analytics_data.strip():
        impact_instructions = _load_system_prompt("impact_reporter")
        system_prompt = f"{system_prompt}\n\n{impact_instructions}"

    # Construir contexto de marca desde chunks RAG
    brand_context = ""
    if context.chunks:
        brand_chunks = "\n\n---\n\n".join(
            chunk.text for chunk in context.chunks
        )
        brand_context = (
            f"\n\n## Contexto de Marca de la Organización\n\n"
            f"Usa la siguiente información para alinear el contenido "
            f"con la identidad de la marca:\n\n{brand_chunks}"
        )
    else:
        brand_context = (
            "\n\n## Nota\n\n"
            "No hay contexto de marca disponible. "
            "Genera contenido con un tono general profesional."
        )

    multimedia_instructions = ""
    if visual_context:
        multimedia_instructions = (
            f"\n\n## Contexto Visual (Archivos adjuntos del usuario)\n\n"
            f"El usuario adjuntó archivos visuales. Aquí tienes el análisis de lo que contienen:\n"
            f"{visual_context}\n\n"
            f"**INSTRUCCIÓN CRÍTICA DE ARTE Y DISEÑO:**\n"
            f"Actúa como Director de Arte. Redacta la historia basándote no solo en el texto "
            f"sino también integrando los insights de estos archivos. "
            f"A lo largo del cuerpo del texto, indica EXACTAMENTE dónde (entre qué párrafos) "
            f"el usuario debería colocar el archivo visual para generar mayor impacto narrativo. "
            f"Hazlo usando la etiqueta literal: `[UBICAR IMAGEN AQUÍ: nombre_del_archivo.ext]`."
        )

    # Construir sección dinámica de personalización
    raw_tones = [t.strip() for t in tone.split(",")]
    tone_instruction = " ".join([
        TONE_INSTRUCTIONS.get(t, TONE_INSTRUCTIONS["profesional"])
        for t in raw_tones if t in TONE_INSTRUCTIONS
    ])
    if not tone_instruction:
        tone_instruction = TONE_INSTRUCTIONS["profesional"]
    audience_instruction = AUDIENCE_INSTRUCTIONS.get(audience, AUDIENCE_INSTRUCTIONS["clientes"])
    length_instruction = LENGTH_INSTRUCTIONS.get(length, LENGTH_INSTRUCTIONS["medio"])

    personalization_section = (
        f"\n\n## Instrucciones de Personalización\n\n"
        f"### Tono\n{tone_instruction}\n\n"
        f"### Audiencia\n{audience_instruction}\n\n"
        f"### Longitud\n{length_instruction}"
    )

    # Sección de datos analíticos si hay
    analytics_section = ""
    if analytics_data.strip():
        analytics_section = (
            f"\n\n## Datos de Impacto del Usuario\n\n"
            f"El usuario proporcionó las siguientes métricas y datos. "
            f"Integralos de forma natural en la narrativa siguiendo las "
            f"instrucciones del reportero de impacto:\n\n"
            f"{analytics_data}"
        )

    # Construir user prompt con los 5 ejes y contexto visual
    user_prompt = (
        f"## Tarea\n\n{task}\n\n"
        f"## Tipo de Contenido\n\n{story_type}\n"
        f"{personalization_section}\n\n"
        f"## Restricciones\n\n"
        f"- El contenido debe estar listo para publicar\n"
        f"- Mantener el tono '{tone}' durante todo el texto\n"
        f"- No incluir notas meta ni disclaimers\n"
        f"{brand_context}"
        f"{multimedia_instructions}"
        f"{analytics_section}"
    )

    logger.info(
        "prompt_built",
        task_length=len(task),
        rag_chunks=len(context.chunks),
        tone=tone,
        audience=audience,
        length=length,
        story_type=story_type,
        has_analytics=bool(analytics_data.strip()),
    )

    return system_prompt, user_prompt


def _select_system_prompt(story_type: str) -> str:
    """Selecciona y carga el system prompt correcto según el tipo de contenido.

    Args:
        story_type: Tipo de contenido o red social.

    Returns:
        Contenido del archivo de prompt correspondiente.
    """
    prompt_name = _PROMPT_MAP.get(story_type, "story_generator")
    return _load_system_prompt(prompt_name)


def _load_system_prompt(prompt_name: str) -> str:
    """Carga un system prompt desde archivos .md en core/llm/prompts/.

    Args:
        prompt_name: Nombre del archivo de prompt (sin extensión).

    Returns:
        Contenido del archivo de prompt.

    Raises:
        FileNotFoundError: Si el archivo de prompt no existe.
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"

    if not prompt_path.exists():
        msg = f"System prompt no encontrado: {prompt_path}"
        raise FileNotFoundError(msg)

    return prompt_path.read_text(encoding="utf-8")
