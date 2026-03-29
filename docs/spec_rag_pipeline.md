# Spec: Pipeline RAG

> Fuente de verdad para la implementación del pipeline de ingestión y retrieval.

## Componentes

1. **Scraper** (`core/rag/scraper.py`) — Extrae contenido de URLs HTTPS
2. **Chunker** (`core/rag/chunker.py`) — Divide en fragments de 512 tokens / 50 overlap
3. **Embedder** (`core/rag/embedder.py`) — Genera embeddings con Cohere (1024 dims)
4. **Retriever** (`core/rag/retriever.py`) — Búsqueda semántica filtrada por org_id

## Flujo

```
URL → Scraper → Chunker → Embedder → Supabase (pgvector)
                                          ↓
Query → Embedder → Retriever → RAGContext
```

## Reglas de seguridad

- URLs: solo HTTPS, validar contra SSRF
- Retrieval: siempre filtrar por `.eq("org_id", org_id)`
- Embeddings: vector(1024), no 1536

## TODO

- [ ] Definir rate limiting del scraper
- [ ] Definir batch size para embedding
- [ ] Definir estrategia de re-ingestión
