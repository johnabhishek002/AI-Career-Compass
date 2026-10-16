import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import ai_service
import career_data
import database


class StudentProfileInput(BaseModel):
    name: str = Field(default="", max_length=80)
    education: str = Field(min_length=2, max_length=240)
    interests: list[str] = Field(min_length=1, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=40)
    career_goal: str = Field(min_length=2, max_length=600)


class RecommendationRequest(BaseModel):
    profile_id: int = Field(gt=0)
    limit: int = Field(default=3, ge=1, le=6)


class SkillGapRequest(BaseModel):
    profile_id: int = Field(gt=0)
    career_id: str


class RoadmapRequest(BaseModel):
    profile_id: int = Field(gt=0)
    career_id: str


class ProgressRequest(BaseModel):
    roadmap_id: int = Field(gt=0)
    week_number: int = Field(ge=1, le=8)
    task_index: int = Field(ge=0, le=4)
    completed: bool


def profile_as_match_input(profile: dict) -> dict:
    return {
        "education": profile["education"],
        "interests": profile["interests"],
        "skills": profile["skills"],
        "goals": profile["career_goal"],
    }


def build_recommendations(profile: dict, limit: int) -> list[dict]:
    return career_data.recommend_careers(profile_as_match_input(profile))[:limit]


def create_saved_roadmaps(profile: dict, recommendations: list[dict]) -> tuple[list[dict], str, str | None]:
    roadmaps = []
    sources = []
    failures = []
    for recommendation in recommendations:
        try:
            item = ai_service.generate_guidance(profile, [recommendation])["careers"][0]
            source: Literal["ollama", "demo"] = "ollama"
        except ai_service.OllamaError as error:
            item = ai_service.demo_guidance([recommendation])["careers"][0]
            source = "demo"
            failures.append(f"{recommendation['title']}: {error}")
        sources.append(source)
        roadmap = {
            "fit_explanation": item["fit_explanation"],
            "gap_explanation": recommendation["gap_explanation"],
            "guidance_gap_explanation": item["gap_explanation"],
            "weeks": item["weeks"],
            "projects": recommendation["projects"],
        }
        roadmaps.append(database.save_roadmap(
            profile_id=profile["id"],
            career_id=recommendation["career_id"],
            career_title=recommendation["title"],
            roadmap=roadmap,
            source=source,
        ))
    source = sources[0] if len(set(sources)) == 1 else "mixed"
    message = None if not failures else (
        "Demo mode was used for some paths because local AI guidance was unavailable or invalid. "
        "Those roadmaps use local starter templates, not AI. " + " ".join(failures)
    )
    return roadmaps, source, message


database.initialize_database()

app = FastAPI(
    title="AI Career Compass API",
    description=(
        "Local-first career guidance for students. Career scores and skill gaps are calculated "
        "transparently from a curated dataset. Optional Ollama guidance runs on your device; "
        "demo roadmaps are labeled and are used if Ollama is unavailable. No paid AI key is used."
    ),
    version="1.0.0",
)
allowed_origins = [origin.strip() for origin in os.getenv(
    "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "ollama": ai_service.ollama_status()}


@app.get("/api/careers", tags=["Careers"], summary="List curated career profiles")
def list_careers() -> dict:
    return {"careers": [
        {"id": item["id"], "title": item["title"], "description": item["description"], "skills": item["skills"], "interests": item["interests"], "projects": item["projects"]}
        for item in career_data.CAREERS
    ]}


@app.post("/api/profiles", status_code=201, tags=["Student Profiles"], summary="Save a student profile locally")
def create_student_profile(payload: StudentProfileInput) -> dict:
    cleaned = payload.model_dump()
    cleaned["name"] = cleaned["name"].strip()
    cleaned["education"] = cleaned["education"].strip()
    cleaned["career_goal"] = cleaned["career_goal"].strip()
    cleaned["interests"] = list(dict.fromkeys(item.strip() for item in cleaned["interests"] if item.strip()))
    cleaned["skills"] = list(dict.fromkeys(item.strip() for item in cleaned["skills"] if item.strip()))
    if not cleaned["interests"]:
        raise HTTPException(status_code=422, detail="Add at least one interest.")
    return database.create_profile(cleaned)


@app.get("/api/profiles/{profile_id}", tags=["Student Profiles"])
def get_student_profile(profile_id: int) -> dict:
    profile = database.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return profile


@app.post("/api/recommendations", tags=["Career Guidance"], summary="Calculate transparent career matches and generate roadmap guidance")
def recommend(payload: RecommendationRequest) -> dict:
    profile = database.get_profile(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    recommendations = build_recommendations(profile, payload.limit)
    roadmaps, source, notice = create_saved_roadmaps(profile, recommendations)
    roadmap_by_career = {item["career_id"]: item for item in roadmaps}
    careers = []
    for item in recommendations:
        saved = roadmap_by_career[item["career_id"]]
        careers.append({
            **item,
            "fit_explanation": saved["fit_explanation"],
            "guidance_gap_explanation": saved["guidance_gap_explanation"],
            "weeks": saved["weeks"],
            "roadmap_id": saved["id"],
            "source": saved["source"],
        })
    return {
        "profile_id": profile["id"],
        "careers": careers,
        "roadmaps": roadmaps,
        "source": source,
        "notice": notice,
        "matching_method": "Deterministic rule-based scoring: 60 points skill overlap, 30 points interest overlap, and up to 10 goal-keyword points.",
    }


@app.get("/api/recommendations/{profile_id}", tags=["Career Guidance"], summary="Retrieve deterministic career matches")
def get_recommendations(profile_id: int, limit: int = Query(default=3, ge=1, le=6)) -> dict:
    profile = database.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return {"profile_id": profile_id, "careers": build_recommendations(profile, limit)}


@app.post("/api/skill-gaps", tags=["Career Guidance"], summary="Analyze skills against the curated career profile")
def analyze_skill_gaps(payload: SkillGapRequest) -> dict:
    profile = database.get_profile(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    try:
        return career_data.skill_gap(profile_as_match_input(profile), payload.career_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Career profile not found.") from error


@app.post("/api/roadmaps", tags=["Learning Roadmaps"], summary="Generate and save an eight-week roadmap")
def generate_roadmap(payload: RoadmapRequest) -> dict:
    profile = database.get_profile(payload.profile_id)
    career = career_data.CAREER_BY_ID.get(payload.career_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    if career is None:
        raise HTTPException(status_code=404, detail="Career profile not found.")
    recommendation = next(item for item in build_recommendations(profile, len(career_data.CAREERS)) if item["career_id"] == payload.career_id)
    roadmaps, source, notice = create_saved_roadmaps(profile, [recommendation])
    return {**roadmaps[0], "notice": notice}


@app.get("/api/roadmaps", tags=["Learning Roadmaps"], summary="Retrieve saved roadmaps for a profile")
def get_saved_roadmaps(profile_id: int = Query(gt=0)) -> dict:
    if database.get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return {"roadmaps": database.list_roadmaps(profile_id)}


@app.get("/api/roadmaps/{roadmap_id}", tags=["Learning Roadmaps"])
def get_saved_roadmap(roadmap_id: int) -> dict:
    roadmap = database.get_roadmap(roadmap_id)
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Roadmap not found.")
    return roadmap


@app.patch("/api/progress", tags=["Progress"], summary="Update completion state for one roadmap task")
def update_learning_progress(payload: ProgressRequest) -> dict:
    roadmap = database.get_roadmap(payload.roadmap_id)
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Roadmap not found.")
    week = next((item for item in roadmap["weeks"] if item["week"] == payload.week_number), None)
    if week is None or payload.task_index >= len(week["tasks"]):
        raise HTTPException(status_code=422, detail="Task index does not exist in that roadmap week.")
    updated = database.update_progress(payload.roadmap_id, payload.week_number, payload.task_index, payload.completed)
    return {"ok": True, "roadmap": updated}


@app.get("/api/dashboard", tags=["Progress"], summary="Retrieve the most recently saved profile and learning progress")
def dashboard() -> dict:
    return database.get_dashboard()