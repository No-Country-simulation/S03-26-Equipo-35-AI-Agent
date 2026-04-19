"""Página de Base de Marca — ingestión multi-fuente para RAG.

Permite a la organización alimentar su base de conocimiento desde:
- 🌐 Sitio Web (scraping)
- 📄 Archivos (PDF, DOCX, TXT)
- 📝 Texto libre (guidelines, tono, misión)
- 🎬 YouTube (transcripción de videos)

Cada fuente pasa por el pipeline: texto → chunk → embed → Supabase.
"""
import streamlit as st
from api_client import fetch_api
from components.styles import render_page_header

if "token" not in st.session_state:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.markdown(
        '<meta http-equiv="refresh" content="0; url=./" />',
        unsafe_allow_html=True,
    )
    st.stop()

render_page_header(
    "Base de <em>Marca</em>",
    "Alimentá la memoria de la IA con el contexto de tu empresa — cuanto más datos, mejores publicaciones."
)

# ── Pestañas de ingestión ──

tab_web, tab_files, tab_text, tab_youtube = st.tabs([
    "🌐 Sitio Web",
    "📄 Archivos",
    "📝 Texto",
    "🎬 YouTube",
])

# ── Tab 1: Sitio Web (scraping) ──

with tab_web:
    st.markdown("""<div class="as-info-box">
        Ingresá una URL con HTTPS. El sistema extraerá el contenido y lo convertirá
        en contexto de marca para la generación de historias.
    </div>""", unsafe_allow_html=True)

    with st.form("ingest_web_form"):
        url = st.text_input(
            "URL del sitio web",
            placeholder="https://mipagina.com/about",
        )
        web_title = st.text_input("Título descriptivo (opcional)")
        web_submit = st.form_submit_button("🌐 Escanear Sitio Web")

    if web_submit:
        if not url:
            st.error("Debés proveer una URL.")
        elif not url.startswith("https://"):
            st.error("La URL debe comenzar con https://")
        else:
            with st.spinner(f"Analizando sitio web: {url}..."):
                try:
                    res = fetch_api(
                        "/rag/ingest",
                        method="POST",
                        json={"url": url, "title": web_title},
                    )
                    chunks = res.get("chunks_count", 0)
                    tier = res.get("tier_used", "")
                    st.success(f"✅ ¡URL escaneada! Se extrajeron **{chunks}** fragmentos de contexto.")
                    st.caption(f"Engine de scraping: `{tier}`")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error durante el escaneo: {e}")


# ── Tab 2: Archivos (PDF, DOCX, TXT) ──

with tab_files:
    st.markdown("""<div class="as-info-box">
        Subí archivos de texto como PDFs, documentos Word o archivos de texto plano.
        La IA extraerá el contenido y lo incorporará a la base de conocimiento de tu marca.
    </div>""", unsafe_allow_html=True)

    with st.form("ingest_file_form"):
        uploaded_file = st.file_uploader(
            "Seleccioná un archivo",
            type=["pdf", "docx", "txt", "md"],
            help="Formatos soportados: PDF, DOCX, TXT, Markdown",
        )
        file_title = st.text_input(
            "Título descriptivo (opcional)",
            placeholder="Ej: Guidelines de marca 2025",
        )
        file_submit = st.form_submit_button("📄 Procesar Archivo")

    if file_submit:
        if not uploaded_file:
            st.error("Debés seleccionar un archivo.")
        else:
            with st.spinner(f"Procesando: {uploaded_file.name}..."):
                try:
                    res = fetch_api(
                        "/rag/ingest-file",
                        method="POST",
                        data={"title": file_title},
                        files=[("file", (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type))],
                    )
                    chunks = res.get("chunks_count", 0)
                    file_type = res.get("file_type", "")
                    st.success(
                        f"✅ Archivo procesado: **{uploaded_file.name}** ({file_type.upper()}) "
                        f"→ {chunks} fragmentos extraídos."
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {e}")


# ── Tab 3: Texto libre ──

with tab_text:
    st.markdown("""<div class="as-info-box">
        Pegá directamente texto como guidelines de marca, tono de voz,
        misión, valores o cualquier información que la IA deba conocer.
    </div>""", unsafe_allow_html=True)

    with st.form("ingest_text_form"):
        manual_text = st.text_area(
            "Texto para la base de conocimiento",
            placeholder=(
                "Ej:\n"
                "Nuestra empresa es líder en tecnología educativa.\n"
                "Nuestro tono de comunicación es cercano pero profesional.\n"
                "Evitamos jerga técnica y priorizamos la claridad..."
            ),
            height=200,
        )
        text_title = st.text_input(
            "Título descriptivo",
            placeholder="Ej: Tono de voz corporativo",
        )
        text_submit = st.form_submit_button("📝 Guardar Texto")

    if text_submit:
        if not manual_text or len(manual_text.strip()) < 20:
            st.error("El texto debe tener al menos 20 caracteres.")
        else:
            with st.spinner("Procesando texto..."):
                try:
                    res = fetch_api(
                        "/rag/ingest-text",
                        method="POST",
                        json={
                            "text": manual_text,
                            "title": text_title or "Texto manual",
                        },
                    )
                    chunks = res.get("chunks_count", 0)
                    st.success(f"✅ Texto guardado → {chunks} fragmentos extraídos.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar el texto: {e}")


# ── Tab 4: YouTube ──

with tab_youtube:
    st.markdown("""<div class="as-info-box">
        Pegá un link de YouTube y el sistema extraerá automáticamente
        la transcripción del video para alimentar la base de conocimiento.
    </div>""", unsafe_allow_html=True)

    with st.form("ingest_youtube_form"):
        yt_url = st.text_input(
            "Link de YouTube",
            placeholder="https://www.youtube.com/watch?v=...",
        )
        yt_title = st.text_input(
            "Título descriptivo (opcional)",
            placeholder="Ej: Webinar de producto Q1 2025",
        )
        yt_submit = st.form_submit_button("🎬 Extraer Transcripción")

    if yt_submit:
        if not yt_url:
            st.error("Debés proveer un link de YouTube.")
        else:
            with st.spinner("Extrayendo transcripción del video..."):
                try:
                    res = fetch_api(
                        "/rag/ingest-youtube",
                        method="POST",
                        json={"url": yt_url, "title": yt_title},
                    )
                    chunks = res.get("chunks_count", 0)
                    lang = res.get("language", "")
                    video_id = res.get("video_id", "")
                    st.success(
                        f"✅ Transcripción extraída ({lang}) del video `{video_id}` "
                        f"→ {chunks} fragmentos."
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al extraer la transcripción: {e}")


# ── Documentos ya ingestados ──

st.divider()
st.markdown("### 🗂️ Base de Conocimiento")
st.caption("Todos los documentos y fuentes que la IA usa para entender tu marca.")

try:
    docs_response = fetch_api("/rag/documents", method="GET")
    documents = docs_response.get("documents", [])

    if documents:
        # Mapeo de iconos por tipo de documento
        type_icons = {
            "web": "🌐",
            "file": "📄",
            "text": "📝",
            "youtube": "🎬",
        }

        # Header de la tabla
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1, 3, 3, 1.5, 1])
        with h_col1:
            st.markdown("**Tipo**")
        with h_col2:
            st.markdown("**Título**")
        with h_col3:
            st.markdown("**Fuente**")
        with h_col4:
            st.markdown("**Fecha**")
        with h_col5:
            st.markdown("**Acción**")

        st.markdown("---")

        # Filas de documentos con botón eliminar
        for doc in documents:
            icon = type_icons.get(doc["doc_type"], "📋")
            col1, col2, col3, col4, col5 = st.columns([1, 3, 3, 1.5, 1])

            with col1:
                st.write(f"{icon} {doc['doc_type'].title()}")
            with col2:
                st.write(doc["title"][:55])
            with col3:
                source = doc["source_url"]
                st.write(source[:45] + ("..." if len(source) > 45 else ""))
            with col4:
                st.write(doc["created_at"][:10])
            with col5:
                if st.button("🗑️", key=f"del_{doc['id']}", help="Eliminar documento"):
                    try:
                        fetch_api(
                            f"/rag/documents/{doc['id']}",
                            method="DELETE",
                        )
                        st.success("Documento eliminado.")
                        st.rerun()
                    except Exception as del_err:
                        st.error(f"Error: {del_err}")

        st.caption(f"Total: {len(documents)} documentos")
    else:
        st.info("Aún no hay documentos en tu base de conocimiento. ¡Empezá agregando fuentes arriba!")

except Exception:
    st.warning("No se pudo cargar la lista de documentos. Verificá que el backend esté corriendo.")
