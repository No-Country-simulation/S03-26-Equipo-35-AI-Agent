"""Extractor de texto de archivos para el pipeline RAG.

Extrae texto plano de archivos subidos (PDF, DOCX, TXT)
para procesarlos por el pipeline: chunk → embed → store.

IMPORTANTE: Este módulo solo EXTRAE texto. No chunkea, no embeddea,
no guarda en la base de datos. Eso lo hace el endpoint de ingestión.
"""

import io

import structlog

logger = structlog.get_logger()

# Tipos MIME soportados
SUPPORTED_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

# Extensiones como fallback si content_type no es confiable
EXTENSION_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".text": "txt",
    ".md": "txt",
}


def _extract_pdf(file_bytes: bytes) -> str:
    """Extrae texto de un archivo PDF usando pypdf.

    Args:
        file_bytes: Contenido binario del archivo PDF.

    Returns:
        Texto concatenado de todas las páginas.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(text.strip())

    return "\n\n".join(pages_text)


def _extract_docx(file_bytes: bytes) -> str:
    """Extrae texto de un archivo DOCX usando python-docx.

    Args:
        file_bytes: Contenido binario del archivo DOCX.

    Returns:
        Texto concatenado de todos los párrafos.
    """
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text and para.text.strip():
            paragraphs.append(para.text.strip())

    return "\n\n".join(paragraphs)


def _extract_txt(file_bytes: bytes) -> str:
    """Extrae texto de un archivo de texto plano.

    Intenta decodificar UTF-8 primero, luego Latin-1 como fallback.

    Args:
        file_bytes: Contenido binario del archivo.

    Returns:
        Texto decodificado.
    """
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def detect_file_type(filename: str, content_type: str) -> str | None:
    """Detecta el tipo de archivo por content_type o extensión.

    Args:
        filename: Nombre del archivo con extensión.
        content_type: MIME type reportado por el cliente.

    Returns:
        Tipo detectado ("pdf", "docx", "txt") o None si no es soportado.
    """
    # Primero intentar por content_type
    file_type = SUPPORTED_TYPES.get(content_type)
    if file_type:
        return file_type

    # Fallback por extensión del nombre de archivo
    for ext, ftype in EXTENSION_MAP.items():
        if filename.lower().endswith(ext):
            return ftype

    return None


async def extract_text_from_file(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> str:
    """Extrae texto plano de un archivo subido.

    Soporta PDF, DOCX y TXT. Detecta el tipo por content_type
    o extensión del archivo como fallback.

    Args:
        file_bytes: Contenido binario del archivo.
        filename: Nombre original del archivo (para detectar extensión).
        content_type: MIME type reportado por el upload.

    Returns:
        Texto extraído del archivo.

    Raises:
        ValueError: Si el tipo de archivo no es soportado o el contenido está vacío.
    """
    file_type = detect_file_type(filename, content_type)

    if file_type is None:
        supported = ", ".join(EXTENSION_MAP.keys())
        msg = (
            f"Tipo de archivo no soportado: '{filename}' ({content_type}). "
            f"Formatos aceptados: {supported}"
        )
        raise ValueError(msg)

    logger.info(
        "file_extract_start",
        filename=filename,
        content_type=content_type,
        file_type=file_type,
        size_bytes=len(file_bytes),
    )

    extractors = {
        "pdf": _extract_pdf,
        "docx": _extract_docx,
        "txt": _extract_txt,
    }

    text = extractors[file_type](file_bytes)

    if not text or len(text.strip()) < 10:
        msg = (
            f"No se pudo extraer texto suficiente de '{filename}'. "
            "El archivo puede estar vacío, ser una imagen escaneada sin OCR, "
            "o estar protegido."
        )
        raise ValueError(msg)

    logger.info(
        "file_extract_done",
        filename=filename,
        file_type=file_type,
        text_length=len(text),
    )

    return text.strip()
