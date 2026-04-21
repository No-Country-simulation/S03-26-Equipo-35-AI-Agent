"""Página de aprobaciones y estado de revisión.
Para el MVP local (Semana 4 y 5): Permite a Revisores/Admins validar contenido.
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
    "Centro de <em>Aprobaciones</em>",
    "Revisá, aprobá o rechazá el contenido antes de publicarlo."
)
st.info("""
**Flujo de aprobación:** Borrador → En Revisión → Aprobado → Publicado
- **Editor**: Puede enviar borradores a revisión
- **Revisor**: Puede aprobar o rechazar historias en revisión
- **Admin**: Puede publicar historias aprobadas
""")

try:
    with st.spinner("Cargando historias en revisión..."):
        # En una v2 se filtraría status="en_revision" por query param en el API
        # Por ahora descargamos el listado base y filtramos visualmente
        # Mostramos: borrador (enviar a revision), en_revision (aprobar/rechazar),
        #            aprobado (publicar), rechazado (volver a borrador)
        historias = fetch_api("/stories/", method="GET", params={"limit": 50})
        en_revision = [h for h in historias if h.get("status") in
                       ("en_revision", "borrador", "aprobado", "rechazado")]

        if not en_revision:
            st.markdown("""
            <div style="padding: 40px 0; text-align: center; color: #999;">
                <div style="font-size: 32px; margin-bottom: 12px;">◎</div>
                <div style="font-size: 14px;">No hay historias pendientes de aprobación.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for item in en_revision:
                status = item.get("status", "borrador")
                status_label = {
                    "borrador": "📝 Borrador",
                    "en_revision": "👁️ En Revisión",
                    "aprobado": "✅ Aprobado",
                    "rechazado": "❌ Rechazado",
                    "publicado": "🌐 Publicado"
                }.get(status, status)

                with st.expander(f"{item.get('title', 'Sin Título')} - {status_label}"):
                    st.write(item.get("content", "Sin contenido"))
                    st.caption(f"Estado actual: **{status}**")

                    # Botones segun el estado y el flujo permitido
                    if status == "borrador":
                        # En borrador: Enviar a revision (editor/revisor/admin)
                        if st.button("📤 Enviar a Revisión", key=f"rev_{item.get('id')}", type="primary"):
                            try:
                                fetch_api(
                                    "/approvals/transition",
                                    method="POST",
                                    json={"story_id": item.get("id"), "target_status": "en_revision"}
                                )
                                st.success("Historia enviada a revisión.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                    elif status == "en_revision":
                        # En revision: Aprobar o Rechazar (revisor/admin)
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Aprobar", key=f"app_{item.get('id')}", type="primary"):
                                try:
                                    fetch_api(
                                        "/approvals/transition",
                                        method="POST",
                                        json={"story_id": item.get("id"), "target_status": "aprobado"}
                                    )
                                    st.success("Historia aprobada.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with c2:
                            if st.button("❌ Rechazar", key=f"rej_{item.get('id')}"):
                                try:
                                    fetch_api(
                                        "/approvals/transition",
                                        method="POST",
                                        json={"story_id": item.get("id"), "target_status": "rechazado"}
                                    )
                                    st.success("Historia rechazada (vuelve a borrador).")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                    elif status == "aprobado":
                        # Aprobado: Publicar (admin) o Convertir en Molde
                        cols = st.columns([1, 1])
                        with cols[0]:
                            if st.button("🚀 Publicar", key=f"pub_{item.get('id')}", type="primary"):
                                try:
                                    fetch_api(
                                        "/approvals/transition",
                                        method="POST",
                                        json={"story_id": item.get("id"), "target_status": "publicado"}
                                    )
                                    st.success("Historia publicada.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with cols[1], st.expander("⭐ Convertir en Molde", expanded=False):
                                st.caption("Guardar esta historia como Post Dorado para futuras generaciones.")
                                story_type = st.selectbox(
                                    "Tipo de contenido",
                                    ["blog", "social", "internal", "press", "email"],
                                    key=f"molde_type_{item.get('id')}"
                                )
                                tone = st.selectbox(
                                    "Tono",
                                    ["profesional", "cercano", "innovador", "inspirador", "formal", "urgente"],
                                    key=f"molde_tone_{item.get('id')}"
                                )
                                if st.button("Guardar Molde", key=f"save_molde_{item.get('id')}", type="secondary"):
                                    try:
                                        fetch_api(
                                            f"/golden-examples/from-story/{item.get('id')}",
                                            method="POST",
                                            json={"story_type": story_type, "tone": tone}
                                        )
                                        st.success(f"✅ Molde guardado: {story_type} + {tone}. Estará disponible para futuras generaciones.")
                                    except Exception as e:
                                        st.error(f"Error al guardar molde: {e}")

                    elif status == "publicado":
                        # Publicado: Solo convertir en molde (ya está publicado)
                        with st.expander("⭐ Convertir en Molde", expanded=False):
                            st.caption("Guardar esta historia como Post Dorado para futuras generaciones.")
                            story_type = st.selectbox(
                                "Tipo de contenido",
                                ["blog", "social", "internal", "press", "email"],
                                key=f"molde_type_pub_{item.get('id')}"
                            )
                            tone = st.selectbox(
                                "Tono",
                                ["profesional", "cercano", "innovador", "inspirador", "formal", "urgente"],
                                key=f"molde_tone_pub_{item.get('id')}"
                            )
                            if st.button("Guardar Molde", key=f"save_molde_pub_{item.get('id')}", type="secondary"):
                                try:
                                    fetch_api(
                                        f"/golden-examples/from-story/{item.get('id')}",
                                        method="POST",
                                        json={"story_type": story_type, "tone": tone}
                                    )
                                    st.success(f"✅ Molde guardado: {story_type} + {tone}. Estará disponible para futuras generaciones.")
                                except Exception as e:
                                    st.error(f"Error al guardar molde: {e}")

                    elif status == "rechazado" and st.button("🔄 Volver a Borrador (para editar)", key=f"back_{item.get('id')}"):
                        # Rechazado: Volver a borrador para editar (editor/admin)
                        try:
                            fetch_api(
                                "/approvals/transition",
                                method="POST",
                                json={"story_id": item.get("id"), "target_status": "borrador"}
                            )
                            st.success("Historia movida a borrador.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

except Exception as e:
    st.error(f"Error al cargar: {e}")
