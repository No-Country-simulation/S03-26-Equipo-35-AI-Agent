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
| **Agentic AI** | **LangGraph** | Orquestación multi-agente con grafo de decisión, retry automático y QA dual (Python + LLM). |
| **Embeddings & RAG** | **Cohere v3** (1024 dims) | Indexación semántica y retrieval asíncrono con `pgvector` en Supabase. |
| **LLM (Composición)** | **Groq + Llama 3.3 70B** | Motor principal de generación narrativa con fallback a **OpenRouter**. |
| **LLM (Análisis)** | **Gemini 2.0 Flash** | Preprocesamiento multimodal: análisis de imágenes y destilación de contexto de marca. |
| **Almacenamiento** | **Supabase** | PostgreSQL + Auth + Storage con multitenancy aislado por RLS. |
| **Caching** | **Upstash Redis** | Almacenamiento efímero de alta velocidad. |

---

## 🤖 Grafo Multi-Agente (LangGraph)

El pipeline de generación ejecuta un grafo con 5 nodos especializados y un ciclo de retry automático:

```
┌─────────────────┐     ┌──────────────────────┐     ┌───────────────────────┐
│  retrieve_rag   │────▶│  analyze_context     │────▶│  write_content        │
│  (Supabase)     │     │  (Gemini Flash)      │     │  (Groq 70B)           │
│  Sin LLM        │     │  Destila brief marca │     │  Genera borrador      │
└─────────────────┘     └──────────────────────┘     └───────┬───────────────┘
                                                              │
                                                              ▼
                        ┌──────────────────────┐     ┌───────────────────────┐
                        │  finalize            │◀────│  qa_editor            │
                        │  draft → final       │ OK  │  (Python + Groq)      │
                        │  Sin LLM             │     │  Formato + tono +     │
                        └──────────────────────┘     │  alucinaciones        │
                                                     └───────┬───────────────┘
                                                              │ Rechazado
                                                              │ (máx 2 reintentos)
                                                              ▼
                                                     ┌───────────────────────┐
                                                     │  write_content        │
                                                     │  (con feedback QA)    │
                                                     └───────────────────────┘
```

**Redes sociales soportadas:** YouTube, Instagram, Facebook, Twitter/X, TikTok, LinkedIn, Blog, Email, Comunicado interno, Nota de prensa.

---

## 🔌 API Endpoints Principales

Toda la API está protegida por Supabase JWT y variables de Rate Limiting por IP/Usuario.

| Método | Endpoint | Descripción | Rate Limit |
|---|---|---|---|
| `POST` | `/stories/generate` | Inicia un job asíncrono para generar contenido. Retorna 202 Accepted con `job_id`. | 20 / hora |
| `GET`  | `/stories/jobs/{id}`| Punteo del estado de generación en tiempo real (Redis). | - |
| `GET`  | `/stories/` | Listado paginado con filtro de `org_id` vía RLS. | 120 / min |
| `POST` | `/rag/ingest/url` | Ingesta contenido (web, youtube) a la base vectorial. | 30 / hora |
| `GET`  | `.../export/image` | Generador de portadas IA vía Hugging Face FLUX.1. | 10 / hora |
| `POST` | `.../versions/{id}/restore`| Regresa el contenido a un snapshot anterior autoguardado. | 120 / min |

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
source .venv/bin/activate

# 4. Verificar activación (debe mostrar .venv/bin/python)
which python

# 5. Instalar dependencias
uv pip install -e ".[dev]"

# 6. Configurar variables de entorno
cp .env.example .env
# Rellenar con las keys correspondientes
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

### 🎮 Demo Rápida (sin APIs)

Para probar la UI sin configurar credenciales de LLM:

1. Levantar el backend (`uvicorn api.main:app --reload`)
2. Levantar el frontend (`streamlit run frontend/app.py`)
3. Clic en **"🚀 Ingresar a la Demo Corporativa"**

El demo token bypasea la autenticación de Supabase y permite navegar toda la interfaz. Las funciones que requieren APIs externas (generación, RAG) necesitan credenciales reales en `.env`.

---

## 📁 Estructura del Proyecto

```
autostory-builder/
├── api/                      ← HTTP routing y dependencias (FastAPI)
│   ├── main.py               ← App factory, lifespan, health check
│   ├── dependencies.py       ← JWT auth, demo token bypass
│   ├── middleware.py          ← CORS dinámico + request logging
│   ├── schemas.py            ← Pydantic models base (CurrentUser, etc.)
│   └── routers/              ← Endpoints por dominio
│       ├── stories.py        ← Generación y listado de historias
│       ├── rag.py            ← Ingestión y búsqueda semántica
│       └── approvals.py      ← Flujo de aprobación
│
├── core/                     ← Lógica PURA de negocio (sin FastAPI)
│   ├── agents/               ← Grafo LangGraph multi-agente
│   │   ├── graph.py          ← Ensamblaje del StateGraph + run_generation_graph()
│   │   ├── nodes.py          ← 5 nodos: RAG, Analista, Escritor, QA, Finalizar
│   │   ├── state.py          ← ContentGenerationState (TypedDict)
│   │   └── prompts/          ← System prompts de agentes (.md)
│   ├── llm/                  ← Providers y prompt builder
│   │   ├── providers/        ← gemini, groq, openrouter
│   │   ├── prompt_builder.py ← Construcción de prompts con 5 ejes
│   │   ├── router.py         ← Router LLM legacy (pre-LangGraph)
│   │   └── prompts/          ← System prompts por red social (.md)
│   ├── rag/                  ← Pipeline RAG completo
│   │   ├── scraper.py        ← Two-tier: httpx+trafilatura → Playwright
│   │   ├── chunker.py        ← 512 tokens, 50 overlap
│   │   ├── embedder.py       ← Cohere embed-multilingual-v3 (1024 dims)
│   │   ├── retriever.py      ← RPC match_embeddings + filtro org_id
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
│   │   └── approval_repository.py
│   └── migrations/           ← SQL para Supabase (7 migraciones)
│
├── frontend/                 ← UI (Streamlit — Python puro)
│   ├── app.py                ← Entry point + login + dashboard
│   ├── api_client.py         ← httpx → FastAPI
│   ├── pages/                ← 5 páginas del MVP
│   └── components/           ← Componentes reutilizables
│
├── tests/                    ← Suite de tests (pytest)
│   ├── unit/                 ← Tests unitarios (state machine, chunker, etc.)
│   └── integration/          ← Tests de integración (graph, auth, RAG)
│
├── docs/                     ← Specs funcionales y roadmap
└── .agents/                  ← Skills y workflows de Antigravity
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
