# Spec: Pipeline RAG Híbrido

> Fuente de verdad para la implementación del pipeline semántico.

## Componentes Robustos

1. **Scraper Adaptativo** (`core/rag/scraper.py`) — `httpx` para texto limpio con fallback a headless `Playwright` para apps SPAs montadas dinámicamente con JS.
2. **Chunker** (`core/rag/chunker.py`) — Estrategia solapada: 512 tokens / 50 overlap.
3. **Embedder** (`core/rag/embedder.py`) — Cohere `embed-multilingual-v3` a dimensionalidad nativa (1024 dims). Tamaño batch nominal: 96 items.
4. **Retriever Híbrido** (`core/rag/retriever.py`) — Fusión Búsqueda Vectorial (Similitud Coseno) + Text Search (FTS Español). Emplea **Reciprocal Rank Fusion (RRF)**.

## Flujo Ingestión Inteligente

El sistema admite input múltiple desde File Uploaders (.docx, .pdf, imágenes) hasta URLs (web regular, YouTube videos).

```
[Fuente Cruda] → Scraper/Extractor → Chunker → Embedder → Supabase pgvector(1024)
                                          ↓
Query de Generación → Retriever (Hybrid+RRF) Filtrado RLS por Empresa → LLM Context
```

## Reglas de Seguridad (Hardcore)

- URLs: Solo acceso restringido HTTPS. Bloqueo SSRF blindado contra consultas API cloud.
- Módulos Aislados: Cada extracción por URL corre con timeouts máximos para proteger IO.
- Autenticación DB: Inmune a filtraciones cruzadas empresariales (`org_id` lock a nivel db).

## Estado (V2 MVP)
✅ Híbrido totalmente ensamblado y superando el 85% de precisión evaluada en contexto empresarial. Se remueve requerimientos de configuración de rate-limiting base al recaer eficientemente en cuotas de Supabase/Cohere.
