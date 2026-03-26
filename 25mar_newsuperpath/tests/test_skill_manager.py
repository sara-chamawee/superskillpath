"""Tests for the Skill Manager Service."""

import pytest

from src.models.errors import NotFoundError, ValidationError
from src.models.skill import AssessmentCriteria, ChecklistItem, Skill
from src.services.skill_manager import (
    CreateSkillInput,
    SkillManagerService,
    UpdateSkillInput,
)


def _valid_create_input(**overrides) -> CreateSkillInput:
    """Helper to build a valid CreateSkillInput with optional overrides."""
    defaults = {
        "name": "Test Skill",
        "definition": "A test skill definition",
        "assessment_criteria": [
            {"name": "Area 1", "checklist_items": ["Item A", "Item B"]},
        ],
    }
    defaults.update(overrides)
    return CreateSkillInput(**defaults)


def _valid_update_input(**overrides) -> UpdateSkillInput:
    defaults = {
        "name": "Updated Skill",
        "definition": "Updated definition",
        "assessment_criteria": [
            {"name": "Updated Area", "checklist_items": ["Updated Item"]},
        ],
    }
    defaults.update(overrides)
    return UpdateSkillInput(**defaults)


class TestCreateSkill:
    def test_create_valid_skill(self):
        svc = SkillManagerService()
        skill = svc.create_skill(_valid_create_input())

        assert skill.name == "Test Skill"
        assert skill.definition == "A test skill definition"
        assert len(skill.assessment_criteria) == 1
        assert skill.assessment_criteria[0].name == "Area 1"
        assert len(skill.assessment_criteria[0].checklist_items) == 2

    def test_create_skill_stored_and_retrievable(self):
        svc = SkillManagerService()
        created = svc.create_skill(_valid_create_input())
        fetched = svc.get_skill(str(created.id))
        assert fetched is created

    def test_create_skill_empty_name_raises(self):
        svc = SkillManagerService()
        with pytest.raises(ValidationError) as exc_info:
            svc.create_skill(_valid_create_input(name=""))
        assert any(f["field_name"] == "name" for f in exc_info.value.fields)

    def test_create_skill_empty_definition_raises(self):
        svc = SkillManagerService()
        with pytest.raises(ValidationError) as exc_info:
            svc.create_skill(_valid_create_input(definition=""))
        assert any(f["field_name"] == "definition" for f in exc_info.value.fields)

    def test_create_skill_no_criteria_raises(self):
        svc = SkillManagerService()
        with pytest.raises(ValidationError) as exc_info:
            svc.create_skill(_valid_create_input(assessment_criteria=[]))
        assert any(
            "assessment_criteria" in f["field_name"] for f in exc_info.value.fields
        )

    def test_create_skill_criteria_no_checklist_raises(self):
        svc = SkillManagerService()
        with pytest.raises(ValidationError) as exc_info:
            svc.create_skill(
                _valid_create_input(
                    assessment_criteria=[{"name": "Area", "checklist_items": []}]
                )
            )
        assert any("checklist_items" in f["field_name"] for f in exc_info.value.fields)

    def test_create_skill_ids_are_unique(self):
        svc = SkillManagerService()
        s1 = svc.create_skill(_valid_create_input(name="Skill 1"))
        s2 = svc.create_skill(_valid_create_input(name="Skill 2"))
        assert s1.id != s2.id

    def test_create_skill_criteria_linked_to_skill(self):
        svc = SkillManagerService()
        skill = svc.create_skill(_valid_create_input())
        for c in skill.assessment_criteria:
            assert c.skill_id == skill.id

    def test_create_skill_checklist_linked_to_criteria(self):
        svc = SkillManagerService()
        skill = svc.create_skill(_valid_create_input())
        for c in skill.assessment_criteria:
            for item in c.checklist_items:
                assert item.assessment_criteria_id == c.id


class TestUpdateSkill:
    def test_update_skill_reflects_changes(self):
        svc = SkillManagerService()
        created = svc.create_skill(_valid_create_input())
        updated = svc.update_skill(str(created.id), _valid_update_input())

        assert updated.name == "Updated Skill"
        assert updated.definition == "Updated definition"
        assert len(updated.assessment_criteria) == 1
        assert updated.assessment_criteria[0].name == "Updated Area"

    def test_update_nonexistent_skill_raises(self):
        svc = SkillManagerService()
        with pytest.raises(NotFoundError):
            svc.update_skill("nonexistent-id", _valid_update_input())

    def test_update_with_invalid_data_raises(self):
        svc = SkillManagerService()
        created = svc.create_skill(_valid_create_input())
        with pytest.raises(ValidationError):
            svc.update_skill(str(created.id), _valid_update_input(name=""))


class TestDeleteSkill:
    def test_delete_existing_skill(self):
        svc = SkillManagerService()
        created = svc.create_skill(_valid_create_input())
        sid = str(created.id)
        svc.delete_skill(sid)
        with pytest.raises(NotFoundError):
            svc.get_skill(sid)

    def test_delete_nonexistent_skill_raises(self):
        svc = SkillManagerService()
        with pytest.raises(NotFoundError):
            svc.delete_skill("nonexistent-id")


class TestGetSkill:
    def test_get_existing_skill(self):
        svc = SkillManagerService()
        created = svc.create_skill(_valid_create_input())
        fetched = svc.get_skill(str(created.id))
        assert fetched.name == created.name

    def test_get_nonexistent_skill_raises(self):
        svc = SkillManagerService()
        with pytest.raises(NotFoundError):
            svc.get_skill("nonexistent-id")


class TestAddSeedSkills:
    def test_add_seed_skills_bulk(self):
        from uuid import uuid4

        svc = SkillManagerService()
        skill_id = uuid4()
        seed_skill = Skill(
            name="Seed Skill",
            definition="From seed",
            id=skill_id,
            is_from_seed_data=True,
        )
        svc.add_seed_skills([seed_skill])
        fetched = svc.get_skill(str(skill_id))
        assert fetched.name == "Seed Skill"
        assert fetched.is_from_seed_data is True
