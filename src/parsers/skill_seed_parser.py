"""Parser for Skills Name.md seed data file.

Reads a Markdown table with columns:
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |

Handles multi-row merging where rows with empty Skills Name are additional
Areas of Measurement for the previous skill.
"""

import logging
import re
from dataclasses import dataclass, field
from uuid import uuid4

from src.models.skill import AssessmentCriteria, ChecklistItem, Skill

logger = logging.getLogger(__name__)


@dataclass
class SkippedRow:
    """A row that was skipped during parsing."""

    row_index: int
    reason: str


@dataclass
class ParseResult:
    """Result of parsing the seed data file."""

    skills: list[Skill] = field(default_factory=list)
    skipped_rows: list[SkippedRow] = field(default_factory=list)


def _is_separator_row(row: str) -> bool:
    """Check if a row is the Markdown table separator (e.g. | ----- | ----- |)."""
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return all(re.match(r"^-+$", cell) for cell in cells if cell)


def _parse_cells(row: str) -> list[str]:
    """Split a pipe-delimited row into cell values, stripping whitespace."""
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _strip_area_number_prefix(area_name: str) -> str:
    """Strip number prefix like '1\\.' or '2\\.' from area of measurement names.

    Handles both escaped backslash-dot (1\\.) and plain dot (1.) formats.
    """
    # Match patterns like "1\." or "2\." (with backslash) or "1." "2." (plain)
    return re.sub(r"^\d+\\?\.\s*", "", area_name).strip()


def _parse_checklist_items(checklist_text: str, criteria_id) -> list[ChecklistItem]:
    """Parse checklist items separated by \\- from a cell.

    Items are separated by '\\-' (backslash-dash) within the cell text.
    """
    # Split on \- pattern (the literal backslash-dash in the markdown)
    # The text contains "\\-" as separator between items
    parts = re.split(r"\\-\s*", checklist_text)
    items = []
    order = 0
    for part in parts:
        text = part.strip()
        if text:
            items.append(
                ChecklistItem(
                    description=text,
                    assessment_criteria_id=criteria_id,
                    order_index=order,
                    id=uuid4(),
                )
            )
            order += 1
    return items


def parse(file_content: str) -> ParseResult:
    """Parse the Skills Name.md file content into Skill objects.

    Args:
        file_content: The raw text content of the Skills Name.md file.

    Returns:
        ParseResult with parsed skills and any skipped rows.
    """
    result = ParseResult()
    lines = file_content.strip().split("\n")

    # Filter to only table rows (lines containing pipes)
    table_rows = [line for line in lines if "|" in line]

    if not table_rows:
        return result

    # Skip header row and separator row
    data_rows: list[tuple[int, str]] = []
    for i, row in enumerate(table_rows):
        if i == 0:
            # Header row — skip
            continue
        if _is_separator_row(row):
            continue
        data_rows.append((i, row))

    current_skill: Skill | None = None
    area_order = 0

    for row_index, row in data_rows:
        cells = _parse_cells(row)

        # Ensure we have at least 4 columns
        if len(cells) < 4:
            result.skipped_rows.append(
                SkippedRow(row_index=row_index, reason="Row has fewer than 4 columns")
            )
            continue

        skill_name = cells[0].strip()
        skill_definition = cells[1].strip()
        area_of_measurement = cells[2].strip()
        checklist_text = cells[3].strip()

        # Check if this row has required data (area + checklist)
        if not area_of_measurement or not checklist_text:
            reason_parts = []
            if not area_of_measurement:
                reason_parts.append("missing Areas of Measurement")
            if not checklist_text:
                reason_parts.append("missing Checklist")
            result.skipped_rows.append(
                SkippedRow(row_index=row_index, reason=", ".join(reason_parts))
            )
            logger.warning(
                "Skipping row %d: %s", row_index, ", ".join(reason_parts)
            )
            continue

        # Determine if this is a new skill or continuation
        if skill_name:
            # NEW skill
            current_skill = Skill(
                name=skill_name,
                definition=skill_definition,
                is_from_seed_data=True,
                id=uuid4(),
            )
            result.skills.append(current_skill)
            area_order = 0

        if current_skill is None:
            # Continuation row but no previous skill exists
            result.skipped_rows.append(
                SkippedRow(
                    row_index=row_index,
                    reason="Continuation row with no preceding skill",
                )
            )
            continue

        # Create assessment criteria for this area
        clean_area_name = _strip_area_number_prefix(area_of_measurement)
        criteria_id = uuid4()
        criteria = AssessmentCriteria(
            name=clean_area_name,
            skill_id=current_skill.id,
            order_index=area_order,
            id=criteria_id,
        )

        # Parse checklist items
        criteria.checklist_items = _parse_checklist_items(checklist_text, criteria_id)

        current_skill.assessment_criteria.append(criteria)
        area_order += 1

    return result


def should_import(catalog_size: int) -> bool:
    """Check whether seed data should be imported.

    Returns False when the catalog already has data, preventing duplicate imports.

    Args:
        catalog_size: The current number of skills in the catalog.

    Returns:
        True if catalog is empty and import should proceed, False otherwise.
    """
    return catalog_size == 0
