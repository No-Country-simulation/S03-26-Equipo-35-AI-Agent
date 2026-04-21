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
