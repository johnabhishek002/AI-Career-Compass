# AI Career Compass

A privacy-focused student career guidance app. Python performs transparent career matching and skill-gap calculations against a curated dataset. Ollama can explain matches and produce personalized weekly learning guidance on the same machine. SQLite stores profiles, roadmaps, and task progress locally. There are no paid AI API keys or external AI requests.

## Features

- Six curated career profiles: AI/ML Engineer, Software Developer, Web Developer, Data Analyst, Cybersecurity Analyst, and Cloud Engineer.
- Deterministic career scores: up to 60 points for current skill overlap, 30 for interest overlap, and 10 for goal-keyword overlap.
- Explicit matched and missing skills from the selected career's dataset.
- Validated eight-week Ollama guidance with one or more tasks and a beginner-friendly project suggestion each week.
- Clearly labeled demo guidance when Ollama is unavailable; demo content is not presented as AI output.
- SQLite persistence for student profiles, roadmaps, and individual task completion.
- Responsive React + Vite dashboard with career comparison, skill gaps, roadmap tasks, and progress summary.

## Project structure

```text
ai-career-compass/
|-- backend/
|   |-- ai_service.py
|   |-- career_data.py
|   |-- database.py
|   |-- main.py
|   |-- model.py
|   |-- requirements.txt
|   |-- skills.md
|   |-- tools.py
|   `-- tests/
|       `-- test_backend.py
|-- frontend/
|   |-- src/
|   |   |-- App.jsx
|   |   |-- main.jsx
|   |   `-- styles.css
|   |-- .env.example
|   |-- index.html
|   |-- package.json
|   `-- vite.config.js
|-- .gitignore
`-- README.md
```

The Ollama response schema and prompt builder live in `backend/model.py`; prompt instructions are in `backend/skills.md`; model discovery and inference helpers are in `backend/tools.py`. `backend/ai_service.py` retains compatibility exports for the API.

## Start Ollama

Keep Ollama running locally at `http://localhost:11434`. In a PowerShell terminal, check installed models:

```powershell
ollama list
```

If a model is not listed, install one, for example:

```powershell
ollama pull llama3.2:3b
```

The backend reads `OLLAMA_MODEL` and verifies it against `/api/tags`. If it is not set, the backend selects an installed model: `llama3.2:1b` only when present, then `llama3.2:3b` when present, otherwise the first installed model. To choose explicitly, set the environment variable before starting Uvicorn:

```powershell
$env:OLLAMA_MODEL = "llama3.2:3b"
```

## Start the backend

Open a PowerShell terminal in `C:\Hackthon2\ai-career-compass` and run:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:OLLAMA_MODEL = "llama3.2:3b"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Set the model value to one shown by `ollama list`. If the existing `.venv` is missing, create it from `backend` with `python -m venv .venv` first. The API is at `http://127.0.0.1:8000`; interactive docs are at `http://127.0.0.1:8000/docs`.

Useful configuration:

```powershell
$env:OLLAMA_URL = "http://localhost:11434"
$env:OLLAMA_MODEL = "gemma3:1b"
$env:CAREER_COMPASS_DB = "C:\Users\you\career-compass.db"
$env:FRONTEND_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
```

## Start the frontend

Install Node.js LTS first if `node` and `npm` are not available. Open a second PowerShell terminal in the project directory:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://127.0.0.1:5173`. The Vite dev server proxies `/api` to the local backend. To point the UI to a different API origin, set `VITE_API_BASE_URL` in `frontend/.env.local` (for example, `VITE_API_BASE_URL=http://127.0.0.1:8000`) and restart Vite. Keep it empty when using the included proxy.

## API overview

- `GET /api/health` checks API and Ollama availability and reports the selected installed model.
- `GET /api/careers` lists curated career profiles, skills, interests, and projects.
- `POST /api/profiles` saves a validated student profile.
- `GET /api/profiles/{profile_id}` retrieves a profile.
- `POST /api/recommendations` calculates top career matches and generates/saves guidance roadmaps.
- `GET /api/recommendations/{profile_id}` retrieves deterministic career matches.
- `POST /api/skill-gaps` calculates matched and missing skills for one career.
- `POST /api/roadmaps` generates and saves one career roadmap.
- `GET /api/roadmaps?profile_id={id}` and `GET /api/roadmaps/{roadmap_id}` retrieve saved roadmaps and progress.
- `PATCH /api/progress` updates a roadmap task completion state.
- `GET /api/dashboard` retrieves the latest saved profile and roadmaps.

Profiles, generated plans, and progress are stored in `backend/career_compass.db` by default. Student data is sent only to the configured local Ollama endpoint; when Ollama is down, deterministic match data and template demo plans are used.

## Run backend tests

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Build the frontend

From `frontend` after `npm install`:

```powershell
npm run build
```