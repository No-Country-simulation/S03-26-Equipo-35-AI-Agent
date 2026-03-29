"""Página de aprobaciones y estado de revisión.
Para el MVP local (Semana 4 y 5): Permite a Revisores/Admins validar contenido.
"""
import streamlit as st
from api_client import fetch_api
from components.styles import inject_global_styles, render_page_header

st.set_page_config(page_title="Aprobaciones", page_icon="✅", layout="wide")
inject_global_styles()

if "token" not in st.session_state:
    st.switch_page("app.py")

render_page_header(
    "Centro de <em>Aprobaciones</em>",
    "Revisá, aprobá o rechazá el contenido antes de publicarlo."
)
st.info("Podés aprobar o rechazar historias. Los cambios se reflejarán usando el motor de estados de Supabase.")

try:
    with st.spinner("Cargando historias en revisión..."):
        # En una v2 se filtraría status="en_revision" por query param en el API
        # Por ahora descargamos el listado base y filtramos visualmente
        historias = fetch_api("/stories/", method="GET", params={"limit": 50})
        en_revision = [h for h in historias if h.get("status") in ("en_revision", "borrador")]

        if not en_revision:
            st.markdown("""
            <div style="padding: 40px 0; text-align: center; color: #999;">
                <div style="font-size: 32px; margin-bottom: 12px;">◎</div>
                <div style="font-size: 14px;">No hay historias pendientes de aprobación.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for item in en_revision:
                with st.expander(f"📝 {item.get('title', 'Sin Título')} - {item.get('story_type', 'N/A').title()}"):
                    st.write(item.get("content", "Sin contenido"))

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Aprobar para Publicación", key=f"app_{item.get('id')}", type="primary"):
                            try:
                                fetch_api(
                                    "/approvals/transition",
                                    method="POST",
                                    json={"story_id": item.get("id"), "target_status": "aprobado"}
                                )
                                st.success("Historia aprobada exitosamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with c2:
                        if st.button("❌ Rechazar a Borrador", key=f"rej_{item.get('id')}"):
                            try:
                                fetch_api(
                                    "/approvals/transition",
                                    method="POST",
                                    json={"story_id": item.get("id"), "target_status": "rechazado"}
                                )
                                st.success("Historia devuelta a Borrador.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

except Exception as e:
    st.error(f"Error al cargar: {e}")
