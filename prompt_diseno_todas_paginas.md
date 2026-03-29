# Prompt: Diseño editorial consistente en todas las páginas

Pegar este prompt en Antigravity.

---

## PROMPT

Eres el Frontend Agent de AutoStory Builder.

Antes de empezar:
1. Lee `GEMINI.md` en `.gemini/GEMINI.md`
2. Lee `.agents/skills/frontend-streamlit/SKILL.md`
3. Lee los archivos actuales de cada página que vas a modificar

**Activa Planning Phase. Presentame los cambios archivo por archivo y esperá aprobación.**

---

## OBJETIVO

Aplicar el sistema de diseño editorial de AutoStory a todas las páginas del frontend.
El diseño ya existe en `frontend/app.py` — hay que extraerlo a un archivo compartido
y aplicarlo consistentemente en las 5 páginas restantes.

**Regla principal:** mantener toda la lógica existente intacta.
Solo cambia la presentación visual — nunca la lógica de negocio.

---

## TAREA 1 — Crear `frontend/components/styles.py`

Extraer `inject_global_styles()` de `app.py` a un archivo compartido.
Agregar estilos adicionales para los elementos que aparecen en las páginas internas.

```python
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

        /* Cards de navegación */
        .as-card {
            border: 0.5px solid rgba(0,0,0,0.12);
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 10px;
            background: rgba(0,0,0,0.02);
        }
        .as-card-primary { border-color: #BA7517; background: #FAEEDA; }
        .as-card-icon { font-size: 16px; margin-bottom: 6px; }
        .as-card-title { font-size: 14px; font-weight: 500; margin-bottom: 3px; }
        .as-card-primary .as-card-title { color: #633806; }
        .as-card-desc { font-size: 12px; color: #888; line-height: 1.5; }
        .as-card-primary .as-card-desc { color: #854F0B; }

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
```

---

## TAREA 2 — Actualizar `app.py`

Reemplazar la función `inject_global_styles()` definida localmente por el import:

```python
from components.styles import inject_global_styles
```

Eliminar la definición local de `inject_global_styles()` del archivo —
ya no es necesaria, viene del módulo compartido.

El resto de `app.py` no cambia.

---

## TAREA 3 — `pages/1_onboarding.py`

Agregar al inicio (después de `st.set_page_config`):

```python
from components.styles import inject_global_styles, render_page_header
inject_global_styles()
```

Reemplazar:
```python
st.title("🌐 Base de Marca (Onboarding)")
st.write("Sincroniza sitios web y materiales para que la IA entienda el tono de tu marca.")
```

Por:
```python
render_page_header(
    "Base de <em>Marca</em>",
    "Sincroniza tu sitio web para que la IA aprenda el tono y contexto de tu empresa."
)
```

Reemplazar el `st.info(...)` dentro del form por:
```python
st.markdown("""<div class="as-info-box">
    Ingresá una URL con HTTPS. El sistema extraerá el contenido y lo convertirá
    en contexto de marca para la generación de historias.
</div>""", unsafe_allow_html=True)
```

El resto de la lógica (form, fetch_api, balloons) no cambia.

---

## TAREA 4 — `pages/2_nueva_historia.py`

Agregar al inicio:
```python
from components.styles import inject_global_styles, render_page_header
inject_global_styles()
```

Reemplazar:
```python
st.title("✍️ Nueva Historia")
st.write("Dime qué necesitas, y lo redactaré utilizando la voz y contexto de tu marca.")
```

Por:
```python
render_page_header(
    "Nueva <em>Historia</em>",
    "Describí lo que necesitás — la IA aplicará la voz y contexto de tu marca."
)
```

Reemplazar el bloque de resultado (el `with st.container(border=True):`) por:

```python
provider = response.get("provider", "")
ms = response.get("latency_ms", 0)
creds = response.get("credits_used", 1)

st.markdown(f"""
<div class="as-result-box">
    <div class="as-result-title">{response.get('title', 'Historia generada')}</div>
    <div style="font-size: 14px; line-height: 1.8;">{response.get('content', '')}</div>
    <div class="as-result-meta">
        Generado con <strong>{provider.upper()}</strong> en {ms:.0f}ms
        · {creds} crédito{'s' if creds != 1 else ''} usado{'s' if creds != 1 else ''}
        · ID: <code>{response.get('story_id', '')}</code>
    </div>
</div>
""", unsafe_allow_html=True)
```

Reemplazar el `st.info("💡 **Tip de generación:**")` del col2 por:
```python
st.markdown("""<div class="as-info-box">
    <strong>Tip:</strong> Cuanto más detallada sea la instrucción,
    mejor resultado. La IA aplicará automáticamente los valores
    de tu Base de Marca.
</div>""", unsafe_allow_html=True)
```

El resto de la lógica no cambia.

---

## TAREA 5 — `pages/3_mis_historias.py`

Agregar al inicio:
```python
from components.styles import inject_global_styles, render_page_header, render_status_badge
inject_global_styles()
```

Reemplazar:
```python
st.title("📚 Mis Historias")
st.write("Visualiza el historial de contenidos generados por la IA para tu marca.")
```

Por:
```python
render_page_header(
    "Mis <em>Historias</em>",
    "Historial de contenidos generados con la voz de tu marca."
)
```

El estado vacío (`st.info("Aún no has generado ninguna historia.")`) reemplazarlo por:
```python
st.markdown("""
<div style="padding: 40px 0; text-align: center; color: #999;">
    <div style="font-size: 32px; margin-bottom: 12px;">✦</div>
    <div style="font-size: 14px;">Aún no generaste ninguna historia.</div>
    <div style="font-size: 12px; margin-top: 6px; color: #bbb;">
        Empezá desde Nueva Historia.
    </div>
</div>
""", unsafe_allow_html=True)
```

El resto de la lógica no cambia.

---

## TAREA 6 — `pages/4_aprobaciones.py`

Agregar al inicio:
```python
from components.styles import inject_global_styles, render_page_header, render_status_badge
inject_global_styles()
```

Reemplazar:
```python
st.title("✅ Centro de Aprobaciones")
st.write("Valida, aprueba o rechaza el contenido en revisión.")
st.warning("🚧 La lógica de estado conectada a los endpoints de workflow es parte de la **Semana 5**.")
```

Por:
```python
render_page_header(
    "Centro de <em>Aprobaciones</em>",
    "Revisá, aprobá o rechazá el contenido antes de publicarlo."
)
st.markdown("""<div class="as-warning-box">
    La conexión con los endpoints de aprobación se completa en Semana 5.
    Por ahora podés ver el contenido pendiente.
</div>""", unsafe_allow_html=True)
```

El estado vacío (`st.info("No hay historias pendientes...")`) reemplazarlo por:
```python
st.markdown("""
<div style="padding: 40px 0; text-align: center; color: #999;">
    <div style="font-size: 32px; margin-bottom: 12px;">◎</div>
    <div style="font-size: 14px;">No hay historias pendientes de aprobación.</div>
</div>
""", unsafe_allow_html=True)
```

El resto de la lógica no cambia.

---

## TAREA 7 — `pages/5_configuracion.py`

Agregar al inicio:
```python
from components.styles import inject_global_styles, render_page_header
inject_global_styles()
```

Reemplazar:
```python
st.title("⚙️ Configuración")
st.write("Gestiona la información de tu organización.")
```

Por:
```python
render_page_header(
    "<em>Configuración</em>",
    "Gestioná los créditos y la información de tu organización."
)
```

Reemplazar el bloque `render_credit_counter(balance=50)` por:
```python
credits = st.session_state.get("credits", 50)
st.markdown(f"""
<div class="as-credits">
    <span class="as-credits-num">{credits}</span>
    <span class="as-credits-label">créditos disponibles</span>
</div>
""", unsafe_allow_html=True)
```

El resto de la lógica no cambia.

---

## TAREA 8 — `components/story_card.py`

Actualizar `render_story_card()` para usar los estilos del sistema:

```python
from components.styles import render_status_badge

def render_story_card(story: dict) -> None:
    """Renderiza una tarjeta visual para una historia en listados."""
    preview = story.get("content", "")
    if len(preview) > 150:
        preview = preview[:150] + "..."

    credits = story.get("credits_used", 0)
    provider = story.get("llm_provider", "—")
    status = story.get("status", "borrador")
    badge_html = render_status_badge(status)

    st.markdown(f"""
    <div class="as-story-row" style="align-items: flex-start; padding: 14px 0;">
        <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <div class="as-story-title" style="font-size: 14px; font-weight: 500;">
                    {story.get('title', 'Sin Título')}
                </div>
                {badge_html}
            </div>
            <div class="as-story-meta">
                {story.get('story_type', '').title()}
                · {story.get('created_at', '')[:10]}
                · 🪙 {credits} crédito{'s' if credits != 1 else ''}
                · {provider}
            </div>
            <div style="font-size: 13px; color: #666; margin-top: 6px; line-height: 1.6;">
                {preview}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<hr style="border: none; border-top: 0.5px solid rgba(0,0,0,0.07); margin: 0;">', unsafe_allow_html=True)
```

---

## Verificación al finalizar:

```bash
streamlit run frontend/app.py
```

Navegar manualmente a cada página y confirmar:
- [ ] Todas las páginas tienen la misma tipografía DM Serif / DM Sans
- [ ] Todos los títulos de página usan `render_page_header()`
- [ ] El acento ámbar `#BA7517` aparece consistentemente en todos los formularios
- [ ] Los estados vacíos muestran el mensaje visual (no `st.info` genérico)
- [ ] Sin errores de import en ninguna página
- [ ] `ruff check frontend/` pasa limpio

**Un solo cambio en `components/styles.py` debe verse reflejado en todas las páginas.**
