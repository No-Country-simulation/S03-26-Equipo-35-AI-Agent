import asyncio
from dotenv import load_dotenv

import structlog

load_dotenv()

from core.rag.scraper import scrape_url
from core.rag.chunker import chunk_content
from core.rag.embedder import embed_chunks
from db.client import get_admin_client

async def test_ingest():
    org_id = "00000000-0000-0000-0000-000000000999" # Demo org ID from dependencies
    url = "https://www.worldvision.bo/quienes-somos"
    
    print("1. Scraping...")
    scraped = await scrape_url(url, org_id)
    print("Scrape completed. Length:", len(scraped.raw_text))
    
    print("2. Chunking...")
    chunks = chunk_content(scraped.raw_text, scraped.url)
    print("Chunks generated:", len(chunks))
    
    print("3. Embedding...")
    embedded = await embed_chunks(chunks, org_id)
    print("Embedded chunks:", len(embedded))
    if len(embedded) > 0:
        print("Dimensión de embedding (Cohere debería ser 1024):", len(embedded[0].embedding))
    
    print("4. Storing to DB...")
    client = get_admin_client()
    try:
        doc_result = client.table("documents").insert({
            "org_id": org_id,
            "source_url": scraped.url,
            "title": scraped.title,
            "raw_content": scraped.raw_text,
            "doc_type": "web",
            "metadata": scraped.metadata,
        }).execute()
        document_id = doc_result.data[0]["id"]
        print("Doc inserted:", document_id)
    except Exception as e:
        print("Failed inserting into documents:")
        raise
    
    embedding_rows = [
        {
            "org_id": org_id,
            "document_id": document_id,
            "chunk_text": ec.chunk.text,
            "chunk_index": ec.chunk.index,
            "embedding": ec.embedding,
            "metadata": ec.chunk.metadata,
        }
        for ec in embedded
    ]
    try:
        client.table("embeddings").insert(embedding_rows).execute()
        print("Embeddings inserted successfully.")
    except Exception as e:
        print("Failed inserting into embeddings table:")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(test_ingest())
    except Exception as e:
        print("--- FULL TRACEBACK ---")
        import traceback
        traceback.print_exc()
