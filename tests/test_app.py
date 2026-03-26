"""Tests for the App entry point."""

import os
import tempfile

import pytest

from src.app import App
from src.services.skill_manager import CreateSkillInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_SKILLS_MD = """\
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| --- | --- | --- | --- |
| Test Skill | A test skill definition | 1\\. Analysis | Analyse data\\- Interpret results |
|  |  | 2\\. Application | Apply methods\\- Validate outcomes |
"""

SAMPLE_COURSES_MD = """\
| No. | NEW Domain | OLD Domain | Skill | Course ID | Course Name | Content Provider | Instructor Name | Duration | col9 | col10 | col11 | To Do List Type | To-Do | col14 | col15 | col16 | col17 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Tech | OldTech | Test Skill | | | | | 2:00:00 | | | | Chat to Assess | | | | | |
| | | | | C001 | Intro Course | Provider A | Dr. Smith | 1:00:00 | | | | | | | | | |
| | | | | C002 | Advanced Course | Provider B | Prof. Lee | 1:00:00 | | | | | | | | | |
"""


def _write_temp(content: str) -> str:
    """Write content to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAppWithoutSeedFiles:
    """App created without any seed files should start with an empty catalog."""

    def test_empty_catalog(self):
        app = App()
        assert app.get_skill_catalog().list_skills() == []

    def test_services_are_available(self):
        app = App()
        assert app.get_skill_manager() is not None
        assert app.get_skill_catalog() is not None
        assert app.get_progress_tracker() is not None
        assert app.get_chat_engine() is not None

    def test_missing_file_graceful(self):
        """Passing a non-existent file should not raise — just log a warning."""
        app = App(skills_file="/tmp/does_not_exist.md")
        assert app.get_skill_catalog().list_skills() == []


class TestAppWithSeedData:
    """App created with seed data files should populate the catalog."""

    def test_seed_skills_loaded(self):
        skills_path = _write_temp(SAMPLE_SKILLS_MD)
        try:
            app = App(skills_file=skills_path)
            skills = app.get_skill_catalog().list_skills()
            assert len(skills) == 1
            assert skills[0].name == "Test Skill"
            assert len(skills[0].assessment_criteria) == 2
        finally:
            os.unlink(skills_path)

    def test_seed_courses_loaded(self):
        skills_path = _write_temp(SAMPLE_SKILLS_MD)
        courses_path = _write_temp(SAMPLE_COURSES_MD)
        try:
            app = App(skills_file=skills_path, courses_file=courses_path)
            courses = app.get_skill_catalog().get_courses_for_skill("Test Skill")
            assert len(courses) == 2
            assert courses[0].name == "Intro Course"

            # Metadata should be applied to the skill
            skill = app.get_skill_catalog().list_skills()[0]
            assert skill.assessment_type == "Chat to Assess"
            assert skill.domain == "Tech"
        finally:
            os.unlink(skills_path)
            os.unlink(courses_path)


class TestFullFlow:
    """End-to-end: seed → catalog → select skill → start chat → send message → check progress."""

    def test_full_learning_flow(self):
        skills_path = _write_temp(SAMPLE_SKILLS_MD)
        try:
            app = App(skills_file=skills_path)

            # 1. Catalog has the seeded skill
            skills = app.get_skill_catalog().list_skills()
            assert len(skills) == 1
            skill = skills[0]
            skill_id = str(skill.id)

            # 2. Select skill for learning
            user_id = "user-1"
            app.get_skill_catalog().select_skills_for_learning(user_id, [skill_id])
            selected = app.get_skill_catalog().get_selected_skills(user_id)
            assert len(selected) == 1

            # 3. Start learning — creates a chat session
            session = app.start_learning(user_id, skill_id)
            session_id = str(session.id)
            assert session.current_step == 0
            assert len(session.messages) == 1  # intro message

            # 4. Send messages to advance through the flow
            # Step 0→1: user responds to intro → baseline assessment
            resp = app.send_chat(session_id, "พร้อมครับ")
            assert resp.message.role == "assistant"

            # Step 1→2: user answers baseline → personalized plan
            resp = app.send_chat(session_id, "มีประสบการณ์บ้างครับ")

            # Step 2→3: user acknowledges plan → content delivery (area 0)
            resp = app.send_chat(session_id, "เริ่มเลยครับ")

            # Step 3→4: content → practice (area 0)
            resp = app.send_chat(session_id, "เข้าใจแล้วครับ")

            # Step 4→5: practice → assessment (area 0)
            resp = app.send_chat(session_id, "ทำเสร็จแล้วครับ")
            assert len(resp.completed_checklist_items) > 0

            # 5. Check progress after first area
            progress = app.get_progress_tracker().get_progress(user_id, skill)
            assert progress.completed_checklist_items > 0
            assert progress.percent_complete > 0

            # Step 5→3: assessment done, loop to content delivery (area 1)
            resp = app.send_chat(session_id, "ไปต่อเลยครับ")

            # Step 3→4: content → practice (area 1)
            resp = app.send_chat(session_id, "เข้าใจแล้วครับ")

            # Step 4→5: practice → assessment (area 1)
            resp = app.send_chat(session_id, "ทำเสร็จแล้วครับ")
            assert len(resp.completed_checklist_items) > 0

            # Step 5→6: all areas done → wrap up
            resp = app.send_chat(session_id, "สรุปเลยครับ")

            # 6. Final progress — should be 100%
            progress = app.get_progress_tracker().get_progress(user_id, skill)
            assert progress.is_completed is True
            assert progress.percent_complete == 100.0

        finally:
            os.unlink(skills_path)

    def test_manually_created_skill_flow(self):
        """Create a skill via SkillManager, then learn it through chat."""
        app = App()

        # Create skill manually
        skill = app.get_skill_manager().create_skill(
            CreateSkillInput(
                name="Custom Skill",
                definition="A custom skill for testing",
                assessment_criteria=[
                    {
                        "name": "Core Concepts",
                        "checklist_items": ["Understand basics", "Apply concepts"],
                    }
                ],
            )
        )
        skill_id = str(skill.id)

        # Verify it appears in catalog
        catalog_skills = app.get_skill_catalog().list_skills()
        assert any(s.name == "Custom Skill" for s in catalog_skills)

        # Start learning
        user_id = "user-2"
        session = app.start_learning(user_id, skill_id)
        assert session is not None
        assert len(session.messages) == 1
