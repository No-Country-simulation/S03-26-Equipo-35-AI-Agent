---
name: Write Tests
description: Escribir y mantener la suite de tests de AutoStory Builder
---

# Skill: Write Tests

## Contexto
Suite de tests de AutoStory Builder con prioridades por criticidad.

## Archivos del dominio
```
tests/unit/
tests/integration/
tests/e2e/
tests/conftest.py
```

## Prioridades

### 🔴 CRÍTICO (CI bloquea si fallan)
- `test_rls_isolation`: org_A no puede ver datos de org_B
- `test_credit_deduction`: créditos se deducen ANTES del LLM
- `test_approval_states`: no se pueden saltar estados del flujo
- `test_auth_jwt`: endpoints rechazan requests sin JWT válido

### 🟡 IMPORTANTE
- `test_rag_retrieval`: retrieval retorna solo docs de la misma org
- `test_llm_fallback`: si Groq falla, OpenRouter responde

### 🟢 DELEGABLE
- Tests de formato de salida
- Tests del scraper con URLs limpias

## Principios
1. Mockear todos los LLM providers (sin llamadas reales)
2. Fixtures reutilizables en `conftest.py`
3. Estructura Arrange / Act / Assert bien separada
4. Coverage: 80% en `core/`, 100% en créditos y RLS
5. `pytest.skip()` para tests pendientes de implementación

## Fixtures disponibles
- `org_a`, `org_b` — organizaciones para tests de aislamiento
- `mock_groq`, `mock_cohere` — mocks de providers
- `sample_rag_context` — contexto RAG de ejemplo
- `db_test` — mock de cliente Supabase
