"""Data model for Course."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Course:
    """A course linked to a skill."""

    skill_id: UUID
    course_code: str
    name: str
    content_provider: str
    instructor_name: str
    duration: str
    order_index: int = 0
    id: UUID = field(default_factory=uuid4)
