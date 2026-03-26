"""Custom error classes for validation and not-found errors."""


class ValidationError(Exception):
    """Raised when input data fails validation."""

    def __init__(self, fields: list[dict]) -> None:
        """Initialize with a list of field errors.

        Args:
            fields: List of dicts with 'field_name' and 'message' keys.
        """
        self.fields = fields
        messages = [f"{f['field_name']}: {f['message']}" for f in fields]
        super().__init__(f"Validation failed: {'; '.join(messages)}")


class NotFoundError(Exception):
    """Raised when a requested entity is not found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        """Initialize with entity type and ID.

        Args:
            entity_type: The type of entity (e.g., 'Skill', 'User').
            entity_id: The ID that was not found.
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id '{entity_id}' not found")
