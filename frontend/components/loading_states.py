"""Componente: Loading states paso a paso.

Muestra mensajes rotativos durante la generación de contenido
para mejorar la percepción de velocidad (perceived performance).

Mensajes:
  "Consultando tu base de marca..."
  "Construyendo la narrativa..."
  "Puliendo el tono..."
"""

import math
import time

import streamlit as st

# Mensajes de progreso por paso
LOADING_MESSAGES: list[str] = [
    "🔍 Consultando tu base de marca...",
    "📝 Construyendo la narrativa...",
    "✨ Puliendo el tono...",
    "🎯 Verificando coherencia...",
    "🚀 Generando versión final..."
]

class GenerationLoadingState:
    """Context manager para animar mensajes rotativos durante un proceso largo.

    Dado que Streamlit es síncrono y bloquea en httpx.post, no podemos tener
    un thread paralelo actualizando el UI fácilmente sin st.experimental_rerun
    loop infinitos o hooks raros.
    Para MVP local: mostraremos un spinner general con un mensaje dinámico simulado
    usando contenedores asíncronos o el spinner de st por defecto.
    Al final usaremos balloons.
    """
    def __init__(self, message="Generando contenido con IA..."):
        self.message = message
        self.placeholder = None

    def __enter__(self):
        self.placeholder = st.empty()
        self.placeholder.info(f"⏳ {self.message}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.placeholder:
            self.placeholder.empty()

# Alternativa: Función síncrona que simule un delay iterativo antes de la request (mock animation)
def simulate_loading_animation(placeholder, sleep_time=0.4):
    """Simula una carga iterando mensajes.
    En una app real, esto correría en JS/React, o con Generator yield.
    Aquí lo hacemos síncrono antes del call real para efecto UX.
    """
    progress_bar = placeholder.progress(0.0)
    status_text = st.empty()

    steps = len(LOADING_MESSAGES)
    for i, msg in enumerate(LOADING_MESSAGES):
        status_text.info(msg)
        progress_bar.progress(math.ceil(100 / steps) * (i + 1))
        time.sleep(sleep_time)

    status_text.empty()
    progress_bar.empty()
