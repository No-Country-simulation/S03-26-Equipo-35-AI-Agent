"""Nodos del grafo multi-agente de generación de contenido.

Cada nodo es una función async que recibe el ContentGenerationState
completo y retorna un dict parcial con los campos que modifica.

Patrón obligatorio: errores van al estado (error + status),
nunca se propagan como excepciones desde dentro del grafo.

Nodos implementados:
  1. node_retrieve_rag       — Recupera chunks de Supabase (sin LLM)
  2. node_analyze_context    — Destila el contexto con Gemini Flash (Agente Analista)
  3. node_write_content      — Genera el borrador con Groq 70B (Agente Escritor)
  4. node_qa_editor          — Valida formato + tono + alucinaciones (Agente Editor)
  5. node_finalize           — Mueve draft → final_content (sin LLM)
"""

import time
from pathlib import Path
from typing import Any

import structlog

from core.agents.state import ContentGenerationState
from core.llm.prompt_builder import (
    AUDIENCE_INSTRUCTIONS,
    LENGTH_INSTRUCTIONS,
    TONE_INSTRUCTIONS,
    _select_system_prompt,
)

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent / "prompts"
MAX_RETRIES = 2

# ── Restricciones de formato por red (usadas en QA duro Python) ──
FORMAT_RULES: dict[str, dict[str, Any]] = {
    "twitter": {"max_tweet_chars": 280, "min_tweets": 5, "max_tweets": 7},
    "instagram": {"max_total_chars": 2200},
    "tiktok": {"max_words": 200},
    "facebook": {"min_words": 100, "max_words": 600},
    "youtube": {"required_sections": ["HOOK", "CTA"]},
    "blog": {"required_markers": ["#"]},
    "email": {"required_sections": ["Asunto"]},
    "linkedin": {"max_total_chars": 3000},
    "internal": {},
    "press": {},
}


def _load_agent_prompt(name: str) -> str:
    """Carga un prompt de agente desde core/agents/prompts/.

    Args:
        name: Nombre del archivo de prompt (sin extensión).

    Returns:
        Contenido del archivo de prompt.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt no encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _check_format_rules_python(content: str, story_type: str) -> tuple[bool, str]:
    """Valida las restricciones de formato con lógica Python pura (determinista).

    Las reglas duras se verifican antes del LLM QA para ahorrar tokens
    y garantizar resultados 100% confiables en checks numéricos.

    Args:
        content: Contenido del borrador.
        story_type: Tipo de contenido a validar.

    Returns:
        Tupla (passed: bool, feedback: str). Si passed=True, feedback es vacío.
    """
    rules = FORMAT_RULES.get(story_type, {})
    errors: list[str] = []

    if story_type == "twitter":
        tweets = [t.strip() for t in content.split("\n\n") if t.strip() and t.strip()[0].isdigit()]
        for i, tweet in enumerate(tweets, 1):
            # Remover el número del tweet para contar chars reales
            tweet_text = tweet[tweet.find("/") + 1:].strip() if "/" in tweet[:4] else tweet
            if len(tweet_text) > rules["max_tweet_chars"]:
                errors.append(
                    f"Tweet {i} tiene {len(tweet_text)} caracteres "
                    f"(máximo {rules['max_tweet_chars']}). Reducirlo."
                )
        if tweets and len(tweets) < rules["min_tweets"]:
            errors.append(f"El hilo tiene {len(tweets)} tweets (mínimo {rules['min_tweets']}).")
        if tweets and len(tweets) > rules["max_tweets"]:
            errors.append(f"El hilo tiene {len(tweets)} tweets (máximo {rules['max_tweets']}).")

    elif story_type in ("instagram", "linkedin"):
        if len(content) > rules["max_total_chars"]:
            errors.append(
                f"El contenido tiene {len(content)} caracteres "
                f"(máximo {rules['max_total_chars']}). Reducirlo."
            )

    elif story_type == "tiktok":
        word_count = len(content.split())
        if word_count > rules["max_words"]:
            errors.append(
                f"Script tiene {word_count} palabras "
                f"(máximo {rules['max_words']} para ~60 seg). Reducirlo."
            )

    elif story_type == "facebook":
        word_count = len(content.split())
        if word_count < rules["min_words"]:
            errors.append(f"Post tiene {word_count} palabras (mínimo {rules['min_words']}).")
        if word_count > rules["max_words"]:
            errors.append(f"Post tiene {word_count} palabras (máximo {rules['max_words']}).")

    elif story_type == "youtube":
        for section in rules["required_sections"]:
            if section not in content:
                errors.append(f"Falta la sección [{section}] en el script de YouTube.")

    if errors:
        return False, "Correcciones requeridas (formato):\n" + "\n".join(
            f"{i+1}. {e}" for i, e in enumerate(errors)
        )
    return True, ""


# ── Nodo 1: Recuperar contexto RAG ──

async def node_retrieve_rag(state: ContentGenerationState) -> dict[str, Any]:
    """Recupera chunks de Supabase sin invocar ningún LLM.

    Convierte los RAGContext chunks al formato de lista de dicts
    que el estado del grafo espera.
    """
    try:
        from core.rag.retriever import retrieve_context

        rag_context = await retrieve_context(
            query=state["task"],
            org_id=state["org_id"],
            top_k=5,
        )

        chunks_as_dicts = [
            {"text": chunk.text, "index": chunk.index, "metadata": chunk.metadata}
            for chunk in rag_context.chunks
        ]

        logger.info(
            "node_retrieve_rag_done",
            chunk_count=len(chunks_as_dicts),
            org_id=state["org_id"],
        )
        return {"rag_chunks": chunks_as_dicts}

    except Exception as e:
        logger.error("node_retrieve_rag_failed", error=str(e)[:200], org_id=state["org_id"])
        return {"rag_chunks": [], "error": f"RAG retrieval failed: {e!s}", "status": "error"}


# ── Nodo 2: Agente Analista de Contexto (Gemini Flash) ──

async def node_analyze_context(state: ContentGenerationState) -> dict[str, Any]:
    """Destila el contexto RAG + analytics + assets en un brief de marca.

    Agente: Gemini Flash (multimodal, contexto largo)
    Output: brand_insights (brief destilado) + visual_context (análisis de imágenes)
    """
    try:
        from core.llm.providers import gemini_provider

        # Pre-procesar assets visuales con Gemini multimodal
        visual_context = ""
        for asset in state.get("assets", []):
            try:
                analysis = await gemini_provider.analyze_asset(
                    file_bytes=asset["bytes"],
                    content_type=asset["content_type"],
                )
                visual_context += f"--- {asset['filename']} ---\n{analysis}\n\n"
                logger.info("asset_analyzed", filename=asset["filename"])
            except Exception as e:
                logger.warning("asset_analysis_failed", filename=asset["filename"], error=str(e)[:100])

        # Construir el user prompt para el Analista
        chunks_text = "\n\n---\n\n".join(
            chunk["text"] for chunk in state.get("rag_chunks", [])
        ) or "No hay contexto de marca disponible."

        analytics_section = ""
        if state.get("analytics_data", "").strip():
            analytics_section = f"\n\n## Datos Analíticos del Usuario\n\n{state['analytics_data']}"

        visual_section = ""
        if visual_context:
            visual_section = f"\n\n## Análisis Visual\n\n{visual_context}"

        user_prompt = (
            f"## Chunks de Marca\n\n{chunks_text}"
            f"{analytics_section}"
            f"{visual_section}"
            f"\n\n## Instrucción\n\nGenera el brief de marca destilado siguiendo tu formato."
        )

        system_prompt = _load_agent_prompt("analyst")

        # Llamar a Gemini Flash como agente analista
        from core.llm.providers import gemini_provider
        start = time.perf_counter()
        response = await gemini_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,  # Temperatura baja: análisis objetivo, no creativo
        )
        latency = (time.perf_counter() - start) * 1000

        logger.info(
            "node_analyze_context_done",
            latency_ms=round(latency, 2),
            org_id=state["org_id"],
        )

        return {
            "brand_insights": response.content,
            "visual_context": visual_context,
        }

    except Exception as e:
        logger.error("node_analyze_context_failed", error=str(e)[:200], org_id=state["org_id"])
        # No bloquear el grafo — continuar con marca sin insights
        chunks_text = "\n\n".join(
            chunk["text"] for chunk in state.get("rag_chunks", [])
        ) or "Sin contexto de marca disponible."
        return {
            "brand_insights": f"## Brief de Marca\n\n{chunks_text}",
            "visual_context": "",
        }


# ── Nodo 3: Agente Escritor Especializado (Groq 70B) ──

async def node_write_content(state: ContentGenerationState) -> dict[str, Any]:
    """Genera el borrador de contenido con el prompt especializado por red/formato.

    Agente: Groq Llama 3.3 70B (velocidad narrativa)
    Si es un reintento, inyecta el qa_feedback del Editor para auto-corrección.
    """
    try:
        from core.llm.providers import groq_provider, openrouter_provider

        story_type = state["story_type"]
        retry_count = state.get("retry_count", 0)

        # Seleccionar system prompt especializado (reutiliza prompt_builder existente)
        system_prompt = _select_system_prompt(story_type)

        # Construir instrucciones de personalización (con soporte para múltiples tonos)
        raw_tones = [t.strip() for t in state.get("tone", "profesional").split(",")]
        tone_instr = " ".join([
            TONE_INSTRUCTIONS.get(t, TONE_INSTRUCTIONS["profesional"])
            for t in raw_tones if t in TONE_INSTRUCTIONS
        ])
        if not tone_instr:
            tone_instr = TONE_INSTRUCTIONS["profesional"]
        audience_instr = AUDIENCE_INSTRUCTIONS.get(state["audience"], AUDIENCE_INSTRUCTIONS["clientes"])
        length_instr = LENGTH_INSTRUCTIONS.get(state["length"], LENGTH_INSTRUCTIONS["medio"])

        # Sección de feedback si es reintento
        retry_section = ""
        if retry_count > 0 and state.get("qa_feedback"):
            retry_section = (
                f"\n\n## ⚠️ REVISIÓN REQUERIDA (Intento {retry_count + 1})\n\n"
                f"Tu borrador anterior fue rechazado por el editor. "
                f"Corrige EXACTAMENTE los siguientes puntos antes de volver a escribir:\n\n"
                f"{state['qa_feedback']}\n\n"
                f"No cambies nada que no esté en esta lista."
            )

        # Sección de analytics
        analytics_section = ""
        if state.get("analytics_data", "").strip():
            analytics_section = (
                f"\n\n## Datos de Impacto\n\n"
                f"Integra estos datos de forma natural en la narrativa:\n{state['analytics_data']}"
            )

        user_prompt = (
            f"## Tarea\n\n{state['task']}\n\n"
            f"## Tipo de Contenido\n\n{story_type}\n\n"
            f"## Brief de Marca (Contexto Destilado)\n\n{state.get('brand_insights', '')}\n\n"
            f"## Instrucciones de Personalización\n\n"
            f"**Tono:** {tone_instr}\n\n"
            f"**Audiencia:** {audience_instr}\n\n"
            f"**Longitud:** {length_instr}"
            f"{analytics_section}"
            f"{retry_section}"
        )

        # Intentar Groq primero, fallback a OpenRouter
        start = time.perf_counter()
        try:
            response = await groq_provider.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=state.get("temperature", 0.6),
            )
        except Exception as groq_err:
            logger.warning("writer_groq_failed_fallback", error=str(groq_err)[:100])
            response = await openrouter_provider.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=state.get("temperature", 0.6),
            )

        latency = (time.perf_counter() - start) * 1000

        logger.info(
            "node_write_content_done",
            retry_count=retry_count,
            provider=response.provider,
            latency_ms=round(latency, 2),
            org_id=state["org_id"],
        )

        return {
            "draft_content": response.content,
            "provider": response.provider,
            "model": response.model,
            "latency_ms": round(latency, 2),
            "tokens_used": response.tokens_used,
        }

    except Exception as e:
        logger.error("node_write_content_failed", error=str(e)[:200], org_id=state["org_id"])
        return {"error": f"Writer failed: {e!s}", "status": "error", "draft_content": ""}


# ── Nodo 4: Agente Editor QA (Groq — modelo ligero) ──

async def node_qa_editor(state: ContentGenerationState) -> dict[str, Any]:
    """Valida el borrador contra restricciones de formato, tono y alucinaciones.

    Evaluación en dos capas:
    1. Reglas Python duras (deterministas, sin costo de tokens)
    2. LLM QA (verifica tono y alucinaciones solo si las reglas duras pasan)

    Agente: Groq (modelo ligero — verificación lógica estructurada)
    """
    try:
        draft = state.get("draft_content", "")
        story_type = state["story_type"]
        retry_count = state.get("retry_count", 0)

        if not draft:
            return {
                "qa_approved": False,
                "qa_feedback": "El borrador está vacío.",
                "retry_count": retry_count + 1,
            }

        # Capa 1: Reglas Python duras
        python_passed, python_feedback = _check_format_rules_python(draft, story_type)

        if not python_passed:
            logger.info(
                "qa_python_rules_failed",
                story_type=story_type,
                retry_count=retry_count,
                org_id=state["org_id"],
            )
            if retry_count >= MAX_RETRIES:
                return {
                    "qa_approved": False,
                    "qa_feedback": python_feedback,
                    "status": "qa_failed_max_retries",
                }
            return {
                "qa_approved": False,
                "qa_feedback": python_feedback,
                "retry_count": retry_count + 1,
            }

        # Capa 2: LLM QA
        from core.llm.providers import groq_provider

        system_prompt = _load_agent_prompt("qa_editor")
        user_prompt = (
            f"## Tipo de Contenido\n\n{story_type}\n\n"
            f"## Brief de Marca\n\n{state.get('brand_insights', 'Sin brief disponible.')}\n\n"
            f"## Datos Originales del Usuario\n\n"
            f"{state.get('analytics_data', 'Ninguno')}\n\n"
            f"## Borrador a Revisar\n\n{draft}"
        )

        start = time.perf_counter()
        response = await groq_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Temperatura baja: queremos rigor, no creatividad
        )
        latency = (time.perf_counter() - start) * 1000

        qa_result = response.content.strip()
        approved = qa_result.strip().startswith("APROBADO")

        logger.info(
            "node_qa_editor_done",
            approved=approved,
            retry_count=retry_count,
            latency_ms=round(latency, 2),
            org_id=state["org_id"],
        )

        if approved:
            return {"qa_approved": True, "qa_feedback": ""}

        # QA rechazó — preparar para reintento o finalizar
        feedback = qa_result.replace("RECHAZADO", "").strip()
        if retry_count >= MAX_RETRIES:
            return {
                "qa_approved": False,
                "qa_feedback": feedback,
                "status": "qa_failed_max_retries",
            }

        return {
            "qa_approved": False,
            "qa_feedback": feedback,
            "retry_count": retry_count + 1,
        }

    except Exception as e:
        logger.error("node_qa_editor_failed", error=str(e)[:200], org_id=state["org_id"])
        # Si el QA falla, aprovamos el borrador para no bloquear al usuario
        return {"qa_approved": True, "qa_feedback": "", "error": f"QA error (auto-approved): {e!s}"}


# ── Nodo 5: Finalizar ──

async def node_finalize(state: ContentGenerationState) -> dict[str, Any]:
    """Mueve el borrador al output final. Sin LLM — solo gestión de estado.

    Si el QA aprobó: `final_content = draft_content`
    Si el QA falló por reintentos: `final_content = draft_content` + marca `status`
    """
    draft = state.get("draft_content", "")
    qa_approved = state.get("qa_approved", False)
    current_status = state.get("status", "ok")

    final_status = current_status if not qa_approved else "ok"

    logger.info(
        "node_finalize_done",
        qa_approved=qa_approved,
        content_length=len(draft),
        status=final_status,
        org_id=state["org_id"],
    )

    return {
        "final_content": draft,
        "status": final_status,
    }
