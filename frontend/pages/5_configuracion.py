"""Página de configuración de la cuenta y créditos."""
import streamlit as st
from api_client import fetch_api
from components.styles import inject_global_styles, render_page_header

st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
inject_global_styles()

if "token" not in st.session_state:
    st.switch_page("app.py")

user_email = st.session_state.get("user", {}).get("email", "Usuario Desconocido")

render_page_header(
    "<em>Configuración</em>",
)

st.markdown("### Perfil de Usuario")
st.text_input("Correo Electrónico", value=user_email, disabled=True)
st.text_input("Rol en la Organización", value="Admin (MVP Default)", disabled=True)

