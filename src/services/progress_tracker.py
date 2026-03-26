"""Progress Tracker Service — tracks user progress on skill checklists."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.models.skill import Skill
from src.models.user import UserChecklistProgress


@dataclass
class ChecklistItemStatus:
    """Status of a single checklist item for a user."""

    checklist_item_id: str
    description: str
    area_of_measurement: str
    is_completed: bool
    completed_at: Optional[datetime] = None


@dataclass
class SkillProgress:
    """Aggregated progress for a user on a specific skill."""

    user_id: str
    skill_id: str
    skill_name: str
    total_checklist_items: int
    completed_checklist_items: int
    percent_complete: float
    checklist_status: list[ChecklistItemStatus] = field(default_factory=list)
    is_completed: bool = False


class ProgressTrackerService:
    """Tracks user progress on skill checklists using in-memory storage."""

    def __init__(self) -> None:
        # Keyed by "user_id:checklist_item_id"
        self._progress: dict[str, UserChecklistProgress] = {}

    def mark_checklist_item_complete(
        self, user_id: str, checklist_item_id: str
    ) -> None:
        """Mark a checklist item as complete for a user. Idempotent."""
        key = f"{user_id}:{checklist_item_id}"
        existing = self._progress.get(key)
        if existing and existing.is_completed:
            return  # Already complete — idempotent
        self._progress[key] = UserChecklistProgress(
            user_id=user_id,  # type: ignore[arg-type]
            checklist_item_id=checklist_item_id,  # type: ignore[arg-type]
            is_completed=True,
            completed_at=datetime.now(),
        )

    def get_progress(self, user_id: str, skill: Skill) -> SkillProgress:
        """Return progress for a user on a specific skill."""
        statuses: list[ChecklistItemStatus] = []
        completed = 0
        total = 0

        for criteria in skill.assessment_criteria:
            for item in criteria.checklist_items:
                total += 1
                key = f"{user_id}:{str(item.id)}"
                progress = self._progress.get(key)
                is_done = progress.is_completed if progress else False
                done_at = progress.completed_at if progress and is_done else None
                if is_done:
                    completed += 1
                statuses.append(
                    ChecklistItemStatus(
                        checklist_item_id=str(item.id),
                        description=item.description,
                        area_of_measurement=criteria.name,
                        is_completed=is_done,
                        completed_at=done_at,
                    )
                )

        pct = (completed / total) * 100 if total > 0 else 0.0

        return SkillProgress(
            user_id=user_id,
            skill_id=str(skill.id),
            skill_name=skill.name,
            total_checklist_items=total,
            completed_checklist_items=completed,
            percent_complete=pct,
            checklist_status=statuses,
            is_completed=(total > 0 and completed == total),
        )

    def get_all_progress(
        self, user_id: str, skills: list[Skill]
    ) -> list[SkillProgress]:
        """Return progress for all given skills."""
        return [self.get_progress(user_id, skill) for skill in skills]

    def is_skill_completed(self, user_id: str, skill: Skill) -> bool:
        """Return True when all checklist items of the skill are complete."""
        return self.get_progress(user_id, skill).is_completed
