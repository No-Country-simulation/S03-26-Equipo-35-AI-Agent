---
name: Backend Endpoint
description: Implementación de endpoints FastAPI con el patrón Router → Service → Repository
---

# Skill: Backend Endpoint

## Contexto
Endpoints FastAPI de AutoStory Builder siguiendo arquitectura limpia.

## Specs de referencia
- `docs/spec_llm_router.md`
- `docs/spec_credit_system.md`
- `docs/spec_approval_flow.md`
- `docs/spec_auth_multitenancy.md`

## Archivos del dominio
```
api/routers/
api/dependencies.py
api/middleware.py
api/main.py
core/llm/
core/credits/
core/approvals/
db/repositories/
```

## Reglas críticas
1. Créditos: VERIFICAR → DEDUCIR → llamar LLM → (si falla: reembolsar)
2. `org_id`: extraer del JWT verificado, NUNCA del request body
3. LLM routing: Gemini Flash → Groq Llama 70B → OpenRouter fallback
4. Lógica de negocio en `core/` — routers solo validan y delegan
5. `async def` en todos los endpoints
6. `response_model` Pydantic en todos los endpoints

## Patrón de endpoint
```python
@router.post("/resource", response_model=ResourceResponse)
async def create_resource(
    request: ResourceRequest,
    org_id: str = Depends(get_current_org),
) -> ResourceResponse:
    # 1. Validar request (Pydantic lo hace automáticamente)
    # 2. Delegar a core/
    result = await core_service.process(request.data, org_id)
    # 3. Retornar response
    return ResourceResponse(**result)
```
