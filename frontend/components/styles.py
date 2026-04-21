"""Estilos globales compartidos — AutoStory Builder.

Importar en cada página con:
    from components.styles import inject_global_styles
    inject_global_styles()
"""

import streamlit as st


def inject_global_styles() -> None:
    """Inyecta el CSS global y tipografías en cualquier página de Streamlit."""
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }

        /* Logo */
        .as-logo {
            font-family: 'DM Serif Display', serif;
            font-size: 20px;
            margin: 0 0 4px;
            color: inherit;
        }
        .as-logo span { color: #BA7517; }

        /* Títulos de página */
        .as-page-title {
            font-family: 'DM Serif Display', serif;
            font-size: 26px;
            font-weight: 400;
            margin: 0 0 4px;
            color: inherit;
        }
        .as-page-title em { color: #BA7517; font-style: italic; }

        .as-page-subtitle {
            font-size: 14px;
            color: #888;
            margin: 0 0 24px;
        }

        /* Greeting dashboard */
        .as-greeting {
            font-family: 'DM Serif Display', serif;
            font-size: 28px;
            font-weight: 400;
            margin-bottom: 4px;
        }
        .as-greeting em { color: #BA7517; font-style: italic; }

        /* Avatar */
        .as-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #FAEEDA;
            color: #BA7517;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 500;
            float: right;
        }

        /* Créditos */
        .as-credits {
            display: inline-flex;
            align-items: baseline;
            gap: 8px;
            background: #FAEEDA;
            border-radius: 8px;
            padding: 10px 16px;
            margin: 12px 0 20px;
        }
        .as-credits-num { font-size: 24px; font-weight: 500; color: #BA7517; }
        .as-credits-label { font-size: 13px; color: #854F0B; }

        /* Tarjetas de Navegación & Botones Destacados (Primary) */
        div[data-testid="stButton"] > button[kind="primary"] {
            text-align: left !important;
            padding: 16px !important;
            height: auto !important;
            border-radius: 10px !important;
            border: 1px solid rgba(186, 117, 23, 0.4) !important;
            background-color: #FAEEDA !important;
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s !important;
            display: flex !important;
            justify-content: flex-start !important;
            color: #633806 !important;
            width: 100% !important;
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            border-color: #BA7517 !important;
            background-color: #fbdfb3 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
            color: #633806 !important;
        }
        div[data-testid="stButton"] > button[kind="primary"] p {
            white-space: pre-wrap !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            line-height: 1.5 !important;
            margin: 0 !important;
            color: #854F0B !important;
        }
        div[data-testid="stButton"] > button[kind="primary"] p::first-line {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #633806 !important;
        }

        /* Historias recientes */
        .as-section-label {
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: #888;
            margin: 16px 0 8px;
        }
        .as-story-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 9px 0;
            border-bottom: 0.5px solid rgba(0,0,0,0.08);
        }
        .as-story-title { font-size: 13px; }
        .as-story-meta { font-size: 11px; color: #999; margin-top: 2px; }

        /* Badges de estado */
        .as-badge {
            font-size: 11px;
            font-weight: 500;
            padding: 3px 10px;
            border-radius: 99px;
            white-space: nowrap;
        }

        /* Info box */
        .as-info-box {
            background: #FAEEDA;
            border-left: 3px solid #BA7517;
            border-radius: 0 8px 8px 0;
            padding: 12px 16px;
            margin: 12px 0;
            font-size: 13px;
            color: #633806;
        }

        /* Warning box */
        .as-warning-box {
            background: #FEF9EC;
            border-left: 3px solid #EF9F27;
            border-radius: 0 8px 8px 0;
            padding: 12px 16px;
            margin: 12px 0;
            font-size: 13px;
            color: #633806;
        }

        /* Métricas de crédito en sidebar */
        .as-sidebar-credits {
            background: #FAEEDA;
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            text-align: center;
        }
        .as-sidebar-credits-num { font-size: 28px; font-weight: 500; color: #BA7517; }
        .as-sidebar-credits-label { font-size: 12px; color: #854F0B; }

        /* Botón primario (submit de forms) */
        div[data-testid="stFormSubmitButton"] button {
            background-color: #BA7517;
            color: white;
            border: none;
            width: 100%;
            font-family: 'DM Sans', sans-serif;
            font-weight: 500;
        }
        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #854F0B;
            color: white;
            border: none;
        }

        /* Contenedor de resultado generado */
        .as-result-box {
            border: 1px solid #BA7517;
            border-radius: 10px;
            padding: 20px;
            margin-top: 16px;
            background: rgba(186, 117, 23, 0.03);
        }
        .as-result-title {
            font-family: 'DM Serif Display', serif;
            font-size: 20px;
            color: inherit;
            margin-bottom: 12px;
        }
        .as-result-meta {
            font-size: 12px;
            color: #999;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 0.5px solid rgba(0,0,0,0.08);
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Perfil persistente en Barra Lateral ──
    if "token" in st.session_state and "user" in st.session_state:
        # Extraemos variables o dejamos defaults simples para no crashear
        user_email = st.session_state["user"].get("email", "Usuario Desconocido")

        st.sidebar.markdown("### Perfil de Usuario")
        st.sidebar.markdown(f"**Usuario:** {user_email}")
        st.sidebar.markdown("**Rol:** Admin (MVP Default)")
        st.sidebar.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        if st.sidebar.button("Cerrar sesión", type="secondary", use_container_width=True, key="btn_logout_global"):
            st.session_state.clear()
            st.rerun()


# Helpers visuales reutilizables

STATUS_LABELS: dict[str, tuple[str, str, str]] = {
    "borrador":    ("Borrador",    "#888780", "#F1EFE8"),
    "en_revision": ("En revisión", "#854F0B", "#FAEEDA"),
    "aprobado":    ("Aprobado",    "#185FA5", "#E6F1FB"),
    "rechazado":   ("Rechazado",   "#A32D2D", "#FCEBEB"),
    "publicado":   ("Publicado",   "#3B6D11", "#EAF3DE"),
}


def render_status_badge(status: str) -> str:
    """Retorna HTML de un badge de estado listo para st.markdown."""
    label, color, bg = STATUS_LABELS.get(status, ("—", "#888", "#eee"))
    return (
        f'<span class="as-badge" style="color:{color}; background:{bg};">'
        f'{label}</span>'
    )


def render_page_header(title: str, subtitle: str = "") -> None:
    """Renderiza el header estándar de página interna con logo y título."""
    st.markdown('<p class="as-logo">Auto<span>Story</span> Builder</p>',
                unsafe_allow_html=True)
    st.markdown(f'<h1 class="as-page-title">{title}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="as-page-subtitle">{subtitle}</p>',
                    unsafe_allow_html=True)
