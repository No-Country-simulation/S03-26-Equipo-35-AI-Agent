import asyncio
import os
from dotenv import load_dotenv

import structlog
logger = structlog.get_logger()

# Configurar para que printee todo
import logging
logging.basicConfig(level=logging.ERROR)

load_dotenv()

from core.rag.scraper import scrape_url
from core.rag.chunker import chunk_content
from core.rag.embedder import embed_chunks
from db.client import get_admin_client, get_client

async def test_full_pipeline():
    url = "https://www.worldvision.bo/quienes-somos"
    # Voy a simular lo que hace dependencies.py con el backend real.
    client = get_admin_client()
    
    # Conseguir una org real de la base de datos
    orgs = client.table("organizations").select("id").limit(1).execute()
    if not orgs.data:
        print("No organizations found in database!")
        return
    org_id = orgs.data[0]["id"]
    print("Using real org_id from DB:", org_id)
    
    print("1. Scraping...")
    scraped = await scrape_url(url, org_id)
    print("Scrape completed. Length:", len(scraped.raw_text))
    
    print("2. Chunking...")
    chunks = chunk_content(scraped.raw_text, scraped.url)
    print("Chunks generated:", len(chunks))
    if not chunks:
        print("Scraper didn't find content.")
        return
    
    print("3. Embedding...")
    try:
        embedded = await embed_chunks(chunks, org_id)
        print("Embedded chunks:", len(embedded))
    except Exception as e:
        print("FAILED AT EMBEDDING CHUNKS:")
        import traceback
        traceback.print_exc()
        return
    
    print("4. Storing to DB Documents...")
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
        print("FAILED AT DB INSERT DOCUMENTS:")
        import traceback
        traceback.print_exc()
        return
    
    print("5. Storing to DB Embeddings...")
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
        print("Embeddings inserted successfully!")
    except Exception as e:
        print("FAILED AT DB INSERT EMBEDDINGS:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
