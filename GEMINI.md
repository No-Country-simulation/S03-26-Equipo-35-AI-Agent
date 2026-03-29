# AutoStory Builder — Contexto de Proyecto
> Leído automáticamente por Antigravity en cada sesión como contexto ambiente.
> Para convenciones detalladas, consultar Skills en `.agents/skills/`.
> Para memoria de sesiones anteriores, consultar Knowledge Items (KIs).

---

## QUÉ ES ESTE PROYECTO

**AutoStory Builder** — Plataforma B2B SaaS que convierte materiales empresariales
(texto, imágenes) en contenido narrativo profesional usando IA con contexto de marca
personalizado por organización (sistema RAG).

**Estado:** MVP en desarrollo activo — Python, FastAPI, Streamlit, Supabase.

---

## STACK TECNOLÓGICO

| Capa | Tecnología |
|---|---|
| Frontend | Streamlit (Python puro — **sin JavaScript**) |
| Backend | FastAPI en Fly.io |
| Base de datos | Supabase (PostgreSQL + pgvector + Auth + Storage) |
| Cache | Upstash Redis |
| Embeddings | Cohere embed-multilingual-v3 — **1024 dims** (no 1536) |
| LLM Composición | Groq + Llama 3.3 70B |
| LLM Routing/Prep | Gemini 1.5 Flash |
| LLM Fallback | OpenRouter |
| Lenguaje | Python 3.11+ — único lenguaje del proyecto |

---

## ESTRUCTURA DE CARPETAS

```
autostory-builder/
├── api/routers/          ← Solo HTTP routing y validación
├── core/                 ← Lógica de negocio PURA (sin imports de FastAPI)
│   ├── rag/              ← scraper, chunker, embedder, retriever
│   ├── llm/              ← router, prompt_builder, providers/
│   ├── credits/          ← calculator, deductor
│   └── approvals/        ← state_machine
├── db/repositories/      ← Acceso a DB — sin SQL crudo en core/
├── frontend/pages/       ← Streamlit — solo presentación
├── tests/                ← unit/, integration/, e2e/
├── docs/                 ← Specs por módulo — fuente de verdad
├── .agents/skills/       ← Skills de Antigravity por dominio
└── .agents/workflows/    ← Flujos de trabajo comunes
```

**Regla clave:** `core/` es independiente del framework — testeable en aislamiento total.

---

## REGLAS DE SEGURIDAD ABSOLUTAS

1. **Todo query a DB incluye `.eq("org_id", org_id)`** — sin excepción
2. **`org_id` siempre del JWT verificado** — nunca del request body
3. **Créditos: verificar → deducir → llamar LLM** — nunca invertir el orden
4. **Sanitizar URLs del scraper** — prevenir SSRF
5. **Sin API keys en el código** — solo variables de entorno
6. **Nunca push directo a `main`** — todo por Pull Request con CI aprobado

---

## FLUJO DE APROBACIÓN DE CONTENIDO

```
BORRADOR → EN_REVISION → APROBADO → PUBLICADO
               ↓
           RECHAZADO → BORRADOR
```

Roles: `editor` crea, `revisor` aprueba/rechaza, `admin` publica.
Ningún rol puede saltar estados.

---

## COSTOS DE CRÉDITOS

| Operación | Créditos |
|---|---|
| Solo texto | 1 |
| Texto + imagen | 3 |
| Audio (Fase 2) | 5 |

---

## PROHIBICIONES EXPLÍCITAS

- ❌ JavaScript en cualquier parte del proyecto
- ❌ Librerías que requieran GPU local
- ❌ Modelos de IA ejecutados localmente (todo es API)
- ❌ Lógica de negocio en `api/routers/` (va en `core/`)
- ❌ SQL crudo fuera de `db/repositories/`
- ❌ Hardcodear `org_id` o valores mágicos en producción
- ❌ Omitir type hints o docstrings en `core/`

---

## PARA TAREAS ESPECIALIZADAS

Usar los Skills en `.agents/skills/` según el dominio:
- RAG pipeline → `.agents/skills/rag-pipeline/SKILL.md`
- Backend / LLM router → `.agents/skills/backend-endpoint/SKILL.md`
- Frontend Streamlit → `.agents/skills/frontend-streamlit/SKILL.md`
- Tests → `.agents/skills/write-tests/SKILL.md`
- Seguridad → `.agents/skills/security-review/SKILL.md`

---

*Proyecto: AutoStory Builder | Semana actual: ver KIs para estado exacto*
