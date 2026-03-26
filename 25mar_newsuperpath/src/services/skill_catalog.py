"""Skill Catalog Service — wraps SkillManagerService with catalog/selection features."""

from datetime import datetime
from uuid import uuid4

from src.models.course import Course
from src.models.errors import NotFoundError
from src.models.skill import Skill
from src.models.user import UserSelectedSkill
from src.services.skill_manager import SkillManagerService


class SkillCatalogService:
    """Provides catalog browsing, skill detail, user selection, and course lookup."""

    def __init__(self, skill_manager: SkillManagerService) -> None:
        self._skill_manager = skill_manager
        self._user_selections: dict[str, list[UserSelectedSkill]] = {}
        self._courses: dict[str, list[Course]] = {}

    def list_skills(self) -> list[Skill]:
        """Return all skills from the skill manager's internal storage."""
        return list(self._skill_manager._skills.values())

    def get_skill_detail(self, skill_id: str) -> Skill:
        """Return full skill detail including AssessmentCriteria and ChecklistItems.

        Raises:
            NotFoundError: If skill_id is not found.
        """
        return self._skill_manager.get_skill(skill_id)

    def select_skills_for_learning(
        self, user_id: str, skill_ids: list[str]
    ) -> None:
        """Store selected skills for a user.

        Validates all skill_ids exist before storing.

        Raises:
            NotFoundError: If any skill_id is not found.
        """
        # Validate all skill_ids exist first
        for sid in skill_ids:
            self._skill_manager.get_skill(sid)

        selections = [
            UserSelectedSkill(
                user_id=user_id,  # type: ignore[arg-type]
                skill_id=sid,  # type: ignore[arg-type]
                id=uuid4(),
                selected_at=datetime.now(),
            )
            for sid in skill_ids
        ]
        self._user_selections[user_id] = selections

    def get_selected_skills(self, user_id: str) -> list[Skill]:
        """Return the skills a user has selected for learning."""
        selections = self._user_selections.get(user_id, [])
        skills: list[Skill] = []
        for sel in selections:
            try:
                skill = self._skill_manager.get_skill(str(sel.skill_id))
                skills.append(skill)
            except NotFoundError:
                # Skill was deleted after selection — skip silently
                pass
        return skills

    def get_courses_for_skill(self, skill_name: str) -> list[Course]:
        """Return courses linked to a skill name."""
        return self._courses.get(skill_name, [])

    def add_courses(
        self,
        skill_courses: dict[str, list[Course]],
        skill_metadata: dict,
    ) -> None:
        """Bulk add course data and metadata, linking courses to skills by name.

        Args:
            skill_courses: Mapping of skill_name -> list of Course objects.
            skill_metadata: Mapping of skill_name -> dict with optional keys
                            'assessment_type', 'domain', 'todo_list_url'.
        """
        for skill_name, courses in skill_courses.items():
            self._courses[skill_name] = courses

        # Apply metadata to matching skills
        for skill in self.list_skills():
            meta = skill_metadata.get(skill.name)
            if meta:
                if "assessment_type" in meta:
                    skill.assessment_type = meta["assessment_type"]
                if "domain" in meta:
                    skill.domain = meta["domain"]
                if "todo_list_url" in meta:
                    skill.todo_list_url = meta["todo_list_url"]
