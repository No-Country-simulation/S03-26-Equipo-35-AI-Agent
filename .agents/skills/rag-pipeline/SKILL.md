---
name: RAG Pipeline
description: Implementación del pipeline de ingestión y retrieval semántico
---

# Skill: RAG Pipeline

## Contexto
Pipeline RAG de AutoStory Builder — scraping, chunking, embedding y retrieval.

## Spec de referencia
Leer `docs/spec_rag_pipeline.md` antes de implementar.

## Archivos del dominio
```
core/rag/scraper.py
core/rag/chunker.py
core/rag/embedder.py
core/rag/retriever.py
db/migrations/002_create_embeddings.sql
tests/unit/test_rag_*
tests/integration/test_rag_*
```

## Reglas críticas
1. Cohere embed-multilingual-v3 = **1024 dimensiones** (no 1536)
2. Todo retrieval incluye filtro `.eq("org_id", org_id)` — sin excepción
3. Sanitizar URLs del scraper (whitelist HTTPS, prevenir SSRF)
4. Chunking: 512 tokens con 50 tokens de overlap
5. Los módulos de `core/rag/` NO importan FastAPI ni Streamlit

## Pasos de implementación
1. Implementar `_validate_url()` en scraper.py (SSRF protection)
2. Implementar `scrape_url()` con httpx
3. Implementar `chunk_content()` con tokenización por palabras
4. Implementar `embed_chunks()` con cliente Cohere
5. Implementar `retrieve_context()` con Supabase RPC o query
6. Escribir tests unitarios para cada componente
7. Escribir test de integración end-to-end del pipeline
