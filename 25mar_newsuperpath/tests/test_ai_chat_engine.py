"""Tests for AIChatEngineService — covers tasks 8.1, 8.2, 8.3, 8.4."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.models.skill import AssessmentCriteria, ChecklistItem, Skill
from src.models.course import Course
from src.services.ai_chat_engine import AIChatEngineService, ChatResponse, StepType
from src.services.progress_tracker import ProgressTrackerService
from src.services.skill_catalog import SkillCatalogService
from src.services.skill_manager import SkillManagerService, CreateSkillInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_engine_with_skill(
    skill_name: str = "Test Skill",
    skill_definition: str = "A test skill definition",
    areas: list[dict] | None = None,
) -> tuple[AIChatEngineService, SkillCatalogService, ProgressTrackerService, str]:
    """Create an engine with a single skill and return (engine, catalog, tracker, skill_id)."""
    if areas is None:
        areas = [
            {"name": "Area 1", "checklist_items": ["Item A", "Item B"]},
            {"name": "Area 2", "checklist_items": ["Item C"]},
        ]

    sm = SkillManagerService()
    skill = sm.create_skill(CreateSkillInput(
        name=skill_name,
        definition=skill_definition,
        assessment_criteria=areas,
    ))
    catalog = SkillCatalogService(sm)
    tracker = ProgressTrackerService()
    engine = AIChatEngineService(catalog, tracker)
    return engine, catalog, tracker, str(skill.id)


# ---------------------------------------------------------------------------
# 8.1 — Chat Session Management
# ---------------------------------------------------------------------------

class TestStartSession:
    """start_session creates a ChatSession with a LearningPath."""

    def test_creates_session_with_learning_path(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        assert session is not None
        assert session.learning_path is not None
        assert str(session.user_id) == "user-1"
        assert str(session.skill_id) == skill_id

    def test_learning_path_covers_all_checklist_items(self) -> None:
        engine, catalog, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        skill = catalog.get_skill_detail(skill_id)
        all_item_ids = {
            str(item.id)
            for criteria in skill.assessment_criteria
            for item in criteria.checklist_items
        }

        path_item_ids: set[str] = set()
        for step in session.learning_path.steps:
            path_item_ids.update(step.related_checklist_items)

        assert path_item_ids == all_item_ids

    def test_learning_path_has_step_per_area(self) -> None:
        engine, catalog, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        skill = catalog.get_skill_detail(skill_id)
        assert len(session.learning_path.steps) == len(skill.assessment_criteria)

    def test_current_step_starts_at_zero(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)
        assert session.current_step == 0

    def test_initial_message_is_assistant_introduction(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        assert len(session.messages) == 1
        msg = session.messages[0]
        assert msg.role == "assistant"
        assert "Test Skill" in msg.content

    def test_multiple_skills_create_separate_sessions(self) -> None:
        sm = SkillManagerService()
        s1 = sm.create_skill(CreateSkillInput(
            name="Skill A",
            definition="Def A",
            assessment_criteria=[{"name": "Area", "checklist_items": ["X"]}],
        ))
        s2 = sm.create_skill(CreateSkillInput(
            name="Skill B",
            definition="Def B",
            assessment_criteria=[{"name": "Area", "checklist_items": ["Y"]}],
        ))
        catalog = SkillCatalogService(sm)
        tracker = ProgressTrackerService()
        engine = AIChatEngineService(catalog, tracker)

        sess1 = engine.start_session("user-1", str(s1.id))
        sess2 = engine.start_session("user-1", str(s2.id))

        assert str(sess1.id) != str(sess2.id)
        assert str(sess1.skill_id) == str(s1.id)
        assert str(sess2.skill_id) == str(s2.id)


# ---------------------------------------------------------------------------
# 8.2 — 7-Step Learning Flow
# ---------------------------------------------------------------------------

class TestSendMessage:
    """send_message drives the 7-step learning flow."""

    def test_returns_chat_response(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)
        resp = engine.send_message(str(session.id), "Hello")

        assert isinstance(resp, ChatResponse)
        assert resp.message.role == "assistant"

    def test_step_progression_intro_to_baseline(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)
        assert session.current_step == StepType.INTRODUCTION.value

        engine.send_message(str(session.id), "Ready!")
        assert session.current_step == StepType.BASELINE_ASSESSMENT.value

    def test_step_progression_baseline_to_plan(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        engine.send_message(str(session.id), "Ready!")  # → BASELINE
        engine.send_message(str(session.id), "I have some experience")  # → PLAN
        assert session.current_step == StepType.PERSONALIZED_PLAN.value

    def test_step_progression_through_content_practice_assessment(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        engine.send_message(str(session.id), "Ready!")  # → BASELINE
        engine.send_message(str(session.id), "Some exp")  # → PLAN
        engine.send_message(str(session.id), "Let's go")  # → CONTENT_DELIVERY
        assert session.current_step == StepType.CONTENT_DELIVERY.value

        engine.send_message(str(session.id), "Got it")  # → PRACTICE
        assert session.current_step == StepType.PRACTICE.value

        resp = engine.send_message(str(session.id), "Done")  # → ASSESSMENT
        assert session.current_step == StepType.ASSESSMENT.value
        # Should have completed checklist items for Area 1
        assert len(resp.completed_checklist_items) > 0

    def test_area_loop_moves_to_next_area(self) -> None:
        """After assessment of area 1, should loop back to content delivery for area 2."""
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        # Walk through steps for area 1
        engine.send_message(str(session.id), "Ready!")       # → BASELINE
        engine.send_message(str(session.id), "Some exp")     # → PLAN
        engine.send_message(str(session.id), "Let's go")     # → CONTENT (area 0)
        engine.send_message(str(session.id), "Got it")       # → PRACTICE (area 0)
        engine.send_message(str(session.id), "Done")         # → ASSESSMENT (area 0)

        # After assessment, respond to move to next area
        engine.send_message(str(session.id), "Next")         # → CONTENT (area 1)
        assert session.current_step == StepType.CONTENT_DELIVERY.value

    def test_wrap_up_after_all_areas(self) -> None:
        """After all areas assessed, should reach WRAP_UP."""
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        # Area 1 flow
        engine.send_message(str(session.id), "Ready!")
        engine.send_message(str(session.id), "Exp")
        engine.send_message(str(session.id), "Go")
        engine.send_message(str(session.id), "Ok")
        engine.send_message(str(session.id), "Done")

        # Area 2 flow (loops back from assessment)
        engine.send_message(str(session.id), "Next")         # → CONTENT (area 1)
        engine.send_message(str(session.id), "Ok")           # → PRACTICE (area 1)
        engine.send_message(str(session.id), "Done")         # → ASSESSMENT (area 1)

        # After last area assessment → WRAP_UP
        engine.send_message(str(session.id), "Finish")       # → WRAP_UP
        assert session.current_step == StepType.WRAP_UP.value

    def test_session_history_tracks_all_messages(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        engine.send_message(str(session.id), "Hello")
        engine.send_message(str(session.id), "World")

        history = engine.get_session_history(str(session.id))
        # 1 intro + 2 user + 2 assistant = 5
        assert len(history) == 5
        assert history[0].role == "assistant"  # intro
        assert history[1].role == "user"
        assert history[2].role == "assistant"
        assert history[3].role == "user"
        assert history[4].role == "assistant"


# ---------------------------------------------------------------------------
# 8.3 — Course Recommendation
# ---------------------------------------------------------------------------

class TestCourseRecommendation:
    """Content delivery step includes course recommendations."""

    def test_content_delivery_includes_courses(self) -> None:
        engine, catalog, _, skill_id = _create_engine_with_skill(
            skill_name="My Skill"
        )
        # Add courses to catalog
        from uuid import uuid4
        courses = [
            Course(
                skill_id=uuid4(),
                course_code="C001",
                name="Intro Course",
                content_provider="Provider A",
                instructor_name="Dr. Smith",
                duration="1:30:00",
            ),
        ]
        catalog._courses["My Skill"] = courses

        session = engine.start_session("user-1", skill_id)
        engine.send_message(str(session.id), "Ready!")       # → BASELINE
        engine.send_message(str(session.id), "Some exp")     # → PLAN
        resp = engine.send_message(str(session.id), "Go")    # → CONTENT

        assert "Intro Course" in resp.message.content
        assert "Dr. Smith" in resp.message.content
        assert "1:30:00" in resp.message.content


# ---------------------------------------------------------------------------
# 8.4 — Inactivity Nudge
# ---------------------------------------------------------------------------

class TestInactivityNudge:
    """check_inactivity returns nudge when session is idle."""

    def test_no_nudge_when_active(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        result = engine.check_inactivity(str(session.id), threshold_minutes=30)
        assert result is None

    def test_nudge_when_inactive(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        # Simulate inactivity by setting last_activity_at in the past
        session.last_activity_at = datetime.now() - timedelta(minutes=45)

        result = engine.check_inactivity(str(session.id), threshold_minutes=30)
        assert result is not None
        assert "Test Skill" in result

    def test_nudge_respects_custom_threshold(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        session.last_activity_at = datetime.now() - timedelta(minutes=10)

        # 5-minute threshold → should nudge
        assert engine.check_inactivity(str(session.id), threshold_minutes=5) is not None
        # 15-minute threshold → should not nudge
        assert engine.check_inactivity(str(session.id), threshold_minutes=15) is None


# ---------------------------------------------------------------------------
# Additional: get_learning_path and summarize_progress
# ---------------------------------------------------------------------------

class TestLearningPathAndProgress:
    """get_learning_path and summarize_progress work correctly."""

    def test_get_learning_path(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        path = engine.get_learning_path(str(session.id))
        assert path is not None
        assert len(path.steps) == 2  # 2 areas

    def test_summarize_progress_initial(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        summary = engine.summarize_progress(str(session.id))
        assert summary["total_checklist_items"] == 3
        assert summary["completed_checklist_items"] == 0
        assert summary["percent_complete"] == 0.0
        assert summary["is_completed"] is False

    def test_summarize_progress_after_assessment(self) -> None:
        engine, _, _, skill_id = _create_engine_with_skill()
        session = engine.start_session("user-1", skill_id)

        # Walk through area 1
        engine.send_message(str(session.id), "Ready!")
        engine.send_message(str(session.id), "Exp")
        engine.send_message(str(session.id), "Go")
        engine.send_message(str(session.id), "Ok")
        engine.send_message(str(session.id), "Done")  # Assessment marks area 1 items

        summary = engine.summarize_progress(str(session.id))
        # Area 1 has 2 items out of 3 total
        assert summary["completed_checklist_items"] == 2
        assert summary["total_checklist_items"] == 3


class TestNotFoundErrors:
    """Operations on non-existent sessions raise NotFoundError."""

    def test_send_message_not_found(self) -> None:
        engine, _, _, _ = _create_engine_with_skill()
        from src.models.errors import NotFoundError
        with pytest.raises(NotFoundError):
            engine.send_message("nonexistent", "Hello")

    def test_get_history_not_found(self) -> None:
        engine, _, _, _ = _create_engine_with_skill()
        from src.models.errors import NotFoundError
        with pytest.raises(NotFoundError):
            engine.get_session_history("nonexistent")

    def test_get_learning_path_not_found(self) -> None:
        engine, _, _, _ = _create_engine_with_skill()
        from src.models.errors import NotFoundError
        with pytest.raises(NotFoundError):
            engine.get_learning_path("nonexistent")

    def test_check_inactivity_not_found(self) -> None:
        engine, _, _, _ = _create_engine_with_skill()
        from src.models.errors import NotFoundError
        with pytest.raises(NotFoundError):
            engine.check_inactivity("nonexistent")
