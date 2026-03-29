---
description: Implementar endpoint de generación de historia completo
---

# Workflow: Nueva Historia — Generación

Flujo completo para implementar la generación de una historia desde el API.

## Pasos

1. **Validar request** — Pydantic schema con tipo de historia y prompt
2. **Extraer org_id** — Del JWT via `get_current_org()`
3. **Calcular costo** — `core/credits/calculator.calculate_cost()`
4. **Verificar y deducir créditos** — `core/credits/deductor.verify_and_deduct()`
5. **Recuperar contexto RAG** — `core/rag/retriever.retrieve_context()`
6. **Construir prompt** — `core/llm/prompt_builder.build_story_prompt()`
7. **Generar contenido** — `core/llm/router.route()` (con fallback)
8. **Guardar historia** — `db/repositories/story_repository.create_story()`
9. **Retornar respuesta** — Historia generada con metadata

## Manejo de errores

- Si paso 4 falla (sin créditos): HTTP 402 Payment Required
- Si paso 7 falla (LLM error): Reembolsar créditos, HTTP 503
- Si paso 8 falla (DB error): Reembolsar créditos, HTTP 500

## Tests a crear/verificar

- `test_create_story_deducts_credits_first`
- `test_create_story_refunds_on_llm_failure`
- `test_create_story_requires_auth`
