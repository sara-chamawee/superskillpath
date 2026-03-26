"""Skill Manager Service — CRUD operations for skills with in-memory storage."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.models.errors import NotFoundError, ValidationError
from src.models.skill import AssessmentCriteria, ChecklistItem, Skill


@dataclass
class CreateSkillInput:
    """Input data for creating a new skill."""

    name: str = ""
    definition: str = ""
    assessment_criteria: list[dict] = field(default_factory=list)


@dataclass
class UpdateSkillInput:
    """Input data for updating an existing skill."""

    name: str = ""
    definition: str = ""
    assessment_criteria: list[dict] = field(default_factory=list)


def _validate_skill_input(
    name: str, definition: str, assessment_criteria: list[dict]
) -> list[dict]:
    """Validate skill input fields and return a list of field errors."""
    errors: list[dict] = []

    if not name or not name.strip():
        errors.append({"field_name": "name", "message": "must not be empty"})

    if not definition or not definition.strip():
        errors.append({"field_name": "definition", "message": "must not be empty"})

    if not assessment_criteria:
        errors.append(
            {
                "field_name": "assessment_criteria",
                "message": "must have at least 1 assessment criteria",
            }
        )
    else:
        for i, criteria in enumerate(assessment_criteria):
            criteria_name = criteria.get("name", "")
            if not criteria_name or not str(criteria_name).strip():
                errors.append(
                    {
                        "field_name": f"assessment_criteria[{i}].name",
                        "message": "must not be empty",
                    }
                )
            checklist_items = criteria.get("checklist_items", [])
            if not checklist_items:
                errors.append(
                    {
                        "field_name": f"assessment_criteria[{i}].checklist_items",
                        "message": "must have at least 1 checklist item",
                    }
                )

    return errors


class SkillManagerService:
    """Manages skill CRUD operations with in-memory dict storage."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def create_skill(self, input: CreateSkillInput) -> Skill:
        """Create a new skill from input data.

        Raises:
            ValidationError: If input data is invalid.
        """
        errors = _validate_skill_input(
            input.name, input.definition, input.assessment_criteria
        )
        if errors:
            raise ValidationError(errors)

        skill_id = uuid4()
        now = datetime.now()

        criteria_list: list[AssessmentCriteria] = []
        for idx, c in enumerate(input.assessment_criteria):
            criteria_id = uuid4()
            items = [
                ChecklistItem(
                    description=item_desc,
                    assessment_criteria_id=criteria_id,
                    order_index=j,
                )
                for j, item_desc in enumerate(c["checklist_items"])
            ]
            criteria_list.append(
                AssessmentCriteria(
                    name=c["name"],
                    skill_id=skill_id,
                    order_index=idx,
                    id=criteria_id,
                    checklist_items=items,
                )
            )

        skill = Skill(
            name=input.name.strip(),
            definition=input.definition.strip(),
            id=skill_id,
            created_at=now,
            updated_at=now,
            assessment_criteria=criteria_list,
        )

        self._skills[str(skill.id)] = skill
        return skill

    def update_skill(self, skill_id: str, input: UpdateSkillInput) -> Skill:
        """Update an existing skill.

        Raises:
            NotFoundError: If skill is not found.
            ValidationError: If input data is invalid.
        """
        if skill_id not in self._skills:
            raise NotFoundError("Skill", skill_id)

        errors = _validate_skill_input(
            input.name, input.definition, input.assessment_criteria
        )
        if errors:
            raise ValidationError(errors)

        skill = self._skills[skill_id]
        skill.name = input.name.strip()
        skill.definition = input.definition.strip()
        skill.updated_at = datetime.now()

        criteria_list: list[AssessmentCriteria] = []
        for idx, c in enumerate(input.assessment_criteria):
            criteria_id = uuid4()
            items = [
                ChecklistItem(
                    description=item_desc,
                    assessment_criteria_id=criteria_id,
                    order_index=j,
                )
                for j, item_desc in enumerate(c["checklist_items"])
            ]
            criteria_list.append(
                AssessmentCriteria(
                    name=c["name"],
                    skill_id=skill.id,
                    order_index=idx,
                    id=criteria_id,
                    checklist_items=items,
                )
            )

        skill.assessment_criteria = criteria_list
        return skill

    def delete_skill(self, skill_id: str) -> None:
        """Delete a skill by ID.

        Raises:
            NotFoundError: If skill is not found.
        """
        if skill_id not in self._skills:
            raise NotFoundError("Skill", skill_id)
        del self._skills[skill_id]

    def get_skill(self, skill_id: str) -> Skill:
        """Get a skill by ID.

        Raises:
            NotFoundError: If skill is not found.
        """
        if skill_id not in self._skills:
            raise NotFoundError("Skill", skill_id)
        return self._skills[skill_id]

    def add_seed_skills(self, skills: list[Skill]) -> None:
        """Bulk add skills from seed data parser."""
        for skill in skills:
            self._skills[str(skill.id)] = skill
