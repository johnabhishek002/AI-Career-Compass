import ipaddress
import os
from urllib.parse import urlsplit

import requests

from model import GuidanceResponse, OllamaError, build_guidance_prompt, parse_guidance


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MODEL_ENV = "OLLAMA_MODEL"


def ensure_local_ollama_url() -> None:
    parsed = urlsplit(OLLAMA_URL)
    hostname = parsed.hostname or ""
    try:
        is_loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname.lower() == "localhost"
    if parsed.scheme not in {"http", "https"} or not is_loopback:
        raise OllamaError("OLLAMA_URL must point to a local loopback host; student data is never sent to remote AI services.")


def installed_models(timeout: float = 3.0) -> list[str]:
    ensure_local_ollama_url()
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return [model["name"] for model in payload.get("models", []) if isinstance(model.get("name"), str)]
    except (requests.RequestException, ValueError, TypeError) as error:
        raise OllamaError("Ollama is unavailable. Start Ollama locally to use AI guidance.") from error


def resolve_model(models: list[str] | None = None) -> str:
    models = installed_models() if models is None else models
    configured = os.getenv(MODEL_ENV, "").strip()
    if configured:
        if configured not in models:
            raise OllamaError(f"Configured OLLAMA_MODEL '{configured}' is not installed. Installed models: {', '.join(models) or 'none'}.")
        return configured
    for name in ["llama3.2:1b", "llama3.2:3b"]:
        if name in models:
            return name
    if models:
        return models[0]
    raise OllamaError("No Ollama models are installed. Pull a model and set OLLAMA_MODEL if needed.")


def ollama_status() -> dict:
    models = []
    try:
        models = installed_models()
        model = resolve_model(models)
        return {"available": True, "url": OLLAMA_URL, "model": model, "installed_models": models}
    except OllamaError as error:
        return {"available": False, "url": OLLAMA_URL, "model": os.getenv(MODEL_ENV) or None, "installed_models": models, "message": str(error)}


def generate_guidance(profile: dict, recommendations: list[dict], timeout: float = 150.0) -> dict:
    models = installed_models()
    model = resolve_model(models)
    expected = {recommendation["career_id"] for recommendation in recommendations}
    prompt = build_guidance_prompt(profile, recommendations)
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": GuidanceResponse.model_json_schema(),
                "options": {"temperature": 0.3},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json().get("response", "")
    except requests.Timeout as error:
        raise OllamaError("The local Ollama model took too long to respond. Try again or choose a smaller installed model.") from error
    except (requests.RequestException, ValueError, TypeError) as error:
        raise OllamaError("Could not get a response from local Ollama.") from error
    return parse_guidance(content, expected)


def demo_guidance(recommendations: list[dict]) -> dict:
    themes = [
        "Set a direction", "Learn the foundations", "Practice core tools", "Build a first version",
        "Add a useful feature", "Review and improve", "Polish the project", "Share and reflect",
    ]
    output = []
    for recommendation in recommendations:
        projects = recommendation["projects"]
        gap = ", ".join(recommendation["missing_skills"][:4]) or "no listed gaps"
        interest = ", ".join(recommendation["matched_interests"][:3]) or "your stated goal"
        weeks = []
        for number, theme in enumerate(themes, start=1):
            task = (
                f"Choose one beginner resource and write down three takeaways about {gap}." if number == 1 else
                f"Complete a small hands-on exercise using {recommendation['missing_skills'][(number - 2) % len(recommendation['missing_skills'])]} and record what you learned." if recommendation["missing_skills"] and number < 7 else
                "Improve your project using feedback, test the result, and document one decision."
            )
            weeks.append({
                "week": number,
                "title": theme,
                "tasks": [task],
                "project_suggestion": projects[(number - 1) % len(projects)],
            })
        output.append({
            "career_id": recommendation["career_id"],
            "fit_explanation": f"Your profile lists interests related to {interest}. This is a starting point to explore, not a prediction of employment outcomes.",
            "gap_explanation": recommendation["gap_explanation"],
            "weeks": weeks,
        })
    return {"careers": output}