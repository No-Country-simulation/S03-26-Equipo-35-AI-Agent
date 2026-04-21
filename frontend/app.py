"""Entry point de la aplicación Streamlit.

Maneja el inicio de sesión y muestra un dashboard básico en el home con diseño UI refinado.
"""

import streamlit as st
from api_client import fetch_api, login_with_supabase
from components.styles import inject_global_styles, render_status_badge

st.set_page_config(
    page_title="AutoStory Builder",
    page_icon="🚀",
    layout="wide",
)


inject_global_styles()


def show_login():
    """Muestra el formulario de inicio de sesión."""
    st.markdown("""
        <style>
            /* Ocultar el Sidebar (navegación de páginas) hasta estar logueado */
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="collapsedControl"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="as-logo" style="margin-bottom: 5px;">Auto<span>Story</span> Builder</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #666; font-size: 15px;">Narrativas que suenan a tu empresa</p>', unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")

        if submit:
            if not email or not password:
                st.error("Por favor ingresa correo y contraseña.")
                return

            try:
                with st.spinner("Autenticando..."):
                    session_data = login_with_supabase(email, password)
                    st.session_state["token"] = session_data["access_token"]
                    st.session_state["user"] = session_data["user"]

                    st.success("¡Sesión iniciada correctamente!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error de autenticación: {e}")


def show_dashboard():
    """Muestra el dashboard tras el login."""
    # Header con logo y org
    col_logo, col_org = st.columns([3, 1])
    with col_logo:
        st.markdown('<p class="as-logo">Auto<span>Story</span> Builder</p>', unsafe_allow_html=True)
    with col_org:
        user_email = st.session_state.get("user", {}).get("email", "")
        initials = user_email[:2].upper() if user_email else "US"
        st.markdown(f'<div class="as-avatar">{initials}</div>', unsafe_allow_html=True)

    # Saludo editorial
    st.markdown('<h1 class="as-greeting">¿Qué historia <em>contamos hoy?</em></h1>',
                unsafe_allow_html=True)

    # Cards de navegación — 2x2 grid usando Botones Nativos de Streamlit
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✦ Nueva historia \n\nGenera contenido desde tus materiales", use_container_width=True, type="primary", key="btn_nueva_historia"):
            st.switch_page("pages/2_nueva_historia.py")

        if st.button("◎ Aprobaciones \n\nRevisá el contenido pendiente", use_container_width=True, type="primary"):
            st.switch_page("pages/4_centro_de_aprobaciones.py")

    with col2:
        if st.button("◈ Base de marca \n\nSincroniza el contexto RAG de tu empresa", use_container_width=True, type="primary"):
            st.switch_page("pages/1_base_de_marca.py")

        if st.button("≡ Mis historias \n\nHistorial y versiones anteriores", use_container_width=True, type="primary"):
            st.switch_page("pages/3_mis_historias.py")

    # Historias recientes
    st.markdown('<p class="as-section-label">Recientes</p>', unsafe_allow_html=True)

    try:
        real_stories = fetch_api("/stories/", method="GET", params={"limit": 3})
        if real_stories:
            recent_stories = [
                {
                    "title": s.get("title", "Sin título"),
                    "meta": s.get("created_at", "")[:10] + " · " + s.get("story_type", "general"),
                    "status": s.get("status", "borrador"),
                }
                for s in real_stories
            ]
        else:
            recent_stories = []
    except Exception:
        recent_stories = []

    if not recent_stories:
        st.info("No tienes historias generadas aún. ¡Ve a 'Nueva historia' para empezar!")
    else:
        for story in recent_stories:
            badge_html = render_status_badge(story["status"])
            st.markdown(f"""
            <div class="as-story-row">
                <div>
                    <div class="as-story-title">{story['title']}</div>
                    <div class="as-story-meta">{story['meta']}</div>
                </div>
                {badge_html}
            </div>
            """, unsafe_allow_html=True)


def main_page():
    if "token" not in st.session_state:
        show_login()
    else:
        show_dashboard()

p_inicio = st.Page(main_page, title="Inicio", default=True)
p_marca = st.Page("pages/1_base_de_marca.py", title="Base de marca")
p_historia = st.Page("pages/2_nueva_historia.py", title="Nueva historia")
p_mis = st.Page("pages/3_mis_historias.py", title="Mis historias")
p_aprob = st.Page("pages/4_centro_de_aprobaciones.py", title="Centro de aprobaciones")
p_ident = st.Page("pages/5_identidad_y_configuración.py", title="Identidad")

pg = st.navigation([p_inicio, p_marca, p_historia, p_mis, p_aprob, p_ident])
pg.run()
