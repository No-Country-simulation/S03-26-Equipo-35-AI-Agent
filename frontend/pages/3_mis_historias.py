"""Página de listado de historias con editor in-line y versionado.

Funcionalidades:
- Listado de historias generadas con card UI
- Editor in-line: editar título y contenido directamente
- Historial de versiones con posibilidad de restaurar
- Botones de exportación: PDF, Imagen, Markdown
- Botón de publicación web (URL compartible)
"""
import streamlit as st
from api_client import fetch_api
from components.styles import render_page_header, render_status_badge

if "token" not in st.session_state:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.markdown(
        '<meta http-equiv="refresh" content="0; url=./" />',
        unsafe_allow_html=True,
    )
    st.stop()

render_page_header(
    "Mis <em>Historias</em>",
    "Historial de contenidos generados — edita, versiona y exporta."
)

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Actualizar", type="primary", use_container_width=True):
        st.rerun()

try:
    with st.spinner("Cargando historias..."):
        stories = fetch_api("/stories/", method="GET", params={"limit": 20})

        if not stories:
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
            for idx, item in enumerate(stories):
                story_id = item.get("id", "")
                badge_html = render_status_badge(item.get("status", "borrador"))

                # ── Card Header ──
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 16px;">
                    <div style="font-size: 14px; font-weight: 500;">{item.get('title', 'Sin Título')}</div>
                    {badge_html}
                </div>
                <div style="font-size: 11px; color: #999; margin-top: 2px;">
                    {item.get('story_type', '').title()}
                    · {item.get('created_at', '')[:10]}
                    · {item.get('llm_provider', '—')}
                </div>
                """, unsafe_allow_html=True)

                # ── Botones de acción en una fila ──
                btn_cols = st.columns([1, 1, 1, 1, 1.3])

                with btn_cols[0]:
                    edit_key = f"edit_{story_id}_{idx}"
                    if st.button("✏️ Editar", key=edit_key, use_container_width=True):
                        st.session_state[f"editing_{story_id}"] = True

                with btn_cols[1]:
                    ver_key = f"ver_{story_id}_{idx}"
                    if st.button("📜 Versiones", key=ver_key, use_container_width=True):
                        st.session_state[f"versions_{story_id}"] = True

                with btn_cols[2]:
                    pdf_key = f"pdf_{story_id}_{idx}"
                    if st.button("📄 PDF", key=pdf_key, use_container_width=True):
                        try:
                            import os

                            import httpx
                            token = st.session_state.get("token", "")
                            api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
                            with httpx.Client(timeout=30.0) as client:
                                resp = client.get(
                                    f"{api_url}/stories/{story_id}/export/pdf",
                                    headers={"Authorization": f"Bearer {token}"},
                                )
                                if resp.status_code == 200:
                                    st.download_button(
                                        "⬇️ Descargar PDF",
                                        data=resp.content,
                                        file_name=f"historia_{story_id[:8]}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_pdf_{story_id}_{idx}",
                                    )
                                else:
                                    st.error("Error al generar PDF")
                        except Exception as e:
                            st.error(f"Error: {e}")

                with btn_cols[3]:
                    img_key = f"img_{story_id}_{idx}"
                    if st.button("🖼️ Imagen", key=img_key, use_container_width=True):
                        try:
                            import os

                            import httpx
                            token = st.session_state.get("token", "")
                            api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
                            with st.spinner("Generando imagen con IA..."), httpx.Client(timeout=120.0) as client:
                                resp = client.get(
                                    f"{api_url}/stories/{story_id}/export/image",
                                    headers={"Authorization": f"Bearer {token}"},
                                )
                                if resp.status_code == 200:
                                    st.image(resp.content, caption="Imagen generada con IA")
                                    st.download_button(
                                        "⬇️ Descargar Imagen",
                                        data=resp.content,
                                        file_name=f"historia_{story_id[:8]}.png",
                                        mime="image/png",
                                        key=f"dl_img_{story_id}_{idx}",
                                    )
                                else:
                                    st.error("Error al generar imagen")
                        except Exception as e:
                            st.error(f"Error: {e}")

                with btn_cols[4]:
                    share_key = f"share_{story_id}_{idx}"
                    if st.button("🔗 Publicar", key=share_key, use_container_width=True):
                        try:
                            result = fetch_api(
                                f"/stories/{story_id}/share",
                                method="POST",
                            )
                            share_url = result.get("share_url", "")
                            st.success("¡Historia publicada!")
                            st.code(share_url, language=None)
                        except Exception as e:
                            st.error(f"Error: {e}")

                # ── Panel Editor In-line (expandible) ──
                if st.session_state.get(f"editing_{story_id}"):
                    with st.expander("✏️ Editor", expanded=True):
                        # Cargar contenido completo
                        try:
                            full_story = fetch_api(f"/stories/{story_id}", method="GET")
                            full_content = full_story.get("content", "")
                            full_title = full_story.get("title", "")
                        except Exception:
                            full_content = item.get("content", "")
                            full_title = item.get("title", "")

                        new_title = st.text_input(
                            "Título",
                            value=full_title,
                            key=f"edit_title_{story_id}_{idx}",
                        )
                        new_content = st.text_area(
                            "Contenido",
                            value=full_content,
                            height=300,
                            key=f"edit_content_{story_id}_{idx}",
                        )
                        edit_summary = st.text_input(
                            "Resumen del cambio (opcional)",
                            placeholder="Ej: Corregir datos del tercer párrafo",
                            key=f"edit_summary_{story_id}_{idx}",
                        )

                        save_col, cancel_col = st.columns(2)
                        with save_col:
                            if st.button("💾 Guardar cambios", key=f"save_{story_id}_{idx}", type="primary"):
                                try:
                                    payload = {"edit_summary": edit_summary}
                                    if new_content != full_content:
                                        payload["content"] = new_content
                                    if new_title != full_title:
                                        payload["title"] = new_title

                                    if "content" in payload or "title" in payload:
                                        result = fetch_api(
                                            f"/stories/{story_id}",
                                            method="PATCH",
                                            json=payload,
                                        )
                                        st.success(
                                            f"✅ Guardado — versión {result.get('version_number', '?')} creada"
                                        )
                                        st.session_state[f"editing_{story_id}"] = False
                                        st.rerun()
                                    else:
                                        st.info("Sin cambios detectados.")
                                except Exception as e:
                                    st.error(f"Error al guardar: {e}")
                        with cancel_col:
                            if st.button("❌ Cancelar", key=f"cancel_{story_id}_{idx}"):
                                st.session_state[f"editing_{story_id}"] = False
                                st.rerun()

                # ── Panel Historial de Versiones (expandible) ──
                if st.session_state.get(f"versions_{story_id}"):
                    with st.expander("📜 Historial de versiones", expanded=True):
                        try:
                            versions = fetch_api(
                                f"/stories/{story_id}/versions",
                                method="GET",
                            )
                            if not versions:
                                st.info("Esta historia no tiene versiones anteriores.")
                            else:
                                for v in versions:
                                    v_num = v.get("version_number", "?")
                                    v_date = v.get("created_at", "")[:16].replace("T", " ")
                                    v_summary = v.get("edit_summary", "")

                                    st.markdown(f"""
                                    <div style="border-left: 2px solid #BA7517; padding-left: 12px; margin: 8px 0;">
                                        <strong>v{v_num}</strong> — {v_date}
                                        <span style="color: #888; font-size: 12px;">
                                            {f' · {v_summary}' if v_summary else ''}
                                        </span>
                                    </div>
                                    """, unsafe_allow_html=True)

                                    st.code(v.get("content", "")[:300] + "...", language="markdown")

                                    if st.button(
                                        f"🔄 Restaurar v{v_num}",
                                        key=f"restore_{story_id}_{v['id']}_{idx}",
                                    ):
                                        try:
                                            fetch_api(
                                                f"/stories/{story_id}/versions/{v['id']}/restore",
                                                method="POST",
                                            )
                                            st.success(f"Historia restaurada a v{v_num}")
                                            st.session_state[f"versions_{story_id}"] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")

                        except Exception as e:
                            st.error(f"Error al cargar versiones: {e}")

                        if st.button("Cerrar", key=f"close_ver_{story_id}_{idx}"):
                            st.session_state[f"versions_{story_id}"] = False
                            st.rerun()

                # Separador
                st.markdown(
                    '<hr style="border: none; border-top: 0.5px solid rgba(0,0,0,0.07); margin: 4px 0;">',
                    unsafe_allow_html=True,
                )

except Exception as e:
    st.error(f"Error al cargar las historias: {e}")
