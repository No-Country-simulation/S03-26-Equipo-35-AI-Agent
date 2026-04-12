# 📖 AutoStory Builder

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.41+-FF4B4B.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20AI-orange.svg)
![Supabase](https://img.shields.io/badge/Supabase-Database%20%26%20Auth-3ECF8E.svg)

> Plataforma B2B SaaS que convierte materiales empresariales (texto, imágenes, video) en contenido narrativo profesional y escalable usando un pipeline multi-agente de IA con contexto de marca personalizado por organización.

---

## 🏗️ Arquitectura y Tecnologías

| Capa | Tecnología | Propósito |
|---|---|---|
| **Frontend UI** | **Streamlit** (Python puro) | Interfaz de usuario sin código de negocio, delegando toda lógica a la API. |
| **Backend API** | **FastAPI** | Servicio HTTP robusto con validación Pydantic V2 y diseño *Router → Service → Repository*. |
| **Agentic AI** | **LangGraph** | Orquestación multi-agente con grafo de decisión, retry automático y pipeline de especialistas (Hook + SEO + QA). |
| **Embeddings & RAG** | **Cohere v3** (1024 dims) | Indexación semántica y retrieval híbrido (vectorial + full-text) con `pgvector` en Supabase. |
| **LLM (Composición)** | **Groq + Llama 3.3 70B** | Motor principal de generación narrativa con fallback a **OpenRouter**. |
| **LLM (Análisis)** | **Gemini 2.0 Flash** | Preprocesamiento multimodal: análisis de imágenes y destilación de contexto de marca. |
| **Almacenamiento** | **Supabase** | PostgreSQL + Auth + Storage con multitenancy aislado por RLS. |
| **Caching** | **Upstash Redis** | Almacenamiento efímero de alta velocidad. |

---

## 🤖 Grafo Multi-Agente — Versión 2 (LangGraph)

El pipeline de generación ejecuta un grafo con **7 nodos especializados**, un ciclo de retry automático y un sub-pipeline de evaluadores especialistas antes del QA final:

```
┌─────────────────┐     ┌──────────────────────┐     ┌───────────────────────┐
│  retrieve_rag   │────▶│  analyze_context     │────▶│  write_content        │
│  (Supabase RRF) │     │  (Gemini Flash)      │     │  (Groq 70B)           │
│  Vectorial+FTS  │     │  Brief + Few-Shot    │     │  Estilo Dorado        │
└─────────────────┘     └──────────────────────┘     └───────┬───────────────┘
                                                              │
                                                              ▼
                                              ┌───────────────────────────────┐
                                              │  hook_agent                   │
                                              │  (Groq 70B)                   │
                                              │  Evalúa gancho narrativo      │
                                              └───────────────┬───────────────┘
                                                              │
                                                              ▼
                                              ┌───────────────────────────────┐
                                              │  seo_agent                    │
                                              │  (Groq 70B)                   │
                                              │  Evalúa hashtags, CTA, formato│
                                              └───────────────┬───────────────┘
                                                              │
                         ┌──────────────────────┐            ▼
                         │  finalize            │◀────┌──────────────────────┐
                         │  draft → final       │ OK  │  qa_editor           │
                         │  Sin LLM             │     │  (Python + Groq)     │
                         └──────────────────────┘     │  Formato + tono +    │
                                                       │  feedback Hook & SEO │
                                                       └───────┬──────────────┘
                                                               │ Rechazado
                                                               │ (máx 2 reintentos)
                                                               ▼
                                                       ┌──────────────────────┐
                                                       │  write_content       │
                                                       │  (con feedback QA)   │
                                                       └──────────────────────┘
```

**Few-Shot Dinámico:** Antes de escribir, el grafo carga hasta 3 "Posts Dorados" de la base de datos (por red social y tono) e inyecta en el prompt su estructura y cadencia para que el LLM imite el estilo de la marca.

**RAG Híbrido (RRF):** La búsqueda combina similitud semántica coseno (Cohere) con Full-Text Search en español, fusionando ambos rankings con Reciprocal Rank Fusion para no perder nombres propios ni cifras concretas.

**Redes sociales soportadas:** YouTube, Instagram, Facebook, Twitter/X, TikTok, LinkedIn, Blog, Email, Comunicado interno, Nota de prensa.

---

## 🔌 API Endpoints Principales

Toda la API está protegida por Supabase JWT y Rate Limiting por IP/Usuario.

| Método | Endpoint | Descripción | Rate Limit |
|---|---|---|---|
| `POST` | `/stories/generate` | Inicia un job asíncrono para generar contenido. Retorna 202 Accepted con `job_id`. | 20 / hora |
| `GET`  | `/stories/jobs/{id}`| Pooling del estado de generación en tiempo real (Redis). | — |
| `GET`  | `/stories/` | Listado paginado con filtro de `org_id` vía RLS. | 120 / min |
| `POST` | `/rag/ingest/url` | Ingesta contenido (web, youtube) a la base vectorial. | 30 / hora |
| `GET`  | `/stories/{id}/export/image` | Generador de portadas IA vía Hugging Face FLUX.1. | 10 / hora |
| `POST` | `/stories/{id}/versions/{vid}/restore` | Regresa el contenido a un snapshot anterior autoguardado. | 120 / min |
| `GET`  | `/golden-examples/` | Lista los Posts Dorados (moldes de estilo) de la organización. | 120 / min |
| `POST` | `/golden-examples/` | Guarda un ejemplo dorado manualmente (FIFO, máx 3/tipo/tono). | 30 / hora |
| `POST` | `/golden-examples/from-story/{id}` | Convierte una historia generada en molde de estilo. | 30 / hora |
| `DELETE` | `/golden-examples/{id}` | Elimina un molde dorado. | 30 / hora |

---

## 📖 Flujo de Uso (Evaluación de Entregables)

Para evaluar el sistema como **Prototipo Funcional**, recomendamos generar 3 historias con distintos tonos:

1. **Inspiracional (Social Media)**: En *Nueva Historia*, elegí Instagram, poné tono *Inspiracional* y pegá un link de YouTube sobre una ONG.
2. **Técnico (Blog Post)**: Elegí Reporte/Blog, tono *Educativo/Técnico* y usá el Chat RAG para inyectar la URL de una documentación.
3. **Corporativo (Nota Prensa)**: Elegí Prensa, tono *Formal* e ingresá datos financieros en texto libre.

Una vez generadas, entrá a **Mis Historias**, abrí el editor In-Line (Historial de versiones), dale a **Publicar Web** y generá una **Imagen IA** para completarlas profesionalmente.

---

## 🚀 Setup de Desarrollo Local

### Requisitos previos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) instalado a nivel sistema
- Cuenta en [Supabase](https://supabase.com)
- Credenciales API para: Groq, Google AI, Cohere, OpenRouter

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/autostory-builder.git
cd autostory-builder

# 2. Crear entorno virtual
uv venv --python 3.11

# 3. Activar entorno virtual
source .venv/bin/activate        # bash/zsh
source .venv/bin/activate.fish   # fish shell

# 4. Verificar activación (debe mostrar .venv/bin/python)
which python

# 5. Instalar dependencias
uv pip install -e ".[dev]"

# 6. Configurar variables de entorno
cp .env.example .env
# Rellenar con las keys correspondientes
```

### Base de Datos (Supabase)

Ejecutar los scripts SQL en orden desde el **SQL Editor** de Supabase:

```
db/migrations/001_create_organizations.sql
db/migrations/002_create_embeddings.sql
db/migrations/003_create_stories.sql
db/migrations/004_create_approval_history.sql
db/migrations/005_create_credit_system.sql
db/migrations/006_create_match_embeddings_rpc.sql
db/migrations/007_add_stories_extras.sql
db/migrations/008_story_versions.sql
db/migrations/009_share_token.sql
db/migrations/010_create_golden_examples.sql
db/migrations/011_hybrid_search_rpc.sql
```

### Ejecutar el Proyecto

Se requieren dos terminales simultáneas:

**Terminal 1 — Backend (FastAPI):**
```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend (Streamlit):**
```bash
source .venv/bin/activate
streamlit run frontend/app.py
```

---

## 📁 Estructura del Proyecto

```
autostory-builder/
├── api/                      ← HTTP routing y dependencias (FastAPI)
│   ├── main.py               ← App factory, lifespan, health check
│   ├── dependencies.py       ← JWT auth y extracción de org_id
│   ├── middleware.py          ← CORS dinámico + request logging
│   ├── schemas.py            ← Pydantic models base (CurrentUser, etc.)
│   └── routers/              ← Endpoints por dominio
│       ├── stories.py        ← Generación y listado de historias
│       ├── rag.py            ← Ingestión y búsqueda semántica
│       ├── approvals.py      ← Flujo de aprobación
│       └── golden_examples.py← Posts Dorados (Few-Shot moldes)
│
├── core/                     ← Lógica PURA de negocio (sin FastAPI)
│   ├── agents/               ← Grafo LangGraph multi-agente
│   │   ├── graph.py          ← Ensamblaje del StateGraph (7 nodos)
│   │   ├── nodes.py          ← retrieve_rag, analyze_context, write_content,
│   │   │                        hook_agent, seo_agent, qa_editor, finalize
│   │   ├── state.py          ← ContentGenerationState (TypedDict)
│   │   └── prompts/          ← System prompts de agentes (.md)
│   │       ├── qa_editor.md
│   │       ├── hook_agent.md ← Evalúa la fuerza del gancho narrativo
│   │       └── seo_agent.md  ← Evalúa optimización algorítmica
│   ├── llm/                  ← Providers y prompt builder
│   │   ├── providers/        ← gemini, groq, openrouter
│   │   ├── prompt_builder.py ← Construcción de prompts con 5 ejes
│   │   └── prompts/          ← System prompts por red social (.md)
│   ├── rag/                  ← Pipeline RAG completo
│   │   ├── scraper.py        ← Two-tier: httpx+trafilatura → Playwright
│   │   ├── chunker.py        ← 512 tokens, 50 overlap
│   │   ├── embedder.py       ← Cohere embed-multilingual-v3 (1024 dims)
│   │   ├── retriever.py      ← RPC híbrida (RRF vectorial+FTS) con fallback
│   │   └── file_extractor.py ← PDF, DOCX, TXT
│   ├── multimedia/           ← Extractores multimedia
│   │   ├── youtube.py        ← Transcripciones de YouTube
│   │   ├── context_scraper.py← Scraping efímero de referencia
│   │   └── storage.py        ← Upload a Supabase Storage
│   └── approvals/            ← State machine de aprobación
│       ├── state_machine.py  ← Transiciones BORRADOR→...→PUBLICADO
│       └── service.py        ← Orquestación de transiciones
│
├── db/                       ← Acceso a datos
│   ├── client.py             ← Singletons Supabase (anon + admin)
│   ├── repositories/         ← Patrón Repository
│   │   ├── story_repository.py
│   │   ├── approval_repository.py
│   │   ├── version_repository.py
│   │   └── golden_example_repository.py ← FIFO, máx 3/tipo/tono
│   └── migrations/           ← SQL para Supabase (11 migraciones)
│
├── frontend/                 ← UI (Streamlit — Python puro)
│   ├── app.py                ← Entry point + login + dashboard
│   ├── api_client.py         ← httpx → FastAPI
│   ├── pages/                ← 5 páginas del MVP
│   │   ├── 1_onboarding.py   ← Ingestión RAG (URL, PDF, YouTube, audio)
│   │   ├── 2_nueva_historia.py← Generación de contenido
│   │   ├── 3_mis_historias.py ← Historial + editor in-line + moldes ⭐
│   │   ├── 4_aprobaciones.py  ← Circuito de aprobación por roles
│   │   └── 5_configuracion.py ← Perfil + gestión de Posts Dorados
│   └── components/           ← Componentes reutilizables
│
├── tests/                    ← Suite de tests (pytest)
│   ├── unit/                 ← Tests unitarios (state machine, chunker, etc.)
│   └── integration/          ← Tests de integración (graph, auth, RAG)
│
└── docs/                     ← Specs funcionales y roadmap
    ├── roadmap_semanal.md
    ├── spec_approval_flow.md
    ├── spec_auth_multitenancy.md
    ├── spec_credit_system.md
    ├── spec_llm_router.md
    └── spec_rag_pipeline.md
```

---

## 🛡️ Seguridad

- **Aislamiento Multitenancy**: Toda query incluye filtro `org_id` — sin excepción.
- **Row Level Security (RLS)**: Aplicado a nivel PostgreSQL por organización.
- **JWT Auth**: `org_id` se extrae siempre del token verificado por Supabase, nunca del request body.
- **Anti-SSRF**: El scraper valida URLs (HTTPS only, no IPs privadas, no puertos no estándar).
- **Créditos transaccionales**: Verificar → deducir → LLM → reembolsar si falla.

---

## 🔄 Flujo de Aprobación

```
BORRADOR → EN_REVISION → APROBADO → PUBLICADO
               ↓
           RECHAZADO → BORRADOR
```

| Rol | Permisos |
|---|---|
| **Editor** | Crea borradores, envía a revisión |
| **Revisor** | Aprueba o rechaza contenido |
| **Admin** | Publica contenido, acceso completo |

---

## 🧪 Testing

```bash
# Linter
uv run ruff check .

# Tests unitarios
uv run pytest tests/unit/ -v

# Cobertura
uv run coverage run -m pytest tests/unit/
uv run coverage report -m
```

### Tests críticos

| Test | Valida |
|---|---|
| `test_approval_states` | State machine no permite saltar estados |
| `test_rls_isolation` | Org A no ve datos de Org B |
| `test_llm_router` | Fallback Groq → OpenRouter funciona |
| `test_rag_chunker` | Chunking con overlap correcto |
| `test_rag_scraper` | Validación SSRF + sanitización de URLs |
| `test_qa_rules` | Reglas de formato por red social |
| `test_state` | Estado tipado del grafo |

---

## 🚀 Deploy

El backend se despliega en **Fly.io** (ver `fly.toml`):

```bash
fly deploy
```

El frontend se despliega en **Streamlit Community Cloud** (gratis para MVP).

---

*Desarrollado por Diego Silvestre Borges Salces — AI & Data Engineer*
