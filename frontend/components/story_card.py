"""Componentes UI compartidos para tarjetas y badges de historias."""

import streamlit as st
from components.styles import render_status_badge


def render_story_card(story: dict) -> None:
    """Renderiza una tarjeta visual para una historia en listados.

    Args:
        story: Diccionario con los datos de la historia (desde la API).
    """
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
