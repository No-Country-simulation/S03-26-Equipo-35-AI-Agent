"""Pipeline RAG — scraping, chunking, embedding y retrieval."""

from dataclasses import dataclass, field


@dataclass
class ScrapedContent:
    """Contenido extraído de una fuente."""

    url: str
    title: str
    raw_text: str
    content_type: str = "text/html"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class Chunk:
    """Fragmento de texto para embedding."""

    text: str
    index: int
    source_url: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class EmbeddedChunk:
    """Chunk con su vector de embedding generado."""

    chunk: Chunk
    embedding: list[float] = field(default_factory=list)  # 1024 dims (Cohere)


@dataclass
class RAGContext:
    """Contexto recuperado por el pipeline RAG para una query."""

    query: str
    chunks: list[Chunk] = field(default_factory=list)
    org_id: str = ""
    total_results: int = 0


@dataclass
class IngestResult:
    """Resultado de una operación de ingestión RAG.

    Retornado por las funciones de core/rag/ingestor.py después de
    completar el pipeline scrape → chunk → embed → store.
    """

    document_id: str
    chunks_count: int
    doc_type: str
    title: str
    metadata: dict[str, str] = field(default_factory=dict)
