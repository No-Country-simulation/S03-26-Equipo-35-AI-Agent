"""Renderizador HTML para publicación web de historias.

Convierte el contenido Markdown de una historia en una página HTML
completa, responsive, con tipografía profesional y branding mínimo.
Se usa para el endpoint público GET /public/{share_token}.
"""

import markdown as md
import structlog

logger = structlog.get_logger()


def render_story_html(
    title: str,
    content: str,
    story_type: str = "blog",
    created_at: str = "",
) -> str:
    """Genera una página HTML completa para una historia publicada.

    Args:
        title: Título de la historia.
        content: Contenido en formato markdown.
        story_type: Tipo de contenido (para metadata visual).
        created_at: Fecha de creación.

    Returns:
        String HTML completo listo para servir como response.
    """
    # Convertir Markdown → HTML
    content_html = md.markdown(
        content,
        extensions=["extra", "nl2br", "sane_lists"],
    )

    date_str = created_at[:10] if created_at else ""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — AutoStory Builder</title>
    <meta name="description" content="{title} — Generado con AutoStory Builder">
    <meta property="og:title" content="{title}">
    <meta property="og:type" content="article">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #FAFAF8;
            color: #333;
            line-height: 1.7;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 720px;
            margin: 0 auto;
            padding: 60px 24px 80px;
        }}

        /* Header */
        .header {{
            margin-bottom: 40px;
            padding-bottom: 24px;
            border-bottom: 2px solid #BA7517;
        }}

        .brand {{
            font-family: 'DM Serif Display', serif;
            font-size: 14px;
            color: #BA7517;
            margin-bottom: 20px;
            letter-spacing: 0.02em;
        }}

        .brand span {{
            color: #333;
        }}

        .story-type {{
            display: inline-block;
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #BA7517;
            background: #FAEEDA;
            padding: 4px 12px;
            border-radius: 99px;
            margin-bottom: 16px;
        }}

        h1 {{
            font-family: 'DM Serif Display', serif;
            font-size: 36px;
            font-weight: 400;
            color: #1a1a1a;
            line-height: 1.3;
            margin-bottom: 12px;
        }}

        .date {{
            font-size: 13px;
            color: #999;
        }}

        /* Content */
        .content {{
            font-size: 16px;
            color: #444;
        }}

        .content h1,
        .content h2,
        .content h3 {{
            font-family: 'DM Serif Display', serif;
            color: #1a1a1a;
            margin-top: 32px;
            margin-bottom: 12px;
        }}

        .content h2 {{ font-size: 24px; }}
        .content h3 {{ font-size: 20px; }}

        .content p {{
            margin-bottom: 16px;
        }}

        .content ul,
        .content ol {{
            margin-bottom: 16px;
            padding-left: 24px;
        }}

        .content li {{
            margin-bottom: 6px;
        }}

        .content strong {{
            color: #1a1a1a;
            font-weight: 500;
        }}

        .content blockquote {{
            border-left: 3px solid #BA7517;
            padding: 12px 20px;
            margin: 20px 0;
            background: #FAEEDA;
            border-radius: 0 8px 8px 0;
            font-style: italic;
            color: #633806;
        }}

        .content code {{
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 14px;
        }}

        .content pre {{
            background: #1a1a2e;
            color: #e0e0e0;
            padding: 16px 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 16px 0;
            font-size: 14px;
        }}

        /* Footer */
        .footer {{
            margin-top: 60px;
            padding-top: 24px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            font-size: 12px;
            color: #aaa;
        }}

        .footer a {{
            color: #BA7517;
            text-decoration: none;
        }}

        /* Responsive */
        @media (max-width: 600px) {{
            .container {{
                padding: 32px 16px 60px;
            }}
            h1 {{
                font-size: 28px;
            }}
            .content {{
                font-size: 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand"><span>Auto</span>Story Builder</div>
            <div class="story-type">{story_type}</div>
            <h1>{title}</h1>
            <div class="date">{date_str}</div>
        </div>

        <div class="content">
            {content_html}
        </div>

        <div class="footer">
            Generado con <a href="#">AutoStory Builder</a>
            — Narrativas que suenan a tu empresa
        </div>
    </div>
</body>
</html>"""

    logger.info("html_rendered", title=title[:30], content_length=len(content_html))
    return html
