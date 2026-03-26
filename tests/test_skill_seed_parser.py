"""Tests for the skill seed data parser."""

import pytest

from src.parsers.skill_seed_parser import (
    ParseResult,
    SkippedRow,
    parse,
    should_import,
)
from src.models.skill import Skill, AssessmentCriteria, ChecklistItem


# --- Sample data fixtures ---

SIMPLE_TABLE = """\
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| ----- | ----- | ----- | ----- |
| TestSkill | A test skill definition | 1\\. Area One | \\- Item A \\- Item B |
"""

MULTI_ROW_TABLE = """\
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| ----- | ----- | ----- | ----- |
| Cognitive Flexibility | Def of CF | 1\\. Area Alpha | \\- Check 1 \\- Check 2 |
|  |  | 2\\. Area Beta | \\- Check 3 \\- Check 4 \\- Check 5 |
"""

TWO_SKILLS_TABLE = """\
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| ----- | ----- | ----- | ----- |
| Skill A | Def A | 1\\. Area A1 | \\- C1 \\- C2 |
|  |  | 2\\. Area A2 | \\- C3 |
| Skill B | Def B | 1\\. Area B1 | \\- C4 \\- C5 |
"""

INCOMPLETE_ROW_TABLE = """\
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| ----- | ----- | ----- | ----- |
| Good Skill | Good def | 1\\. Good Area | \\- Good item |
| Bad Skill | Bad def |  | \\- Orphan item |
| Also Bad | Also bad def | 1\\. Has area |  |
"""


# --- Tests for parse() ---


class TestParseBasic:
    """Test basic parsing of well-formed seed data."""

    def test_parse_single_skill_single_area(self):
        result = parse(SIMPLE_TABLE)
        assert len(result.skills) == 1
        assert len(result.skipped_rows) == 0

        skill = result.skills[0]
        assert skill.name == "TestSkill"
        assert skill.definition == "A test skill definition"
        assert skill.is_from_seed_data is True
        assert len(skill.assessment_criteria) == 1

        criteria = skill.assessment_criteria[0]
        assert criteria.name == "Area One"  # number prefix stripped
        assert criteria.order_index == 0
        assert len(criteria.checklist_items) == 2
        assert criteria.checklist_items[0].description == "Item A"
        assert criteria.checklist_items[1].description == "Item B"

    def test_parse_multi_row_skill(self):
        result = parse(MULTI_ROW_TABLE)
        assert len(result.skills) == 1

        skill = result.skills[0]
        assert skill.name == "Cognitive Flexibility"
        assert len(skill.assessment_criteria) == 2

        area1 = skill.assessment_criteria[0]
        assert area1.name == "Area Alpha"
        assert area1.order_index == 0
        assert len(area1.checklist_items) == 2

        area2 = skill.assessment_criteria[1]
        assert area2.name == "Area Beta"
        assert area2.order_index == 1
        assert len(area2.checklist_items) == 3

    def test_parse_two_skills(self):
        result = parse(TWO_SKILLS_TABLE)
        assert len(result.skills) == 2

        skill_a = result.skills[0]
        assert skill_a.name == "Skill A"
        assert len(skill_a.assessment_criteria) == 2

        skill_b = result.skills[1]
        assert skill_b.name == "Skill B"
        assert len(skill_b.assessment_criteria) == 1

    def test_all_skills_marked_as_seed_data(self):
        result = parse(TWO_SKILLS_TABLE)
        for skill in result.skills:
            assert skill.is_from_seed_data is True

    def test_unique_ids(self):
        result = parse(TWO_SKILLS_TABLE)
        skill_ids = [s.id for s in result.skills]
        assert len(skill_ids) == len(set(skill_ids))

        criteria_ids = [
            c.id for s in result.skills for c in s.assessment_criteria
        ]
        assert len(criteria_ids) == len(set(criteria_ids))


class TestParseSkippedRows:
    """Test that incomplete rows are skipped with reasons."""

    def test_skip_rows_missing_area_or_checklist(self):
        result = parse(INCOMPLETE_ROW_TABLE)
        assert len(result.skills) == 1  # only "Good Skill" parsed
        assert result.skills[0].name == "Good Skill"
        assert len(result.skipped_rows) == 2

    def test_skipped_row_has_reason(self):
        result = parse(INCOMPLETE_ROW_TABLE)
        reasons = [sr.reason for sr in result.skipped_rows]
        assert any("missing Areas of Measurement" in r for r in reasons)
        assert any("missing Checklist" in r for r in reasons)

    def test_empty_content(self):
        result = parse("")
        assert len(result.skills) == 0
        assert len(result.skipped_rows) == 0

    def test_header_only(self):
        content = """\
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| ----- | ----- | ----- | ----- |
"""
        result = parse(content)
        assert len(result.skills) == 0


class TestParseEdgeCases:
    """Test edge cases in parsing."""

    def test_continuation_row_without_preceding_skill(self):
        content = """\
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| ----- | ----- | ----- | ----- |
|  |  | 1\\. Orphan Area | \\- Orphan item |
"""
        result = parse(content)
        assert len(result.skills) == 0
        assert len(result.skipped_rows) == 1
        assert "no preceding skill" in result.skipped_rows[0].reason.lower()

    def test_area_number_prefix_stripped(self):
        result = parse(SIMPLE_TABLE)
        criteria = result.skills[0].assessment_criteria[0]
        # "1\. Area One" should become "Area One"
        assert criteria.name == "Area One"

    def test_checklist_item_order_index(self):
        result = parse(SIMPLE_TABLE)
        items = result.skills[0].assessment_criteria[0].checklist_items
        assert items[0].order_index == 0
        assert items[1].order_index == 1

    def test_criteria_linked_to_skill(self):
        result = parse(SIMPLE_TABLE)
        skill = result.skills[0]
        for criteria in skill.assessment_criteria:
            assert criteria.skill_id == skill.id

    def test_checklist_linked_to_criteria(self):
        result = parse(SIMPLE_TABLE)
        criteria = result.skills[0].assessment_criteria[0]
        for item in criteria.checklist_items:
            assert item.assessment_criteria_id == criteria.id


# --- Tests for should_import() ---


class TestShouldImport:
    """Test the should_import guard function."""

    def test_returns_true_when_catalog_empty(self):
        assert should_import(0) is True

    def test_returns_false_when_catalog_has_data(self):
        assert should_import(1) is False
        assert should_import(10) is False
        assert should_import(100) is False
