import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "career_compass.db"
DB_PATH = Path(os.getenv("CAREER_COMPASS_DB", DEFAULT_DB_PATH))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                education TEXT NOT NULL,
                interests_json TEXT NOT NULL,
                skills_json TEXT NOT NULL,
                career_goal TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS learning_roadmaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
                career_id TEXT NOT NULL,
                career_title TEXT NOT NULL,
                roadmap_json TEXT NOT NULL,
                source TEXT NOT NULL CHECK(source IN ('ollama', 'demo')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(profile_id, career_id)
            );
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roadmap_id INTEGER NOT NULL REFERENCES learning_roadmaps(id) ON DELETE CASCADE,
                week_number INTEGER NOT NULL CHECK(week_number BETWEEN 1 AND 8),
                task_index INTEGER NOT NULL CHECK(task_index >= 0),
                completed INTEGER NOT NULL CHECK(completed IN (0, 1)),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(roadmap_id, week_number, task_index)
            );
            """
        )


def create_profile(profile: dict) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO student_profiles (name, education, interests_json, skills_json, career_goal)
               VALUES (?, ?, ?, ?, ?)""",
            (profile.get("name", ""), profile["education"], json.dumps(profile["interests"]), json.dumps(profile["skills"]), profile["career_goal"]),
        )
        return get_profile(cursor.lastrowid, connection)


def get_profile(profile_id: int, connection: sqlite3.Connection | None = None) -> dict | None:
    if connection is not None:
        row = connection.execute("SELECT * FROM student_profiles WHERE id = ?", (profile_id,)).fetchone()
        return profile_from_row(row) if row else None
    with get_connection() as db:
        row = db.execute("SELECT * FROM student_profiles WHERE id = ?", (profile_id,)).fetchone()
        return profile_from_row(row) if row else None


def profile_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "education": row["education"],
        "interests": json.loads(row["interests_json"]), "skills": json.loads(row["skills_json"]),
        "career_goal": row["career_goal"], "created_at": row["created_at"],
    }


def save_roadmap(profile_id: int, career_id: str, career_title: str, roadmap: dict, source: str) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO learning_roadmaps (profile_id, career_id, career_title, roadmap_json, source)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(profile_id, career_id) DO UPDATE SET
                 roadmap_json = excluded.roadmap_json, source = excluded.source,
                 created_at = CURRENT_TIMESTAMP
               RETURNING id""",
            (profile_id, career_id, career_title, json.dumps(roadmap), source),
        )
        return get_roadmap(cursor.fetchone()["id"], connection)


def get_roadmap(roadmap_id: int, connection: sqlite3.Connection | None = None) -> dict | None:
    if connection is not None:
        row = connection.execute("SELECT * FROM learning_roadmaps WHERE id = ?", (roadmap_id,)).fetchone()
        return roadmap_from_row(row, connection) if row else None
    with get_connection() as db:
        row = db.execute("SELECT * FROM learning_roadmaps WHERE id = ?", (roadmap_id,)).fetchone()
        return roadmap_from_row(row, db) if row else None


def roadmap_from_row(row: sqlite3.Row, connection: sqlite3.Connection) -> dict:
    roadmap_data = json.loads(row["roadmap_json"])
    progress_rows = connection.execute(
        "SELECT week_number, task_index, completed FROM progress WHERE roadmap_id = ?",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"], "profile_id": row["profile_id"], "career_id": row["career_id"],
        "career_title": row["career_title"], "source": row["source"],
        "created_at": row["created_at"], **roadmap_data,
        "progress": {f"{item['week_number']}:{item['task_index']}": bool(item["completed"]) for item in progress_rows},
    }


def list_roadmaps(profile_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM learning_roadmaps WHERE profile_id = ? ORDER BY id", (profile_id,)
        ).fetchall()
        return [roadmap_from_row(row, connection) for row in rows]


def update_progress(roadmap_id: int, week_number: int, task_index: int, completed: bool) -> dict | None:
    with get_connection() as connection:
        if connection.execute("SELECT 1 FROM learning_roadmaps WHERE id = ?", (roadmap_id,)).fetchone() is None:
            return None
        connection.execute(
            """INSERT INTO progress (roadmap_id, week_number, task_index, completed)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(roadmap_id, week_number, task_index) DO UPDATE SET
                 completed = excluded.completed, updated_at = CURRENT_TIMESTAMP""",
            (roadmap_id, week_number, task_index, int(completed)),
        )
        return get_roadmap(roadmap_id, connection)


def get_dashboard() -> dict:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM student_profiles ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return {"profile": None, "roadmaps": []}
        profile = profile_from_row(row)
        return {"profile": profile, "roadmaps": list_roadmaps(profile["id"])}