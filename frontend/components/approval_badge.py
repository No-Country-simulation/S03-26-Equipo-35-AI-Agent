"""Componente: Badge de estado de aprobación.

Muestra un badge visual con el estado de aprobación de una historia.
Cada estado tiene un color y emoji distintivo.
"""

import streamlit as st

# Configuración visual por estado
STATUS_CONFIG: dict[str, dict[str, str]] = {
    "borrador": {"emoji": "📝", "color": "gray", "label": "Borrador"},
    "en_revision": {"emoji": "👀", "color": "blue", "label": "En Revisión"},
    "aprobado": {"emoji": "✅", "color": "green", "label": "Aprobado"},
    "rechazado": {"emoji": "❌", "color": "red", "label": "Rechazado"},
    "publicado": {"emoji": "🚀", "color": "violet", "label": "Publicado"},
}


def render_approval_badge(status: str) -> None:
    """Renderiza un badge visual con el estado de aprobación.

    Args:
        status: Estado de la historia ('borrador', 'en_revision',
                'aprobado', 'rechazado', 'publicado').
    """
    config = STATUS_CONFIG.get(status, STATUS_CONFIG["borrador"])

    st.markdown(
        f":{config['color']}[{config['emoji']} {config['label']}]"
    )
