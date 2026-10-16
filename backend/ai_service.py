"""Compatibility exports for the local Ollama service modules."""

from model import (
    CareerGuidance,
    GuidanceResponse,
    OllamaError,
    WeekPlan,
    build_guidance_prompt,
    parse_guidance,
)
from tools import (
    MODEL_ENV,
    OLLAMA_URL,
    demo_guidance,
    ensure_local_ollama_url,
    generate_guidance,
    installed_models,
    ollama_status,
    resolve_model,
)

__all__ = [
    "CareerGuidance",
    "GuidanceResponse",
    "MODEL_ENV",
    "OLLAMA_URL",
    "OllamaError",
    "WeekPlan",
    "build_guidance_prompt",
    "demo_guidance",
    "ensure_local_ollama_url",
    "generate_guidance",
    "installed_models",
    "ollama_status",
    "parse_guidance",
    "resolve_model",
]