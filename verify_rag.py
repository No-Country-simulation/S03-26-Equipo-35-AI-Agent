from db.client import get_admin_client
client = get_admin_client()

# Obtener el último documento insertado (que debería ser tu URL)
docs = client.table("documents").select("title, source_url, raw_content").order("created_at", desc=True).limit(1).execute()

if docs.data:
    doc = docs.data[0]
    print(f"\n--- ÚLTIMO DOCUMENTO CREADO ---")
    print(f"URL: {doc['source_url']}")
    print(f"Título detectado: {doc['title']}")
    print(f"Longitud del texto extraído: {len(doc['raw_content'])} caracteres")
    print("\n--- PRIMEROS 500 CARACTERES DEL CONTENIDO REAL ---")
    print(doc['raw_content'][:500] + "...\n")
else:
    print("No hay documentos en la base de datos.")

# Obtener los últimos embeddings (los chunks de texto partitados)
embeddings = client.table("embeddings").select("chunk_text").order("created_at", desc=True).limit(2).execute()

if embeddings.data:
    print("\n--- CHUNKS LISTOS PARA EL RAG ---")
    for i, e in enumerate(embeddings.data):
        print(f"\n[Chunk {i+1}] ({len(e['chunk_text'])} caracteres):")
        print(e['chunk_text'][:250] + "...\n")

