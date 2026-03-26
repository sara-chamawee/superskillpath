"""Parser for Skill x Content mapping file.

Reads a Markdown table with 18 columns per row. Key columns (0-based after
splitting by pipe):
  0: No.
  1: NEW Domain
  2: OLD Domain
  3: Skill
  4: Course ID
  5: Course Name
  6: Content Provider
  7: Instructor Name
  8: Duration
  12: To Do List Type
  13: To-Do

Parsing rules:
- Row with Skill column filled (non-empty) = SUMMARY row for that skill group
  (contains domain, skill name, total duration, assessment type).
- Row with Skill column empty = Individual COURSE under the current skill group.
- The No. column groups courses together — same No. = same skill.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from src.models.course import Course

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Metadata extracted from a skill summary row."""

    domain: str
    assessment_type: str
    todo_list_url: Optional[str] = None
    total_duration: str = ""


@dataclass
class CourseParseResult:
    """Result of parsing the course content mapping file."""

    skill_courses: dict[str, list[Course]] = field(default_factory=dict)
    skill_metadata: dict[str, SkillMetadata] = field(default_factory=dict)


def _is_separator_row(row: str) -> bool:
    """Check if a row is the Markdown table separator (e.g. | --- | --- |)."""
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


def parse_courses(file_content: str) -> CourseParseResult:
    """Parse the Skill x Content mapping file into courses grouped by skill.

    Args:
        file_content: The raw text content of the mapping file.

    Returns:
        CourseParseResult with skill_courses and skill_metadata mappings.
    """
    result = CourseParseResult()
    lines = file_content.strip().split("\n")

    # Filter to only table rows (lines containing pipes)
    table_rows = [line for line in lines if "|" in line]

    if not table_rows:
        return result

    # Skip header row and separator row
    data_rows: list[str] = []
    for i, row in enumerate(table_rows):
        if i == 0:
            continue
        if _is_separator_row(row):
            continue
        data_rows.append(row)

    current_skill_name: Optional[str] = None
    course_order = 0

    for row in data_rows:
        cells = _parse_cells(row)

        # Need at least 9 columns to read up to Duration (index 8)
        if len(cells) < 9:
            continue

        skill_name = cells[3].strip() if len(cells) > 3 else ""
        course_id = cells[4].strip() if len(cells) > 4 else ""
        course_name = cells[5].strip() if len(cells) > 5 else ""
        content_provider = cells[6].strip() if len(cells) > 6 else ""
        instructor_name = cells[7].strip() if len(cells) > 7 else ""
        duration = cells[8].strip() if len(cells) > 8 else ""
        todo_list_type = cells[12].strip() if len(cells) > 12 else ""
        todo_link = cells[13].strip() if len(cells) > 13 else ""

        if skill_name:
            # SUMMARY row — new skill group
            current_skill_name = skill_name
            course_order = 0

            domain = cells[1].strip() if len(cells) > 1 else ""

            metadata = SkillMetadata(
                domain=domain,
                assessment_type=todo_list_type,
                todo_list_url=todo_link if todo_link else None,
                total_duration=duration,
            )
            result.skill_metadata[current_skill_name] = metadata

            if current_skill_name not in result.skill_courses:
                result.skill_courses[current_skill_name] = []
        else:
            # COURSE row — individual course under current skill
            if current_skill_name is None:
                logger.warning("Course row found with no preceding skill summary, skipping")
                continue

            if not course_name:
                # Skip rows without a course name
                continue

            course = Course(
                skill_id=uuid4(),  # placeholder; caller links to real skill
                course_code=course_id,
                name=course_name,
                content_provider=content_provider,
                instructor_name=instructor_name,
                duration=duration,
                order_index=course_order,
                id=uuid4(),
            )

            if current_skill_name not in result.skill_courses:
                result.skill_courses[current_skill_name] = []
            result.skill_courses[current_skill_name].append(course)
            course_order += 1

    return result
