"""Página de configuración de la cuenta y voz de marca (Golden Examples)."""
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

user_email = st.session_state.get("user", {}).get("email", "Usuario Desconocido")

render_page_header(
    "Identidad & <em>Configuración</em>",
    "Ajustá tu cuenta y entrená la voz de tu marca guardando ejemplos dorados."
)

st.markdown("### Post Dorados (Moldes de Estilo)")
st.markdown("""<div class="as-info-box">
    Guardá aquí tus mejores publicaciones hechas a mano. El motor de IA las leerá antes de
    escribir para imitar tu estilo exacto. (Límite: 3 por red y tono, se borra la más vieja).
</div>""", unsafe_allow_html=True)

with st.expander("+ Cargar post dorado a mano", expanded=False), st.form("manual_golden_form"):
        c1, c2 = st.columns(2)
        with c1:
            g_type = st.selectbox("Red Social", ["linkedin", "instagram", "twitter", "blog", "facebook"])
        with c2:
            g_tone = st.text_input("Tono", value="profesional")

        g_title = st.text_input("Título descriptivo (ej: Posteo ventas Q3)")
        g_content = st.text_area("Contenido completo del Post", height=150)

        if st.form_submit_button("Guardar Molde ⭐"):
            if len(g_content) < 20:
                st.error("El contenido debe tener al menos 20 caracteres.")
            else:
                try:
                    fetch_api(
                        "/golden-examples/",
                        method="POST",
                        json={
                            "story_type": g_type,
                            "tone": g_tone,
                            "title": g_title,
                            "content": g_content
                        }
                    )
                    st.success("Molde guardado exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# Listar los existentes
st.divider()
try:
    examples = fetch_api("/golden-examples/", method="GET")
    if not examples:
        st.info("No hay moldes dorados guardados todavía.")
    else:
        for ex in examples:
            with st.container():
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**{ex.get('title', 'Sin título')}** (`{ex.get('story_type')}` | `{ex.get('tone')}`)")
                    st.caption(f"Origen: {ex.get('source')} | Creado: {ex.get('created_at', '')[:10]}")
                    st.text(ex.get("content", "")[:100] + "...")
                with col2:
                    if st.button("🗑️", key=f"del_{ex['id']}"):
                        try:
                            fetch_api(f"/golden-examples/{ex['id']}", method="DELETE")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                st.divider()
except Exception as e:
    st.warning(f"No se pudieron cargar los ejemplos: {e}")

