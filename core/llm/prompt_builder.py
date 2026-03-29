"""Constructor de prompts para generación de historias.

Construye prompts con la estructura de 5 ejes:
  [ROL] [CONTEXTO DE MARCA — RAG] [TAREA] [RESTRICCIONES] [FORMATO DE SALIDA]

Los prompts del sistema se almacenan como archivos .md externos
en core/llm/prompts/. Este módulo los combina con el contexto RAG
y la tarea del usuario.
"""

from pathlib import Path

import structlog

from core.rag import RAGContext

logger = structlog.get_logger()

# Directorio de prompts
PROMPTS_DIR = Path(__file__).parent / "prompts"


def build_story_prompt(
    context: RAGContext,
    task: str,
    brand_tone: str = "profesional",
    visual_context: str = "",
) -> tuple[str, str]:
    """Construye el prompt completo para generación de una historia.

    Combina el contexto de marca (RAG), la tarea del usuario y el tono
    en un prompt estructurado según los 5 ejes.

    Args:
        context: Contexto RAG con chunks de marca de la organización.
        task: Tarea específica del usuario (ej: 'escribe un blog post sobre X').
        brand_tone: Tono de marca configurado. Default: 'profesional'.

    Returns:
        Tupla (system_prompt, user_prompt) listos para enviar al LLM.

    Raises:
        ValueError: Si la tarea está vacía.
    """
    if not task.strip():
        msg = "La tarea no puede estar vacía"
        raise ValueError(msg)

    # Cargar system prompt base
    system_prompt = _load_system_prompt("story_generator")

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

    # Construir user prompt con los 5 ejes y contexto visual
    user_prompt = (
        f"## Tarea\n\n{task}\n\n"
        f"## Tono de Marca\n\n{brand_tone}\n\n"
        f"## Restricciones\n\n"
        f"- El contenido debe estar listo para publicar\n"
        f"- Mantener el tono '{brand_tone}' durante todo el texto\n"
        f"- No incluir notas meta ni disclaimers\n"
        f"{brand_context}"
        f"{multimedia_instructions}"
    )

    logger.info(
        "prompt_built",
        task_length=len(task),
        rag_chunks=len(context.chunks),
        brand_tone=brand_tone,
    )

    return system_prompt, user_prompt


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
