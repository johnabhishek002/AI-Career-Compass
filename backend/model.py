import json
import re
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class OllamaError(RuntimeError):
    pass


class WeekPlan(BaseModel):
    week: int = Field(ge=1, le=8)
    title: str = Field(min_length=2, max_length=100)
    tasks: list[str] = Field(min_length=1, max_length=5)
    project_suggestion: str = Field(min_length=2, max_length=300)


class CareerGuidance(BaseModel):
    career_id: str
    fit_explanation: str = Field(min_length=10, max_length=700)
    gap_explanation: str = Field(min_length=10, max_length=700)
    weeks: list[WeekPlan] = Field(min_length=8, max_length=8)


class GuidanceResponse(BaseModel):
    careers: list[CareerGuidance] = Field(min_length=1, max_length=6)


def build_guidance_prompt(profile: dict, recommendations: list[dict]) -> str:
    try:
        instructions = Path(__file__).with_name("skills.md").read_text(encoding="utf-8")
    except OSError as error:
        raise OllamaError("The local career guidance prompt file could not be read.") from error

    request_data = {
        "profile": {
            "education": profile["education"],
            "interests": profile["interests"],
            "skills": profile["skills"],
            "career_goal": profile["career_goal"],
        },
        "careers": [{
            "career_id": item["career_id"],
            "title": item["title"],
            "matched_interests": item["matched_interests"],
            "matched_skills": item["matched_skills"],
            "missing_skills": item["missing_skills"],
            "curated_projects": item["projects"],
        } for item in recommendations],
    }
    schema = json.dumps(GuidanceResponse.model_json_schema(), ensure_ascii=True)
    context = json.dumps(request_data, ensure_ascii=True)
    return f"{instructions}\n\nRequired JSON schema:\n{schema}\n\nStudent profile and curated careers:\n{context}"


def parse_guidance(content: str, expected_ids: set[str]) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        result = GuidanceResponse.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError, TypeError) as error:
        raise OllamaError("Ollama returned guidance that did not match the required JSON format.") from error
    returned_ids = {career.career_id for career in result.careers}
    if returned_ids != expected_ids or len(returned_ids) != len(result.careers):
        raise OllamaError("Ollama returned guidance for unexpected careers.")
    for career in result.careers:
        if [week.week for week in career.weeks] != list(range(1, 9)):
            raise OllamaError("Ollama did not return all eight roadmap weeks in order.")
    return result.model_dump()