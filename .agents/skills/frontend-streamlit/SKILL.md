---
name: Frontend Streamlit
description: Desarrollo de páginas y componentes Streamlit
---

# Skill: Frontend Streamlit

## Contexto
Frontend de AutoStory Builder — solo Streamlit + Python.

## Archivos del dominio
```
frontend/pages/
frontend/components/
```

## Reglas críticas
1. SOLO Streamlit + Python. Sin JavaScript, sin HTML custom, sin React
2. Toda comunicación con datos: httpx a FastAPI — nunca directo a Supabase
3. `st.session_state` para estado de sesión
4. Un componente por archivo en `frontend/components/`
5. Sin lógica de negocio en el frontend

## UX Guidelines
- Loading states por pasos con mensajes rotativos:
  "Consultando tu base de marca..." → "Construyendo la narrativa..." → "Puliendo el tono..."
- Story reveal animado al recibir contenido generado
- Mensajes de error claros y accionables
- Labels descriptivos en todos los inputs
- Credit counter visible en sidebar

## Patrón de página
```python
import streamlit as st
import httpx

st.set_page_config(page_title="...", page_icon="...", layout="wide")

# 1. Verificar sesión
if "token" not in st.session_state:
    st.warning("Inicia sesión para continuar")
    st.stop()

# 2. Render UI
st.title("...")

# 3. Interacción con API
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/endpoint",
            headers={"Authorization": f"Bearer {st.session_state.token}"})
        return response.json()
```
