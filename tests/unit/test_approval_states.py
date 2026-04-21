"""Tests de la máquina de estados de aprobación.

🔴 CRÍTICO — CI bloquea si fallan.
Verifica que no se pueden saltar estados y que los roles se respetan.

Estos tests tienen lógica REAL implementada porque state_machine.py
está completamente implementado.
"""

import pytest

from core.approvals.state_machine import (
    InvalidTransitionError,
    get_available_transitions,
    transition,
)


class TestApprovalStateMachine:
    """Suite de tests para la máquina de estados de aprobación."""

    # ── Transiciones válidas ──

    def test_editor_can_send_borrador_to_revision(self) -> None:
        """Editor puede enviar un borrador a revisión."""
        result = transition("borrador", "en_revision", "editor")
        assert result == "en_revision"

    def test_revisor_can_approve_content(self) -> None:
        """Revisor puede aprobar contenido en revisión."""
        result = transition("en_revision", "aprobado", "revisor")
        assert result == "aprobado"

    def test_revisor_can_reject_content(self) -> None:
        """Revisor puede rechazar contenido en revisión."""
        result = transition("en_revision", "rechazado", "revisor")
        assert result == "rechazado"

    def test_admin_can_publish_approved_content(self) -> None:
        """Admin puede publicar contenido aprobado."""
        result = transition("aprobado", "publicado", "admin")
        assert result == "publicado"

    def test_editor_can_revert_rejected_to_borrador(self) -> None:
        """Editor puede revertir contenido rechazado a borrador."""
        result = transition("rechazado", "borrador", "editor")
        assert result == "borrador"

    def test_admin_can_do_any_valid_transition(self) -> None:
        """Admin puede realizar cualquier transición válida."""
        assert transition("borrador", "en_revision", "admin") == "en_revision"
        assert transition("en_revision", "aprobado", "admin") == "aprobado"
        assert transition("en_revision", "rechazado", "admin") == "rechazado"
        assert transition("rechazado", "borrador", "admin") == "borrador"
        assert transition("aprobado", "publicado", "admin") == "publicado"

    # ── Transiciones inválidas ──

    def test_cannot_skip_from_borrador_to_aprobado(self) -> None:
        """No se puede saltar de borrador directamente a aprobado."""
        with pytest.raises(InvalidTransitionError):
            transition("borrador", "aprobado", "admin")

    def test_cannot_skip_from_borrador_to_publicado(self) -> None:
        """No se puede saltar de borrador directamente a publicado."""
        with pytest.raises(InvalidTransitionError):
            transition("borrador", "publicado", "admin")

    def test_editor_cannot_approve(self) -> None:
        """Editor no tiene permiso para aprobar contenido."""
        with pytest.raises(InvalidTransitionError):
            transition("en_revision", "aprobado", "editor")

    def test_editor_cannot_publish(self) -> None:
        """Editor no tiene permiso para publicar contenido."""
        with pytest.raises(InvalidTransitionError):
            transition("aprobado", "publicado", "editor")

    def test_revisor_cannot_publish(self) -> None:
        """Revisor no tiene permiso para publicar contenido."""
        with pytest.raises(InvalidTransitionError):
            transition("aprobado", "publicado", "revisor")

    def test_publicado_is_terminal_state(self) -> None:
        """Publicado es un estado terminal — no hay transiciones de salida."""
        with pytest.raises(InvalidTransitionError):
            transition("publicado", "borrador", "admin")

    # ── Validación de inputs ──

    def test_invalid_state_raises_value_error(self) -> None:
        """Estado inválido lanza ValueError."""
        with pytest.raises(ValueError, match="Estado actual no válido"):
            transition("inexistente", "borrador", "admin")

    def test_invalid_role_raises_value_error(self) -> None:
        """Rol inválido lanza ValueError."""
        with pytest.raises(ValueError, match="Rol no válido"):
            transition("borrador", "en_revision", "superadmin")

    # ── get_available_transitions ──

    def test_get_available_transitions_for_editor(self) -> None:
        """Editor desde borrador solo puede enviar a revisión."""
        available = get_available_transitions("borrador", "editor")
        assert available == ["en_revision"]

    def test_get_available_transitions_for_revisor(self) -> None:
        """Revisor desde en_revision puede aprobar o rechazar."""
        available = get_available_transitions("en_revision", "revisor")
        assert sorted(available) == ["aprobado", "rechazado"]

    def test_publicado_has_no_transitions(self) -> None:
        """Estado publicado no tiene transiciones disponibles."""
        available = get_available_transitions("publicado", "admin")
        assert available == []
