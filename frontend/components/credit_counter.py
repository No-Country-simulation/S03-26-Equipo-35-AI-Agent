"""Componente: Credit Counter en Sidebar."""

import streamlit as st


def render_credit_counter(balance: int) -> None:
    """Renderiza el balance de créditos en la barra lateral.

    Destaca en rojo si el balance es 0, naranja si es bajo (<5).
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🪙 Mi Billetera")

    if balance > 5:
        color = "normal"
    elif balance > 0:
        color = "off"
    else:
        color = "error"

    st.sidebar.metric(
        label="Créditos Disponibles",
        value=balance,
        delta=None,
        delta_color=color
    )

    if balance <= 0:
        st.sidebar.error("Créditos agotados. Recarga para continuar generando.")
    elif balance <= 5:
        st.sidebar.warning("Créditos bajos.")
