"""Tests unitarios del scraper RAG — validación de URLs.

Verifica la protección contra SSRF y la validación de URLs.
No requiere API keys ni conexión a servicios externos.
Solo testea _validate_url (función pura, sin I/O).
"""

import pytest

from core.rag.scraper import _validate_url


class TestURLValidation:
    """Tests de validación y sanitización de URLs contra SSRF."""

    def test_validate_url_accepts_https(self) -> None:
        """URLs HTTPS válidas pasan la validación.

        Arrange: URL HTTPS de un sitio público
        Act: _validate_url
        Assert: Retorna la URL sin modificar
        """
        url = "https://www.example.com/page"
        result = _validate_url(url)
        assert result == url

    def test_validate_url_rejects_http(self) -> None:
        """URLs HTTP (sin TLS) son rechazadas.

        Arrange: URL HTTP
        Act: _validate_url
        Assert: ValueError mencionando HTTPS
        """
        with pytest.raises(ValueError, match="HTTPS"):
            _validate_url("http://www.example.com/page")

    def test_validate_url_rejects_ftp(self) -> None:
        """URLs con otros protocolos son rechazadas."""
        with pytest.raises(ValueError, match="HTTPS"):
            _validate_url("ftp://files.example.com/doc.pdf")

    def test_validate_url_rejects_localhost(self) -> None:
        """URLs apuntando a localhost son rechazadas.

        Arrange: URL con localhost
        Act: _validate_url
        Assert: ValueError mencionando hostname bloqueado
        """
        with pytest.raises(ValueError, match="bloqueado"):
            _validate_url("https://localhost/admin")

    def test_validate_url_rejects_127_0_0_1(self) -> None:
        """URLs con 127.0.0.1 son rechazadas."""
        with pytest.raises(ValueError, match="bloqueado"):
            _validate_url("https://127.0.0.1/admin")

    def test_validate_url_rejects_long_urls(self) -> None:
        """URLs mayores a 2048 chars son rechazadas.

        Arrange: URL de 3000 chars
        Act: _validate_url
        Assert: ValueError mencionando longitud
        """
        long_url = "https://example.com/" + "a" * 3000
        with pytest.raises(ValueError, match="larga"):
            _validate_url(long_url)

    def test_validate_url_rejects_non_standard_port(self) -> None:
        """URLs con puertos no estándar son rechazadas.

        Arrange: URL con puerto 8080
        Act: _validate_url
        Assert: ValueError mencionando puerto
        """
        with pytest.raises(ValueError, match="443"):
            _validate_url("https://example.com:8080/page")

    def test_validate_url_accepts_standard_port_443(self) -> None:
        """URLs con puerto 443 explícito son aceptadas."""
        url = "https://example.com:443/page"
        result = _validate_url(url)
        assert result == url

    def test_validate_url_rejects_empty_hostname(self) -> None:
        """URLs sin hostname son rechazadas."""
        with pytest.raises(ValueError):
            _validate_url("https:///path")
