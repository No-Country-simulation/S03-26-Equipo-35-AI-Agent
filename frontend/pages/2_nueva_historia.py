"""Página de creación de nueva historia."""
import streamlit as st
from api_client import fetch_api
from components.loading_states import simulate_loading_animation
from components.styles import inject_global_styles, render_page_header

st.set_page_config(page_title="Nueva Historia", page_icon="✍️", layout="wide")
inject_global_styles()

if "token" not in st.session_state:
    st.switch_page("app.py")

render_page_header(
    "Nueva <em>Historia</em>",
    "Describí lo que necesitás — la IA aplicará la voz y contexto de tu marca."
)

col1, col2 = st.columns([2, 1])

with col1, st.form("generate_form"):
        story_type = st.selectbox(
            "Tipo de Contenido",
            options=["blog", "social", "internal", "press", "email"],
            format_func=lambda x: x.title()
        )

        task = st.text_area(
            "Instrucciones de la tarea (Prompt)",
            placeholder="Ej: Escribe un post de LinkedIn anunciando el lanzamiento de nuestra nueva plataforma...",
            height=150
        )

        brand_tone = st.selectbox(
            "Tono de Marca Deseado",
            options=["profesional", "innovador", "cercano", "formal", "persuasivo"]
        )

        st.markdown("<p style='font-size: 14px; font-weight: 500; margin-bottom: 5px;'>Contexto Multimedia (Opcional)</p>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Sube imágenes o documentos para que la IA los analice (ej. gráficos, infografías).",
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg", "pdf"]
        )

        submit = st.form_submit_button("Generar Borrador ✨", type="primary")

with col2:
    st.markdown("""<div class="as-info-box">
        <strong>Tip:</strong> Cuanto más detallada sea la instrucción,
        mejor resultado. Si subes gráficos o fotos, el modelo actuará como 
        <em>Director de Arte</em>, leyendo las fotos y sugiriendo dónde insertarlas 
        en la historia resultante.
    </div>""", unsafe_allow_html=True)

if submit:
    if not task:
        st.error("Debes proveer las instrucciones de la tarea.")
    else:
        # Contenedor para la UI de progreso rotativo
        anim_placeholder = st.empty()
        simulate_loading_animation(anim_placeholder, sleep_time=0.3)

        try:
            with st.spinner("Llamando a la IA Multimodal..."):
                file_payload = []
                if uploaded_files:
                    for f in uploaded_files:
                        file_payload.append(("files", (f.name, f.getvalue(), f.type)))

                response = fetch_api(
                    "/stories/generate",
                    method="POST",
                    data={
                        "task": task,
                        "story_type": story_type,
                        "brand_tone": brand_tone,
                    },
                    files=file_payload if file_payload else None
                )

            st.success("¡Contenido generado exitosamente!")

            provider = response.get("provider", "")
            ms = response.get("latency_ms", 0)
            creds = response.get("credits_used", 1)

            st.markdown(f"""
            <div class="as-result-box">
                <div class="as-result-title">{response.get('title', 'Historia generada')}</div>
                <div style="font-size: 14px; line-height: 1.8;">{response.get('content', '')}</div>
                <div class="as-result-meta">
                    Generado con <strong>{provider.upper()}</strong> en {ms:.0f}ms
                    · ID: <code>{response.get('story_id', '')}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.balloons()

        except Exception as e:
            st.error(f"Hubo un error al generar la historia.\n\nDetalle técnico: {e}")
