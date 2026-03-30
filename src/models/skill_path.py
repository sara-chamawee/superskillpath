"""Data models for Admin Skill Path Template management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class PathItem:
    """A learning content item within a SkillPathTemplate."""

    title: str
    item_type: str  # "fixed", "open"
    content_type: str  # "material", "quiz", "todo", "simulation"
    learning_type: str  # "formal", "social", "experiential"
    order: int = 0
    material_id: Optional[str] = None
    estimated_minutes: int = 0
    badge_level_order: int = 1
    area_index: Optional[int] = None
    required: bool = True
    ai_generated: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass
class PathCriteria:
    """Assessment criteria for a BadgeLevel."""

    criteria_type: str
    value: float
    badge_level_order: int = 1
    id: UUID = field(default_factory=uuid4)


@dataclass
class BadgeLevel:
    """A badge level within a SkillPathTemplate (1-3 levels)."""

    name: str
    order: int
    description: str = ""
    content_provider: str = ""
    image: Optional[str] = None
    criteria: list[PathCriteria] = field(default_factory=list)
    areas: list[dict] = field(default_factory=list)  # [{name, checklist_items}]
    id: UUID = field(default_factory=uuid4)


VALID_ITEM_TYPES = {"fixed", "open"}
VALID_CONTENT_TYPES = {"material", "quiz", "todo", "simulation"}
VALID_LEARNING_TYPES = {"formal", "social", "experiential"}
VALID_CRITERIA_TYPES = {
    "min_hours", "class_attendance", "quiz_score", "completion_rate",
    "project", "coaching", "todo_list", "skill_acquired",
    "competency", "offline_learning",
}
PERCENTAGE_CRITERIA = {"quiz_score", "completion_rate"}
VALID_STATUSES = {"draft", "published", "archived"}
VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class SkillPathTemplate:
    """Main template for an admin-created Skill Path."""

    title: str
    skill_name: str
    description: str = ""
    status: str = "draft"
    created_by: str = ""
    version: int = 1
    cover_image: Optional[str] = None
    items: list[PathItem] = field(default_factory=list)
    badge_levels: list[BadgeLevel] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    datetime_create: datetime = field(default_factory=datetime.now)
    datetime_update: datetime = field(default_factory=datetime.now)


@dataclass
class Enrollment:
    """A learner's enrollment in a SkillPathTemplate."""

    template_id: UUID
    learner_name: str
    status: str = "active"  # "active", "completed", "dropped"
    total_hours: float = 0.0
    items_completed: int = 0
    items_total: int = 0
    avg_quiz_score: float = 0.0
    enrolled_at: datetime = field(default_factory=datetime.now)
    id: UUID = field(default_factory=uuid4)
    plan_items: list[dict] = field(default_factory=list)
    quiz_attempts: list[dict] = field(default_factory=list)
    submissions: list[dict] = field(default_factory=list)
    nudges: list[dict] = field(default_factory=list)


@dataclass
class AuditLog:
    """Audit log entry for important changes."""

    actor: str
    action: str  # "publish", "archive", "update"
    target_type: str
    target_id: str
    changes_summary: str = ""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TokenUsageLog:
    """Log entry for AI token usage."""

    module_type: str
    request_tokens: int = 0
    response_tokens: int = 0
    total_tokens: int = 0
    response_ms: float = 0.0
    is_error: bool = False
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SafetyViolationLog:
    """Log entry for content safety violations."""

    content_type: str
    original_content: str
    violation_type: str
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
