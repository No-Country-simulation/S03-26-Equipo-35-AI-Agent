# 📖 AutoStory Builder

> Plataforma B2B SaaS que convierte materiales empresariales (texto, imágenes) en contenido narrativo profesional usando IA con contexto de marca personalizado por organización.

---

## 🏗️ Stack Tecnológico

| Capa | Tecnología |
|---|---|
| **Frontend** | Streamlit (Python puro) |
| **Backend** | FastAPI en Fly.io |
| **Base de datos** | Supabase (PostgreSQL + pgvector + Auth + Storage) |
| **Cache** | Upstash Redis |
| **Embeddings** | Cohere embed-multilingual-v3 (1024 dims) |
| **LLM Composición** | Groq + Llama 3.3 70B |
| **LLM Routing/Prep** | Gemini 1.5 Flash |
| **LLM Fallback** | OpenRouter |

---

## 🚀 Setup Local

### Requisitos previos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)
- Cuenta en Supabase con proyecto configurado
- API keys para Groq, Google AI, Cohere

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/autostory-builder.git
cd autostory-builder

# 2. Crear entorno virtual
uv venv --python 3.11

# 3. Activar entorno
source .venv/bin/activate

# 4. Verificar
which python  # Debe mostrar .venv/bin/python

# 5. Instalar dependencias
uv pip install -r requirements.txt

# 6. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys y configuración
```

### Ejecutar

```bash
# Backend (FastAPI)
uvicorn api.main:app --reload --port 8000

# Frontend (Streamlit) — en otra terminal
streamlit run frontend/pages/1_onboarding.py
```

---

## 📁 Estructura del Proyecto

```
autostory-builder/
├── api/                  ← HTTP routing y validación (FastAPI)
│   ├── main.py           ← App factory con lifespan
│   ├── dependencies.py   ← Inyección de dependencias
│   ├── middleware.py      ← CORS, logging
│   └── routers/           ← Endpoints por dominio
├── core/                 ← Lógica de negocio PURA (sin framework)
│   ├── rag/               ← scraper, chunker, embedder, retriever
│   ├── llm/               ← router, prompt_builder, providers/
│   ├── credits/           ← calculator, deductor
│   └── approvals/         ← state_machine
├── db/                   ← Acceso a datos
│   ├── client.py          ← Cliente Supabase
│   ├── repositories/      ← Patrón Repository
│   └── migrations/        ← SQL migrations
├── frontend/             ← UI (Streamlit)
│   ├── pages/             ← Páginas de la aplicación
│   └── components/        ← Componentes reutilizables
├── tests/                ← Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docs/                 ← Specs por módulo
```

---

## 🔒 Seguridad

- **Multitenancy**: Toda query incluye filtro `org_id` — aislamiento por organización
- **RLS**: Row Level Security activado en todas las tablas de Supabase
- **JWT**: Autenticación basada en tokens — `org_id` siempre del JWT, nunca del body
- **Créditos**: Verificar → Deducir → LLM → Reembolsar si falla

---

## 🧪 Tests

```bash
# Tests unitarios
pytest tests/unit/ -v

# Coverage
coverage run -m pytest tests/unit/
coverage report
```

---

## 📄 Licencia

MIT

---

*Desarrollado por Diego Silvestre Borges Salces — AI & Data Engineer*
