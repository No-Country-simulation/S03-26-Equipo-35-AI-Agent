"""Tests unitarios para el estado del grafo LangGraph.

Verifica que el ContentGenerationState TypedDict se inicializa
correctamente y que los campos tienen los tipos esperados.
"""


from core.agents.state import ContentGenerationState


class TestContentGenerationState:
    """Tests del TypedDict ContentGenerationState."""

    def test_state_can_be_created_with_all_fields(self):
        """El estado debe poder crearse con todos los campos."""
        state: ContentGenerationState = {
            "task": "Escribe un blog post",
            "org_id": "test-org-123",
            "story_type": "blog",
            "tone": "profesional",
            "audience": "clientes",
            "length": "medio",
            "temperature": 0.6,
            "analytics_data": "",
            "assets": [],
            "rag_chunks": [],
            "brand_insights": "",
            "visual_context": "",
            "draft_content": "",
            "qa_feedback": "",
            "qa_approved": False,
            "retry_count": 0,
            "final_content": "",
            "provider": "",
            "model": "",
            "latency_ms": 0.0,
            "tokens_used": 0,
            "error": None,
            "status": "ok",
        }

        assert state["task"] == "Escribe un blog post"
        assert state["org_id"] == "test-org-123"
        assert state["qa_approved"] is False
        assert state["retry_count"] == 0
        assert state["status"] == "ok"
        assert state["error"] is None

    def test_state_supports_all_story_types(self):
        """El estado debe soportar todos los story_types válidos."""
        valid_types = ["blog", "internal", "press", "email", "youtube", "instagram", "facebook", "twitter", "tiktok"]
        for story_type in valid_types:
            state: ContentGenerationState = {
                "task": "test",
                "org_id": "test",
                "story_type": story_type,
                "tone": "profesional",
                "audience": "clientes",
                "length": "medio",
                "temperature": 0.6,
                "analytics_data": "",
                "assets": [],
                "rag_chunks": [],
                "brand_insights": "",
                "visual_context": "",
                "draft_content": "",
                "qa_feedback": "",
                "qa_approved": False,
                "retry_count": 0,
                "final_content": "",
                "provider": "",
                "model": "",
                "latency_ms": 0.0,
                "tokens_used": 0,
                "error": None,
                "status": "ok",
            }
            assert state["story_type"] == story_type

    def test_state_error_field_can_be_string(self):
        """El campo error puede ser un string cuando hay error."""
        state: ContentGenerationState = {
            "task": "test",
            "org_id": "test",
            "story_type": "blog",
            "tone": "profesional",
            "audience": "clientes",
            "length": "medio",
            "temperature": 0.6,
            "analytics_data": "",
            "assets": [],
            "rag_chunks": [],
            "brand_insights": "",
            "visual_context": "",
            "draft_content": "",
            "qa_feedback": "",
            "qa_approved": False,
            "retry_count": 0,
            "final_content": "",
            "provider": "",
            "model": "",
            "latency_ms": 0.0,
            "tokens_used": 0,
            "error": "Connection timeout",
            "status": "error",
        }
        assert state["error"] == "Connection timeout"
        assert state["status"] == "error"
