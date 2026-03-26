"""Data models for Skill, AssessmentCriteria, and ChecklistItem."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class ChecklistItem:
    """A single checklist item under an assessment criteria."""

    description: str
    assessment_criteria_id: UUID
    order_index: int = 0
    id: UUID = field(default_factory=uuid4)


@dataclass
class AssessmentCriteria:
    """An assessment criteria for a skill, containing checklist items."""

    name: str
    skill_id: UUID
    order_index: int = 0
    id: UUID = field(default_factory=uuid4)
    checklist_items: list[ChecklistItem] = field(default_factory=list)


@dataclass
class Skill:
    """A skill with assessment criteria and checklist items."""

    name: str
    definition: str
    domain: Optional[str] = None
    assessment_type: Optional[str] = None  # "Submit Assignment File" or "Chat to Assess"
    todo_list_url: Optional[str] = None
    is_from_seed_data: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    assessment_criteria: list[AssessmentCriteria] = field(default_factory=list)
