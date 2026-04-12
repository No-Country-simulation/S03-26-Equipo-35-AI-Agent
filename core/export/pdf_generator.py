"""Generador de PDF para historias.

Convierte una historia (título + contenido markdown) en un PDF
profesional con tipografía DM Sans / DM Serif Display, header
con branding y footer con metadata.

Usa fpdf2 (sin dependencias externas pesadas).
"""

import re

import structlog
from fpdf import FPDF

logger = structlog.get_logger()

# Directorio de fuentes (usamos las built-in de fpdf2 para simplificar)
# En producción se podría usar DM Sans TTF
_MARGIN = 20
_PAGE_WIDTH = 210  # A4 en mm
_CONTENT_WIDTH = _PAGE_WIDTH - (2 * _MARGIN)


class StoryPDF(FPDF):
    """PDF personalizado con header y footer de AutoStory Builder."""

    def __init__(self, story_title: str, story_type: str) -> None:
        super().__init__()
        self.story_title = story_title
        self.story_type = story_type

    def header(self) -> None:
        """Header con branding en cada página."""
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(186, 117, 23)  # #BA7517
        self.cell(0, 8, "AutoStory Builder", align="L")
        self.set_text_color(150, 150, 150)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 8, self.story_type.title(), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 220, 220)
        self.line(self.l_margin, self.get_y(), _PAGE_WIDTH - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        """Footer con número de página."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")


def _strip_markdown(text: str) -> list[dict[str, str]]:
    """Convierte markdown básico en bloques tipificados para renderizar.

    Soporta: headers (#), bold (**), listas (- o *), párrafos.

    Args:
        text: Contenido en formato markdown.

    Returns:
        Lista de dicts con 'type' (h1, h2, h3, bold, list, paragraph)
        y 'text' (contenido limpio).
    """
    blocks: list[dict[str, str]] = []
    lines = text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("### "):
            blocks.append({"type": "h3", "text": stripped[4:]})
        elif stripped.startswith("## "):
            blocks.append({"type": "h2", "text": stripped[3:]})
        elif stripped.startswith("# "):
            blocks.append({"type": "h1", "text": stripped[2:]})
        elif stripped.startswith(("- ", "* ", "• ")):
            # Elemento de lista
            bullet_text = stripped[2:]
            blocks.append({"type": "list", "text": bullet_text})
        elif stripped.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            blocks.append({"type": "list", "text": stripped})
        else:
            # Limpiar markdown inline básico (**bold**, *italic*, etc.)
            clean = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
            clean = re.sub(r"\*(.*?)\*", r"\1", clean)
            clean = re.sub(r"`(.*?)`", r"\1", clean)
            blocks.append({"type": "paragraph", "text": clean})

    return blocks


def generate_story_pdf(
    title: str,
    content: str,
    story_type: str = "blog",
    created_at: str = "",
) -> bytes:
    """Genera un PDF profesional a partir de una historia.

    Args:
        title: Título de la historia.
        content: Contenido en formato markdown.
        story_type: Tipo de contenido (para metadata).
        created_at: Fecha de creación (para footer informativo).

    Returns:
        Bytes del archivo PDF listo para descargar.
    """
    pdf = StoryPDF(story_title=title, story_type=story_type)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_margins(_MARGIN, _MARGIN + 15, _MARGIN)

    # ── Título principal ──
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(
        w=_CONTENT_WIDTH,
        h=10,
        text=title,
        align="L",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)

    # ── Metadata ──
    if created_at:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(
            w=_CONTENT_WIDTH,
            h=6,
            text=f"Generado el {created_at[:10]} · {story_type.title()}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(4)

    # Separador
    pdf.set_draw_color(186, 117, 23)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 40, pdf.get_y())
    pdf.ln(8)

    # ── Contenido ──
    blocks = _strip_markdown(content)

    for block in blocks:
        block_type = block["type"]
        text = block["text"]

        if block_type == "h1":
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(w=_CONTENT_WIDTH, h=8, text=text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        elif block_type == "h2":
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(w=_CONTENT_WIDTH, h=7, text=text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        elif block_type == "h3":
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(w=_CONTENT_WIDTH, h=7, text=text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        elif block_type == "list":
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            # Indentar listas
            pdf.set_x(pdf.l_margin + 6)
            pdf.multi_cell(
                w=_CONTENT_WIDTH - 6,
                h=6,
                text=f"•  {text}",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.ln(1)

        else:  # paragraph
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(w=_CONTENT_WIDTH, h=6, text=text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    # ── Output ──
    pdf_bytes = pdf.output()

    logger.info(
        "pdf_generated",
        title=title[:50],
        pages=pdf.page_no(),
        size_bytes=len(pdf_bytes),
    )

    return bytes(pdf_bytes)
