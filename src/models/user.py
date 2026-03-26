"""Data models for User, UserSelectedSkill, and UserChecklistProgress."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class User:
    """A system user."""

    name: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserSelectedSkill:
    """A skill selected by a user for learning."""

    user_id: UUID
    skill_id: UUID
    id: UUID = field(default_factory=uuid4)
    selected_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserChecklistProgress:
    """Tracks a user's progress on a single checklist item."""

    user_id: UUID
    checklist_item_id: UUID
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    id: UUID = field(default_factory=uuid4)
