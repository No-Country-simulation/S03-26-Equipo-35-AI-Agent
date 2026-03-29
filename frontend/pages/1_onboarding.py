"""Página de onboarding — ingestión de marca.

Permite a la organización procesar URLs para construir su RAG base.
"""
import streamlit as st
from api_client import fetch_api
from components.styles import inject_global_styles, render_page_header

st.set_page_config(page_title="Base de Marca", page_icon="🌐", layout="wide")
inject_global_styles()

if "token" not in st.session_state:
    st.switch_page("app.py")

render_page_header(
    "Base de <em>Marca</em>",
    "Sincroniza tu sitio web para que la IA aprenda el tono y contexto de tu empresa."
)

with st.form("ingest_form"):
    st.subheader("Ingresar nueva URL")
    st.markdown("""<div class="as-info-box">
        Ingresá una URL con HTTPS. El sistema extraerá el contenido y lo convertirá
        en contexto de marca para la generación de historias.
    </div>""", unsafe_allow_html=True)
    url = st.text_input("URL ej: https://mipagina.com/about", placeholder="https://...")
    title = st.text_input("Título descriptivo (opcional)")

    submit = st.form_submit_button("Escanear sitio web")
    if submit:
        if not url:
            st.error("Debes proveer una URL.")
        elif not url.startswith("https://"):
            st.error("La URL debe comenzar con https://")
        else:
            with st.spinner(f"Analizando sitio web: {url}..."):
                try:
                    res = fetch_api(
                        "/rag/ingest",
                        method="POST",
                        json={"url": url, "title": title}
                    )
                    chunks = res.get("chunks_count", 0)
                    tier = res.get("tier_used", "")
                    st.success(f"✅ ¡URL escaneada exitosamente! Se extrajeron {chunks} fragmentos de contexto.")
                    st.caption(f"Metadata interna: Engine de scraping usado: `{tier}`")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error durante el escaneo: {e}")

st.divider()

st.markdown("### 🗂️ Documentos y Sitios ya asimilados")
st.write("_Las URL asimiladas estarán disponibles automáticamente para la generación de tu próximo contenido._")
# Nota: Podríamos listar los documentos consultando una API `GET /rag/docs` si la hubiera.
# Como el scope actual solo menciona generación e ingestión en week 2/3, lo dejamos como info visual.
