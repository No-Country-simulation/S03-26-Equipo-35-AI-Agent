"""Página de creación de nueva historia."""
import streamlit as st
from api_client import fetch_api
from components.loading_states import simulate_loading_animation
from components.styles import render_page_header

if "token" not in st.session_state:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.markdown(
        '<meta http-equiv="refresh" content="0; url=./" />',
        unsafe_allow_html=True,
    )
    st.stop()

render_page_header(
    "Nueva <em>Historia</em>",
    "Describí lo que necesitás — la IA aplicará la voz y contexto de tu marca."
)

col1, col2 = st.columns([2, 1])

with col1:
    # ── Selector de tipo + Redes sociales: FUERA del form para reactividad ──
    story_type = st.selectbox(
        "Tipo de Contenido",
        options=["blog", "redes sociales", "internal", "press", "email"],
        format_func=lambda x: {
            "blog": "📝 Blog Post",
            "redes sociales": "📱 Redes Sociales",
            "internal": "🏢 Comunicación Interna",
            "press": "📰 Comunicado de Prensa",
            "email": "📧 Email",
        }.get(x, x.title()),
        key="story_type_selector",
    )

    # Sección de redes sociales (condicional — se re-renderiza al cambiar el selectbox)
    selected_networks: list[str] = []
    if story_type == "redes sociales":
        st.markdown(
            "<p style='font-size: 14px; font-weight: 500; margin-bottom: 5px;'>"
            "Seleccioná las redes (máximo 3)</p>",
            unsafe_allow_html=True,
        )
        net_col1, net_col2, net_col3, net_col4, net_col5, net_col6 = st.columns(6)
        with net_col1:
            if st.checkbox("YouTube", key="net_youtube"):
                selected_networks.append("youtube")
        with net_col2:
            if st.checkbox("Instagram", key="net_instagram"):
                selected_networks.append("instagram")
        with net_col3:
            if st.checkbox("Facebook", key="net_facebook"):
                selected_networks.append("facebook")
        with net_col4:
            if st.checkbox("X / Twitter", key="net_twitter"):
                selected_networks.append("twitter")
        with net_col5:
            if st.checkbox("TikTok", key="net_tiktok"):
                selected_networks.append("tiktok")
        with net_col6:
            if st.checkbox("LinkedIn", key="net_linkedin"):
                selected_networks.append("linkedin")

        if len(selected_networks) > 3:
            st.warning("Máximo 3 redes por solicitud. Se usarán las primeras 3.")
            selected_networks = selected_networks[:3]

    # ── Formulario de generación (los campos sin interactividad condicional) ──
    with st.form("generate_form"):
        task = st.text_area(
            "Instrucciones de la tarea (Prompt)",
            placeholder="Ej: Escribe un post anunciando el lanzamiento de nuestra nueva plataforma...",
            height=150,
        )

        # ── Personalización dinámica ──
        st.markdown("---")
        st.markdown(
            "<p style='font-size: 16px; font-weight: 600; margin-bottom: 10px;'>"
            "⚙️ Personalización</p>",
            unsafe_allow_html=True,
        )

        pers_col1, pers_col2, pers_col3 = st.columns(3)

        with pers_col1:
            selected_tones = st.multiselect(
                "Tono de Escritura",
                options=["profesional", "formal", "cercano", "innovador", "inspirador", "urgente", "persuasivo", "emotivo"],
                default=["profesional"],
                max_selections=2,
                help="Elige hasta 2 estilos combinados de redacción (Ej: inspirador y cercano).",
            )
            tone = ", ".join(selected_tones) if selected_tones else "profesional"

        with pers_col2:
            audience = st.selectbox(
                "Audiencia",
                options=["clientes", "donantes", "comunidad", "socios", "inversores"],
                format_func=lambda x: {
                    "clientes": "🎯 Clientes",
                    "donantes": "🤝 Donantes",
                    "comunidad": "🌍 Comunidad",
                    "socios": "🤝 Socios / Partners",
                    "inversores": "📊 Inversores",
                }.get(x, x.title()),
                help="Define para quién se escribe el contenido.",
            )

        with pers_col3:
            length = st.selectbox(
                "Longitud",
                options=["corto", "medio", "largo"],
                index=1,
                format_func=lambda x: {
                    "corto": "📄 Corto (~150 palabras)",
                    "medio": "📋 Medio (300-500 palabras)",
                    "largo": "📑 Largo (700-1000 palabras)",
                }.get(x, x.title()),
                help="Define la extensión del contenido generado.",
            )

        creativity = st.select_slider(
            "Nivel de Creatividad",
            options=["Conservador", "Balanceado", "Creativo"],
            value="Balanceado",
            help="Conservador: preciso y factual · Balanceado: equilibrio · Creativo: más libre y original.",
        )

        # ── Datos analíticos ──
        analytics_data = ""
        has_analytics = st.checkbox(
            "¿Tu contenido tiene métricas o datos de impacto?",
            help="Activá esto si querés incluir números, KPIs o datos que la IA integrará en la narrativa.",
        )
        if has_analytics:
            analytics_data = st.text_area(
                "Pegá aquí tus datos: ventas, beneficiarios, cobertura, KPIs, etc.",
                placeholder="Ej: 5,000 beneficiarios en 2025, 3 países, $200K recaudados, 95% de satisfacción...",
                height=100,
                max_chars=2000,
                help="Máximo 2000 caracteres. La IA integrará estos datos de forma natural en la narrativa.",
            )

        # ── Contexto Multimedia ──
        st.markdown("---")
        st.markdown(
            "<p style='font-size: 14px; font-weight: 500; margin-bottom: 5px;'>"
            "Contexto Multimedia (Opcional)</p>",
            unsafe_allow_html=True,
        )
        uploaded_files = st.file_uploader(
            "Sube imágenes, documentos, audio o video para que la IA los analice.",
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg", "pdf", "mp3", "wav", "ogg", "mp4", "mov", "webm"],
            help="Imágenes y PDFs: analizados visualmente. Audio/Video: transcripción automática disponible próximamente.",
        )

        youtube_url = st.text_input(
            "🎬 Link de YouTube (Opcional)",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Pegá un link de YouTube y la IA extraerá automáticamente la transcripción del video como contexto.",
        )

        reference_url = st.text_input(
            "🔗 Link de Referencia (Opcional)",
            placeholder="https://ejemplo.com/articulo-con-datos...",
            help="Pegá el link de un artículo, informe o página web. La IA extraerá el texto y lo usará como contexto de investigación.",
        )

        submit = st.form_submit_button("Generar Borrador ✨", type="primary")

with col2:
    st.markdown("""<div class="as-info-box">
    <strong>Tip:</strong> Cuanto más detallada sea la instrucción,
    mejor resultado.<br><br>
    <strong>Personalización:</strong><br>
    🎯 Tono — Cómo suena el texto<br>
    👥 Audiencia — Para quién se escribe<br>
    📏 Longitud — Extensión del contenido<br>
    🎨 Creatividad — Qué tan libre es la IA<br><br>
    <strong>Archivos soportados:</strong><br>
    🖼️ Imágenes y PDFs — analizados visualmente ahora.<br>
    🎙️ Audio y video — transcripción automática disponible próximamente.
</div>""", unsafe_allow_html=True)

if submit:
    if not task:
        st.error("Debes proveer las instrucciones de la tarea.")
    elif story_type == "redes sociales" and not selected_networks:
        st.error("Seleccioná al menos una red social.")
    else:
        # Normalizar creativity al formato esperado por el backend
        creativity_value = creativity.lower()  # "Conservador" → "conservador"

        # Contenedor para la UI de progreso rotativo
        anim_placeholder = st.empty()
        simulate_loading_animation(anim_placeholder, sleep_time=0.3)

        try:
            # Extraer transcripción de YouTube si hay URL
            youtube_context = ""
            if youtube_url and youtube_url.strip():
                with st.spinner("🎬 Extrayendo transcripción de YouTube..."):
                    try:
                        yt_response = fetch_api(
                            "/stories/youtube-transcript",
                            method="POST",
                            json={"url": youtube_url.strip()},
                        )
                        youtube_context = yt_response.get("text", "")
                        yt_lang = yt_response.get("language", "")
                        st.success(f"✅ Transcripción extraída ({yt_lang}) — {len(youtube_context)} caracteres")
                    except Exception as yt_err:
                        st.warning(f"⚠️ No se pudo extraer la transcripción: {yt_err}")

            # Extraer contenido de URL de referencia si hay
            reference_context = ""
            if reference_url and reference_url.strip():
                with st.spinner("🔗 Extrayendo contenido de la página de referencia..."):
                    try:
                        ref_response = fetch_api(
                            "/stories/scrape-context",
                            method="POST",
                            json={"url": reference_url.strip()},
                        )
                        reference_context = ref_response.get("text", "")
                        ref_title = ref_response.get("title", "")
                        st.success(f"✅ Contexto extraído: \"{ref_title[:50]}\" — {ref_response.get('char_count', 0)} caracteres")
                    except Exception as ref_err:
                        st.warning(f"⚠️ No se pudo extraer el contexto: {ref_err}")

            # Combinar todas las fuentes de contexto externo
            context_parts: list[str] = []
            if youtube_context:
                context_parts.append(f"## Transcripción de Video YouTube\n\n{youtube_context}")
            if reference_context:
                context_parts.append(f"## Contenido de Referencia\n\n{reference_context}")
            if analytics_data:
                context_parts.append(f"## Datos Analíticos del Usuario\n\n{analytics_data}")

            combined_analytics = "\n\n---\n\n".join(context_parts) if context_parts else ""

            # Preparar archivos
            file_payload = []
            if uploaded_files:
                for f in uploaded_files:
                    file_payload.append(("files", (f.name, f.getvalue(), f.type)))

            if story_type == "redes sociales":
                # ── Generación Multi-Red ──
                with st.spinner(f"Generando contenido para {len(selected_networks)} redes..."):
                    response = fetch_api(
                        "/stories/generate-multi",
                        method="POST",
                        data={
                            "task": task,
                            "networks": ",".join(selected_networks),
                            "tone": tone,
                            "audience": audience,
                            "length": length,
                            "creativity": creativity_value,
                            "analytics_data": combined_analytics,
                        },
                        files=file_payload if file_payload else None,
                    )

                st.success(
                    f"¡Contenido generado para {len(response.get('results', []))} redes! "
                    f"({response.get('total_latency_ms', 0):.0f}ms total)"
                )

                # Mostrar resultados en tabs
                results = response.get("results", [])
                if results:
                    network_labels = {
                        "youtube": "🎬 YouTube",
                        "instagram": "📸 Instagram",
                        "facebook": "📘 Facebook",
                        "twitter": "🐦 X/Twitter",
                        "tiktok": "🎵 TikTok",
                        "linkedin": "💼 LinkedIn",
                    }
                    tab_names = [
                        network_labels.get(r["network"], r["network"].title())
                        for r in results
                    ]
                    tabs = st.tabs(tab_names)

                    for tab, result in zip(tabs, results, strict=False):
                        with tab:
                            if result.get("provider") == "error":
                                st.error(result.get("content", "Error desconocido"))
                            else:
                                st.markdown(
                                    f"<div class='as-result-meta'>Generado con "
                                    f"<strong>{result.get('provider', '').upper()}</strong> "
                                    f"en {result.get('latency_ms', 0):.0f}ms "
                                    f"· ID: <code>{result.get('story_id', '')}</code></div>",
                                    unsafe_allow_html=True,
                                )
                                st.code(result.get("content", ""), language="markdown")
                                st.download_button(
                                    f"⬇️ Descargar {result['network'].title()}",
                                    data=result.get("content", ""),
                                    file_name=f"{result['network']}_{task[:20].replace(' ', '_')}.md",
                                    mime="text/markdown",
                                    key=f"dl_{result['network']}",
                                )

            else:
                # ── Generación Simple ──
                with st.spinner("Enviando a la IA Multimodal..."):
                    response = fetch_api(
                        "/stories/generate",
                        method="POST",
                        data={
                            "task": task,
                            "story_type": story_type,
                            "tone": tone,
                            "audience": audience,
                            "length": length,
                            "creativity": creativity_value,
                            "analytics_data": combined_analytics,
                        },
                        files=file_payload if file_payload else None,
                    )

                # ── Modo Async: si recibimos job_id, hacer polling ──
                if response.get("job_id"):
                    import time as _time

                    job_id = response["job_id"]
                    progress_placeholder = st.empty()
                    progress_placeholder.info("⏳ Generación en background — esperando progreso...")

                    max_polls = 120  # 120 * 3s = 6 minutos máximo
                    for _poll in range(max_polls):
                        _time.sleep(3)
                        try:
                            job_status = fetch_api(f"/stories/jobs/{job_id}", method="GET")
                        except Exception:
                            continue

                        status_val = job_status.get("status", "")
                        progress_msg = job_status.get("progress", "Procesando...")

                        if status_val == "completed":
                            progress_placeholder.empty()
                            result_data = job_status.get("result", {})
                            response = result_data  # Usar el resultado del job
                            st.success("¡Contenido generado exitosamente!")
                            break
                        elif status_val == "failed":
                            progress_placeholder.empty()
                            error_msg = job_status.get("result", {}).get("error", "Error desconocido")
                            st.error(f"Error en la generación: {error_msg}")
                            response = None
                            break
                        else:
                            progress_placeholder.info(f"⏳ {progress_msg}")
                    else:
                        progress_placeholder.empty()
                        st.warning("La generación está tomando más tiempo del esperado. Revisá 'Mis Historias' en unos minutos.")
                        response = None

                else:
                    # ── Modo Sync (sin Redis) ──
                    st.success("¡Contenido generado exitosamente!")

                if response:
                    provider = response.get("provider", "")
                    ms = response.get("latency_ms", 0)

                    st.markdown(f"""
                    <div class="as-result-box">
                        <div class="as-result-title">{response.get('title', 'Historia generada')}</div>
                        <div class="as-result-meta">
                            Generado con <strong>{provider.upper()}</strong> en {ms:.0f}ms
                            · ID: <code>{response.get('story_id', '')}</code>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.code(response.get("content", ""), language="markdown")

                # Botones de exportación
                exp_col1, exp_col2, exp_col3 = st.columns(3)
                with exp_col1:
                    st.download_button(
                        "⬇️ Markdown",
                        data=response.get("content", ""),
                        file_name=f"{story_type}_{task[:20].replace(' ', '_')}.md",
                        mime="text/markdown",
                        key="dl_md_single",
                    )
                with exp_col2:
                    story_id = response.get("story_id", "")
                    if story_id and st.button("📄 Descargar PDF", key="dl_pdf_gen"):
                        try:
                            import os

                            import httpx
                            token = st.session_state.get("token", "")
                            api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
                            with httpx.Client(timeout=30.0) as http_client:
                                resp = http_client.get(
                                    f"{api_url}/stories/{story_id}/export/pdf",
                                    headers={"Authorization": f"Bearer {token}"},
                                )
                                if resp.status_code == 200:
                                    st.download_button(
                                        "⬇️ Guardar PDF",
                                        data=resp.content,
                                        file_name=f"historia_{story_id[:8]}.pdf",
                                        mime="application/pdf",
                                        key="dl_pdf_gen_save",
                                    )
                                else:
                                    st.error("Error al generar PDF")
                        except Exception as pdf_err:
                            st.error(f"Error: {pdf_err}")
                with exp_col3:
                    if story_id and st.button("🔗 Publicar Link", key="share_gen"):
                        try:
                            share_result = fetch_api(
                                f"/stories/{story_id}/share",
                                method="POST",
                            )
                            st.success("¡Historia publicada!")
                            st.code(share_result.get("share_url", ""), language=None)
                        except Exception as share_err:
                            st.error(f"Error: {share_err}")

            st.balloons()

        except Exception as e:
            st.error(f"Hubo un error al generar la historia.\n\nDetalle técnico: {e}")
