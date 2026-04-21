"""Router y providers LLM para AutoStory Builder."""

from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """Respuesta de un proveedor LLM."""

    content: str
    provider: str  # 'groq', 'gemini', 'openrouter'
    model: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)
