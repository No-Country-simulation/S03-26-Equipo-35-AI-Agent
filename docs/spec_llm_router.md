# Spec: LangGraph Multi-Agent LLM Pipeline

> Fuente de verdad para el framework de agentes LLM orquestado por LangGraph.

## Arquitectura de Grafo (7 Nodos)

La generación narrativa ya no es un simple router procedural, sino un pipeline robusto multi-agente en `core/agents/graph.py` basado en estado inmutable (`TypedDict`).

**Proceso Principal:**
```
1. retrieve_rag     (Vectorial + FTS Cohere/Supabase)
2. analyze_context  (Gemini 2.0 Flash → Destilación de brief y brand)
3. write_content    (Groq Llama-3.3-70B → Redacción base combinando few-shots "Golden Rules")
4. hook_agent       (Groq → Revisa fuerza narrativa y gancho visual)
5. seo_agent        (Groq → Ajusta etiquetas y engagement por red social)
6. qa_editor        (Capa determinista + Evaluador heurístico final)
7. finalize         (Volcado y empaquetado para BD)
```

## Proveedores

| Prioridad | Proveedor | Rol Principal |
|---|---|---|
| 1° | Gemini Flash | Extracción de metadata, OCR de imágenes inyectadas y análisis estructural |
| 2° | Groq | Velocidad hiper-optimizada para la escritura creativa de volumen |
| 3° | OpenRouter | Fallback en caso de que Llama local en Groq arroje Rate Limit HTTP 429 |

## Prompt Structure (Few-Shot Dinámico)

Las plantillas de sistema (en `/core/agents/prompts/`) inyectan contexto RAG y adicionalmente capturan **hasta 3 "Posts Dorados"** (Golden Examples) por Red Social dictados por el usuario para mimetizar la cadencia de la organización.

## Reglas Clave Implementadas

- **Aislamiento de costo:** Los créditos se deducen en el endpoint _antes_ de entrar al Grafo. Se reembolsan asíncronamente si el grafo crashea.
- **Retry Automático:** Si `qa_editor` reprueba el contenido, el router cicla hacia atrás a `write_content` un máximo de 2 veces para auto-corrección sin intervención humana.

## Estado (V2 MVP)
✅ Implementado con Timeouts, Retries (120 segs) y Background Jobs (Redis Celery-like pooling).
