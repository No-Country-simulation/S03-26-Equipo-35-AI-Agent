"""Tests unitarios para las reglas de formato QA (sin LLM).

Valida la función _check_format_rules_python() que aplica
restricciones deterministas antes del LLM QA.
"""


from core.agents.nodes import _check_format_rules_python


class TestTwitterRules:
    """Tests para las restricciones del hilo de Twitter."""

    def test_valid_thread_passes(self):
        """Hilo con tweets dentro del límite debe pasar."""
        content = "\n\n".join([
            "1/ Este es el tweet 1 con un contenido válido y dentro del límite.",
            "2/ Este es el tweet 2 también válido.",
            "3/ Tweet 3 con información importante.",
            "4/ Tweet 4 desarrollando la idea.",
            "5/ Tweet 5 con el CTA final. Seguime para más contenido.",
        ])
        passed, feedback = _check_format_rules_python(content, "twitter")
        assert passed is True
        assert feedback == ""

    def test_tweet_over_280_chars_fails(self):
        """Tweet que supera 280 caracteres debe fallar."""
        long_tweet = "1/ " + "x" * 290
        content = "\n\n".join([
            long_tweet,
            "2/ Tweet corto.",
            "3/ Tweet corto.",
            "4/ Tweet corto.",
            "5/ Tweet corto.",
        ])
        passed, feedback = _check_format_rules_python(content, "twitter")
        assert passed is False
        assert "280" in feedback

    def test_too_few_tweets_fails(self):
        """Hilo con menos de 5 tweets debe fallar."""
        content = "\n\n".join([
            "1/ Tweet 1.",
            "2/ Tweet 2.",
            "3/ Tweet 3.",
        ])
        passed, feedback = _check_format_rules_python(content, "twitter")
        assert passed is False
        assert "mínimo" in feedback.lower()

    def test_too_many_tweets_fails(self):
        """Hilo con más de 7 tweets debe fallar."""
        tweets = [f"{i}/ Tweet número {i}." for i in range(1, 10)]
        content = "\n\n".join(tweets)
        passed, feedback = _check_format_rules_python(content, "twitter")
        assert passed is False
        assert "máximo" in feedback.lower()


class TestInstagramRules:
    """Tests para las restricciones del caption de Instagram."""

    def test_valid_caption_passes(self):
        """Caption dentro del límite de 2200 chars debe pasar."""
        content = "Este es un caption válido para Instagram. " * 20  # ~880 chars
        passed, _ = _check_format_rules_python(content, "instagram")
        assert passed is True

    def test_caption_over_limit_fails(self):
        """Caption mayor a 2200 chars debe fallar."""
        content = "x" * 2201
        passed, feedback = _check_format_rules_python(content, "instagram")
        assert passed is False
        assert "2200" in feedback

    def test_caption_exactly_at_limit_passes(self):
        """Caption de exactamente 2200 chars debe pasar."""
        content = "x" * 2200
        passed, _ = _check_format_rules_python(content, "instagram")
        assert passed is True


class TestTikTokRules:
    """Tests para las restricciones del script de TikTok."""

    def test_valid_script_passes(self):
        """Script con menos de 200 palabras debe pasar."""
        content = "palabra " * 150  # 150 palabras
        passed, _ = _check_format_rules_python(content, "tiktok")
        assert passed is True

    def test_script_over_limit_fails(self):
        """Script con más de 200 palabras debe fallar."""
        content = "palabra " * 201
        passed, feedback = _check_format_rules_python(content, "tiktok")
        assert passed is False
        assert "200" in feedback


class TestFacebookRules:
    """Tests para las restricciones del post de Facebook."""

    def test_valid_post_passes(self):
        """Post entre 100 y 600 palabras debe pasar."""
        content = "Esta es una palabra. " * 150  # ~150 palabras
        passed, _ = _check_format_rules_python(content, "facebook")
        assert passed is True

    def test_post_too_short_fails(self):
        """Post con menos de 100 palabras debe fallar."""
        content = "Palabra " * 50
        passed, feedback = _check_format_rules_python(content, "facebook")
        assert passed is False
        assert "mínimo" in feedback.lower()

    def test_post_too_long_fails(self):
        """Post con más de 600 palabras debe fallar."""
        content = "Palabra " * 700
        passed, feedback = _check_format_rules_python(content, "facebook")
        assert passed is False
        assert "máximo" in feedback.lower()


class TestYouTubeRules:
    """Tests para las restricciones del script de YouTube."""

    def test_valid_script_passes(self):
        """Script con HOOK y CTA debe pasar."""
        content = "[HOOK — 0:00-0:05]\nAbre con impacto\n\n[CTA — CIERRE]\nSuscribite al canal."
        passed, _ = _check_format_rules_python(content, "youtube")
        assert passed is True

    def test_missing_hook_fails(self):
        """Script sin sección HOOK debe fallar."""
        content = "Introducción sin hook.\n\n[CTA — CIERRE]\nSuscribite."
        passed, feedback = _check_format_rules_python(content, "youtube")
        assert passed is False
        assert "HOOK" in feedback

    def test_missing_cta_fails(self):
        """Script sin sección CTA debe fallar."""
        content = "[HOOK — 0:00-0:05]\nAbre con impacto.\n\nDesarrollo del tema."
        passed, feedback = _check_format_rules_python(content, "youtube")
        assert passed is False
        assert "CTA" in feedback


class TestUnknownFormat:
    """Tests para formatos sin reglas específicas."""

    def test_unknown_format_always_passes(self):
        """Formatos sin reglas duras deben pasar siempre."""
        passed, _ = _check_format_rules_python("cualquier contenido", "blog")
        assert passed is True

    def test_internal_format_passes(self):
        passed, _ = _check_format_rules_python("contenido interno", "internal")
        assert passed is True
