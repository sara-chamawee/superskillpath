"""Parser for skill-courses.md — simple 5-column table mapping skills to courses."""

import re
import logging
from uuid import uuid4
from src.models.course import Course

logger = logging.getLogger(__name__)


def parse_skill_courses(file_content: str) -> dict[str, list[Course]]:
    """Parse skill-courses.md into a dict of skill_name -> list[Course].

    Table format:
    | Skill | Course ID | Course Name | Content Provider | Instructor |
    """
    result: dict[str, list[Course]] = {}
    lines = file_content.strip().split("\n")
    table_rows = [l for l in lines if "|" in l]

    for i, row in enumerate(table_rows):
        # Skip header and separator
        if i == 0:
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        if re.match(r"^-+$", cells[0].strip()):
            continue

        skill_name = cells[0].strip()
        course_id = cells[1].strip()
        course_name = cells[2].strip()
        provider = cells[3].strip()
        instructor = cells[4].strip()

        # Skip empty rows (skill separator rows)
        if not skill_name or not course_name:
            continue

        if skill_name not in result:
            result[skill_name] = []

        order = len(result[skill_name])
        result[skill_name].append(Course(
            skill_id=uuid4(),  # placeholder, caller links to real skill
            course_code=course_id,
            name=course_name,
            content_provider=provider,
            instructor_name=instructor,
            duration="",
            order_index=order,
            id=uuid4(),
        ))

    logger.info("Parsed %d skills with %d total courses from skill-courses.md",
                len(result), sum(len(v) for v in result.values()))
    return result
