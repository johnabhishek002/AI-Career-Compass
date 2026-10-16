CAREERS = [
    {
        "id": "ai-ml-engineer",
        "title": "AI/ML Engineer",
        "description": "Build and evaluate software systems that learn patterns from data.",
        "skills": ["python", "statistics", "linear algebra", "machine learning", "data analysis", "sql", "model evaluation", "software engineering"],
        "interests": ["artificial intelligence", "machine learning", "mathematics", "research", "automation", "data"],
        "projects": ["Train and evaluate a small image or text classifier", "Compare simple recommendation approaches on an open dataset"],
    },
    {
        "id": "software-developer",
        "title": "Software Developer",
        "description": "Design, implement, test, and maintain software applications and services.",
        "skills": ["programming", "python", "javascript", "data structures", "software engineering", "git", "testing", "problem solving"],
        "interests": ["building apps", "technology", "problem solving", "automation", "games", "creative coding"],
        "projects": ["Build a command-line tool that solves a real everyday problem", "Create a small application with tests and clear documentation"],
    },
    {
        "id": "web-developer",
        "title": "Web Developer",
        "description": "Create accessible, responsive websites and web applications.",
        "skills": ["html", "css", "javascript", "react", "accessibility", "git", "web apis", "testing"],
        "interests": ["web design", "building apps", "visual design", "user experience", "creative coding", "technology"],
        "projects": ["Build an accessible responsive portfolio site", "Create a small dashboard that consumes a public API"],
    },
    {
        "id": "data-analyst",
        "title": "Data Analyst",
        "description": "Turn structured data into clear findings that help teams make decisions.",
        "skills": ["sql", "data analysis", "statistics", "spreadsheets", "data visualization", "python", "communication", "critical thinking"],
        "interests": ["data", "research", "business", "patterns", "communication", "problem solving"],
        "projects": ["Analyze a public dataset and publish a concise visual report", "Create a dashboard that answers three practical questions"],
    },
    {
        "id": "cybersecurity-analyst",
        "title": "Cybersecurity Analyst",
        "description": "Help protect systems by identifying risks, investigating signals, and improving defenses.",
        "skills": ["networking", "linux", "security fundamentals", "python", "risk analysis", "incident response", "communication", "systems administration"],
        "interests": ["cybersecurity", "privacy", "investigation", "networks", "systems", "problem solving"],
        "projects": ["Create a home lab and document a basic security audit", "Analyze sample logs and write a concise incident timeline"],
    },
    {
        "id": "cloud-engineer",
        "title": "Cloud Engineer",
        "description": "Deploy and operate reliable applications and infrastructure using cloud platforms.",
        "skills": ["linux", "networking", "cloud fundamentals", "containers", "python", "security fundamentals", "git", "systems administration"],
        "interests": ["cloud computing", "infrastructure", "automation", "networks", "systems", "technology"],
        "projects": ["Containerize and document a small web service", "Design a cloud deployment diagram with security and cost considerations"],
    },
]

CAREER_BY_ID = {career["id"]: career for career in CAREERS}


def normalize_terms(values: list[str]) -> set[str]:
    return {" ".join(value.lower().strip().split()) for value in values if value.strip()}


def score_career(profile: dict, career: dict) -> dict:
    skills = normalize_terms(profile.get("skills", []))
    interests = normalize_terms(profile.get("interests", []))
    career_skills = normalize_terms(career["skills"])
    career_interests = normalize_terms(career["interests"])
    matched_skills = sorted(skills & career_skills)
    missing_skills = sorted(career_skills - skills)
    matched_interests = sorted(interests & career_interests)
    skill_points = 60 * len(matched_skills) / max(len(career_skills), 1)
    interest_points = 30 * len(matched_interests) / max(len(career_interests), 1)
    goal_terms = normalize_terms(profile.get("goal_keywords", []))
    goal_matches = sorted(goal_terms & (career_skills | career_interests))
    goal_points = min(10, 2 * len(goal_matches))
    score = round(min(100, skill_points + interest_points + goal_points))
    reasons = []
    if matched_interests:
        reasons.append(f"Your interests align with {', '.join(matched_interests)}.")
    if matched_skills:
        reasons.append(f"You already list relevant skills: {', '.join(matched_skills)}.")
    if not reasons:
        reasons.append("This is an exploratory option; your current profile does not yet list a direct skills or interests match.")
    return {
        "career_id": career["id"],
        "title": career["title"],
        "description": career["description"],
        "score": score,
        "matched_skills": matched_skills,
        "matched_interests": matched_interests,
        "missing_skills": missing_skills,
        "explanation": " ".join(reasons),
        "gap_explanation": "Skills in this curated starter profile that are not listed in your profile: " + (", ".join(missing_skills) if missing_skills else "none"),
        "projects": career["projects"],
    }


def recommend_careers(profile: dict) -> list[dict]:
    goal_words = set(" ".join(profile.get("goals", "").lower().split()))
    scored = []
    for career in CAREERS:
        goal_keywords = [word for word in goal_words if len(word) > 3]
        scored.append(score_career({**profile, "goal_keywords": goal_keywords}, career))
    return sorted(scored, key=lambda item: (-item["score"], item["title"]))


def skill_gap(profile: dict, career_id: str) -> dict:
    career = CAREER_BY_ID.get(career_id)
    if career is None:
        raise KeyError(career_id)
    result = score_career(profile, career)
    return {
        "career_id": career_id,
        "career_title": career["title"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "gap_explanation": result["gap_explanation"],
    }