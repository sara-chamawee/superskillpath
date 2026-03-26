"""Tests for the Skill Catalog Service."""

import pytest
from uuid import uuid4

from src.models.course import Course
from src.models.errors import NotFoundError
from src.models.skill import Skill
from src.services.skill_catalog import SkillCatalogService
from src.services.skill_manager import CreateSkillInput, SkillManagerService


def _make_catalog() -> tuple[SkillCatalogService, SkillManagerService]:
    """Create a SkillCatalogService backed by a fresh SkillManagerService."""
    sm = SkillManagerService()
    return SkillCatalogService(sm), sm


def _create_skill(sm: SkillManagerService, name: str = "Test Skill") -> Skill:
    """Helper to create a valid skill via the manager."""
    return sm.create_skill(
        CreateSkillInput(
            name=name,
            definition=f"Definition of {name}",
            assessment_criteria=[
                {"name": "Area 1", "checklist_items": ["Item A", "Item B"]},
            ],
        )
    )


class TestListSkills:
    def test_empty_catalog(self):
        catalog, _ = _make_catalog()
        assert catalog.list_skills() == []

    def test_lists_all_created_skills(self):
        catalog, sm = _make_catalog()
        s1 = _create_skill(sm, "Skill A")
        s2 = _create_skill(sm, "Skill B")
        listed = catalog.list_skills()
        listed_ids = {s.id for s in listed}
        assert s1.id in listed_ids
        assert s2.id in listed_ids
        assert len(listed) == 2

    def test_includes_seed_data_skills(self):
        catalog, sm = _make_catalog()
        seed = Skill(name="Seed", definition="From seed", id=uuid4(), is_from_seed_data=True)
        sm.add_seed_skills([seed])
        created = _create_skill(sm, "Manual")
        listed = catalog.list_skills()
        assert len(listed) == 2


class TestGetSkillDetail:
    def test_returns_full_detail(self):
        catalog, sm = _make_catalog()
        skill = _create_skill(sm)
        detail = catalog.get_skill_detail(str(skill.id))
        assert detail.name == skill.name
        assert len(detail.assessment_criteria) == 1
        assert len(detail.assessment_criteria[0].checklist_items) == 2

    def test_not_found_raises(self):
        catalog, _ = _make_catalog()
        with pytest.raises(NotFoundError):
            catalog.get_skill_detail("nonexistent-id")


class TestSelectSkillsForLearning:
    def test_select_single_skill(self):
        catalog, sm = _make_catalog()
        skill = _create_skill(sm)
        user_id = str(uuid4())
        catalog.select_skills_for_learning(user_id, [str(skill.id)])
        selected = catalog.get_selected_skills(user_id)
        assert len(selected) == 1
        assert selected[0].id == skill.id

    def test_select_multiple_skills(self):
        catalog, sm = _make_catalog()
        s1 = _create_skill(sm, "Skill A")
        s2 = _create_skill(sm, "Skill B")
        user_id = str(uuid4())
        catalog.select_skills_for_learning(user_id, [str(s1.id), str(s2.id)])
        selected = catalog.get_selected_skills(user_id)
        assert len(selected) == 2
        selected_ids = {s.id for s in selected}
        assert s1.id in selected_ids
        assert s2.id in selected_ids

    def test_select_nonexistent_skill_raises(self):
        catalog, sm = _make_catalog()
        _create_skill(sm)
        user_id = str(uuid4())
        with pytest.raises(NotFoundError):
            catalog.select_skills_for_learning(user_id, ["nonexistent-id"])

    def test_get_selected_skills_empty_user(self):
        catalog, _ = _make_catalog()
        assert catalog.get_selected_skills("unknown-user") == []

    def test_selection_overwrites_previous(self):
        catalog, sm = _make_catalog()
        s1 = _create_skill(sm, "Skill A")
        s2 = _create_skill(sm, "Skill B")
        user_id = str(uuid4())
        catalog.select_skills_for_learning(user_id, [str(s1.id)])
        catalog.select_skills_for_learning(user_id, [str(s2.id)])
        selected = catalog.get_selected_skills(user_id)
        assert len(selected) == 1
        assert selected[0].id == s2.id


class TestGetCoursesForSkill:
    def test_no_courses(self):
        catalog, _ = _make_catalog()
        assert catalog.get_courses_for_skill("Unknown Skill") == []

    def test_returns_added_courses(self):
        catalog, sm = _make_catalog()
        skill = _create_skill(sm, "Python Basics")
        course = Course(
            skill_id=skill.id,
            course_code="PY101",
            name="Intro to Python",
            content_provider="Provider A",
            instructor_name="Instructor A",
            duration="1:00:00",
            order_index=0,
        )
        catalog.add_courses({"Python Basics": [course]}, {})
        courses = catalog.get_courses_for_skill("Python Basics")
        assert len(courses) == 1
        assert courses[0].name == "Intro to Python"


class TestAddCourses:
    def test_add_courses_with_metadata(self):
        catalog, sm = _make_catalog()
        skill = _create_skill(sm, "Data Analysis")
        course = Course(
            skill_id=skill.id,
            course_code="DA201",
            name="Data Analysis 101",
            content_provider="Provider B",
            instructor_name="Instructor B",
            duration="2:00:00",
        )
        catalog.add_courses(
            {"Data Analysis": [course]},
            {"Data Analysis": {"assessment_type": "Chat to Assess", "domain": "Data"}},
        )
        # Courses stored
        assert len(catalog.get_courses_for_skill("Data Analysis")) == 1
        # Metadata applied to skill
        detail = catalog.get_skill_detail(str(skill.id))
        assert detail.assessment_type == "Chat to Assess"
        assert detail.domain == "Data"

    def test_add_courses_metadata_no_match(self):
        catalog, sm = _make_catalog()
        _create_skill(sm, "Unrelated Skill")
        catalog.add_courses(
            {"Other Skill": []},
            {"Other Skill": {"domain": "Other"}},
        )
        # No crash, metadata just doesn't apply
        skills = catalog.list_skills()
        assert skills[0].domain is None
