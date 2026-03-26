"""Data models for ChatSession, ChatMessage, LearningPath, and LearningStep."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class ChatMessage:
    """A single message in a chat session."""

    session_id: UUID
    role: str  # "user" or "assistant"
    content: str
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearningStep:
    """A single step in a learning path."""

    learning_path_id: UUID
    order_index: int
    title: str
    description: str
    id: UUID = field(default_factory=uuid4)
    related_checklist_items: list[str] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)


@dataclass
class LearningPath:
    """A learning path generated for a chat session."""

    session_id: UUID
    skill_id: UUID
    id: UUID = field(default_factory=uuid4)
    steps: list[LearningStep] = field(default_factory=list)


@dataclass
class ChatSession:
    """A chat session between a user and the AI for learning a skill."""

    user_id: UUID
    skill_id: UUID
    learning_path: Optional[LearningPath] = None
    current_step: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity_at: datetime = field(default_factory=datetime.now)
    messages: list[ChatMessage] = field(default_factory=list)
