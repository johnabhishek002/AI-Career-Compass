import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_service
import career_data
import database
import main
import requests
import tools


class CareerDataTests(unittest.TestCase):
    def test_matching_is_deterministic_and_exposes_skill_gaps(self):
        profile = {
            "education": "Computer science student",
            "interests": ["web design", "visual design"],
            "skills": ["javascript", "html", "css"],
            "goals": "Build accessible web applications",
        }
        first = career_data.recommend_careers(profile)
        second = career_data.recommend_careers(profile)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["career_id"], "web-developer")
        self.assertIn("react", first[0]["missing_skills"])
        self.assertIn("javascript", first[0]["matched_skills"])

    def test_model_default_uses_only_installed_models(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ai_service.resolve_model(["llama3.2:3b", "gemma3:1b"]), "llama3.2:3b")
            self.assertEqual(ai_service.resolve_model(["llama3.2:1b", "llama3.2:3b"]), "llama3.2:1b")

    def test_uninstalled_configured_model_is_rejected(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "missing:1b"}):
            with self.assertRaises(ai_service.OllamaError):
                ai_service.resolve_model(["llama3.2:3b"])

    def test_health_reports_installed_models_when_configuration_is_invalid(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "missing:1b"}):
            with patch.object(tools, "installed_models", return_value=["llama3.2:3b"]):
                status = ai_service.ollama_status()
        self.assertFalse(status["available"])
        self.assertEqual(status["installed_models"], ["llama3.2:3b"])
        self.assertIn("not installed", status["message"])

    def test_remote_ollama_host_is_rejected_for_privacy(self):
        with patch.object(tools, "OLLAMA_URL", "https://example.com"):
            with self.assertRaises(ai_service.OllamaError):
                ai_service.ensure_local_ollama_url()

    def test_model_response_requires_eight_ordered_weeks(self):
        invalid = '{"careers":[{"career_id":"web-developer","fit_explanation":"A reasonable fit because you enjoy building accessible web interfaces.","gap_explanation":"React is not listed in the profile yet, so it is a useful learning target.","weeks":[]}]}'
        with self.assertRaises(ai_service.OllamaError):
            ai_service.parse_guidance(invalid, {"web-developer"})

    def test_malformed_json_is_rejected(self):
        with self.assertRaises(ai_service.OllamaError):
            ai_service.parse_guidance("{not json", {"web-developer"})

    def test_ollama_connection_failure_is_reported(self):
        with patch.object(tools.requests, "get", side_effect=requests.ConnectionError("offline")):
            with self.assertRaisesRegex(ai_service.OllamaError, "Ollama is unavailable"):
                ai_service.installed_models()

    def test_ollama_timeout_is_reported(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llama3.2:3b"}):
            with patch.object(tools, "installed_models", return_value=["llama3.2:3b"]):
                with patch.object(tools.requests, "post", side_effect=requests.Timeout):
                    with self.assertRaisesRegex(ai_service.OllamaError, "took too long"):
                        ai_service.generate_guidance(
                            {"education": "Student", "interests": ["web design"], "skills": [], "career_goal": "Build websites"},
                            [{"career_id": "web-developer", "title": "Web Developer", "matched_interests": [], "matched_skills": [], "missing_skills": [], "projects": []}],
                        )


class ApiWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "test.db"
        database.initialize_database()

    def tearDown(self):
        database.DB_PATH = self.old_path
        self.temp_dir.cleanup()

    def make_profile(self):
        return main.create_student_profile(main.StudentProfileInput(
            name="Casey",
            education="Second year computer science",
            interests=["web design", "visual design"],
            skills=["javascript", "html", "css"],
            career_goal="Build accessible web applications",
        ))

    def test_profile_recommendation_demo_roadmap_and_progress_persist(self):
        profile = self.make_profile()
        with patch.object(main.ai_service, "generate_guidance", side_effect=ai_service.OllamaError("Ollama offline")):
            result = main.recommend(main.RecommendationRequest(profile_id=profile["id"], limit=3))

        self.assertEqual(result["source"], "demo")
        self.assertIn("demo", result["notice"].lower())
        self.assertEqual(result["careers"][0]["career_id"], "web-developer")
        roadmap = result["roadmaps"][0]
        self.assertEqual(len(roadmap["weeks"]), 8)
        self.assertEqual(database.get_roadmap(roadmap["id"])["source"], "demo")

        updated = main.update_learning_progress(main.ProgressRequest(
            roadmap_id=roadmap["id"], week_number=1, task_index=0, completed=True,
        ))
        self.assertTrue(updated["roadmap"]["progress"]["1:0"])
        dashboard = main.dashboard()
        self.assertEqual(dashboard["profile"]["id"], profile["id"])
        self.assertTrue(dashboard["roadmaps"][0]["progress"]["1:0"])

    def test_progress_rejects_nonexistent_task(self):
        profile = self.make_profile()
        recommendation = career_data.recommend_careers(main.profile_as_match_input(profile))[0]
        plan = ai_service.demo_guidance([recommendation])["careers"][0]
        roadmap = database.save_roadmap(
            profile["id"], recommendation["career_id"], recommendation["title"],
            {"fit_explanation": plan["fit_explanation"], "gap_explanation": plan["gap_explanation"], "weeks": plan["weeks"], "projects": recommendation["projects"]}, "demo",
        )
        with self.assertRaises(Exception) as error:
            main.update_learning_progress(main.ProgressRequest(
                roadmap_id=roadmap["id"], week_number=1, task_index=3, completed=True,
            ))
        self.assertIn("Task index", str(error.exception))

    def test_skill_gap_endpoint_returns_curated_gap(self):
        profile = self.make_profile()
        result = main.analyze_skill_gaps(main.SkillGapRequest(
            profile_id=profile["id"], career_id="web-developer",
        ))
        self.assertIn("react", result["missing_skills"])

if __name__ == "__main__":
    unittest.main()