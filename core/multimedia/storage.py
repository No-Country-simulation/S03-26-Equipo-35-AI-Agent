"""Servicio de almacenamiento multimedia para Supabase Storage.

Sube imágenes y documentos al bucket 'multimedia_assets' para que el LLM Multimodal
pueda procesarlos reteniendo su persistencia.
"""

import uuid
from typing import Any

import structlog
from fastapi import UploadFile

from db.client import get_client

logger = structlog.get_logger()
BUCKET_NAME = "multimedia_assets"


async def upload_file(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    org_id: str,
) -> dict[str, Any]:
    """Sube un archivo a Supabase Storage y retorna su URL pública.

    Genera una ruta única usando uuid para prevenir colisiones.

    Args:
        file_bytes: Contenido binario del archivo.
        filename: Nombre original del archivo (para conservar extensión/metadata).
        content_type: MIME type del archivo.
        org_id: ID de la organización dueña del archivo.

    Returns:
        Diccionario con metadata y la url pública del archivo.

    Raises:
        ValueError: Si falla la subida a Supabase.
    """
    client = get_client()

    # Generar un nombre único: org_id/uuid_filename
    unique_id = str(uuid.uuid4())
    safe_filename = filename.replace(" ", "_").lower()
    path = f"{org_id}/{unique_id}_{safe_filename}"

    try:
        # En la API de python de Supabase, storage.from_ devuelve el storage_bucket_api
        bucket = client.storage.from_(BUCKET_NAME)

        # Subir archivo
        res = bucket.upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type}
        )

        if not res:
            msg = f"No se recibió respuesta al subir el archivo {filename}"
            raise ValueError(msg)

        # Obtener URL pública (asumiendo que el bucket es público para lectura RLS)
        public_url = bucket.get_public_url(path)

        logger.info(
            "file_uploaded_success",
            filename=filename,
            path=path,
            org_id=org_id,
            bytes=len(file_bytes),
        )

        return {
            "path": path,
            "public_url": public_url,
            "filename": filename,
            "content_type": content_type,
        }

    except Exception as e:
        logger.error(
            "file_upload_failed",
            filename=filename,
            error=str(e),
            org_id=org_id,
        )
        raise ValueError(f"Fallo al subir archivo {filename}: {e}") from e
