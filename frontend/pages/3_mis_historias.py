"""Página de listado de historias generadas."""
import streamlit as st
from api_client import fetch_api
from components.story_card import render_story_card
from components.styles import inject_global_styles, render_page_header

st.set_page_config(page_title="Mis Historias", page_icon="📚", layout="wide")
inject_global_styles()

if "token" not in st.session_state:
    st.switch_page("app.py")

render_page_header(
    "Mis <em>Historias</em>",
    "Historial de contenidos generados con la voz de tu marca."
)

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Actualizar Historias", type="primary", use_container_width=True):
        st.rerun()

try:
    with st.spinner("Cargando historias..."):
        # Llamar a FastAPI GET /stories/
        res = fetch_api("/stories/", method="GET", params={"limit": 10})

        if not res:
            st.markdown("""
            <div style="padding: 40px 0; text-align: center; color: #999;">
                <div style="font-size: 32px; margin-bottom: 12px;">✦</div>
                <div style="font-size: 14px;">Aún no generaste ninguna historia.</div>
                <div style="font-size: 12px; margin-top: 6px; color: #bbb;">
                    Empezá desde Nueva Historia.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Crear la primera"):
                st.switch_page("pages/2_nueva_historia.py")
        else:
            for item in res:
                render_story_card(item)
except Exception as e:
    st.error(f"Error al cargar las historias: {e}")
