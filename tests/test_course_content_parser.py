"""Tests for course_content_parser."""

from src.parsers.course_content_parser import CourseParseResult, SkillMetadata, parse_courses


SAMPLE_TABLE = """\
| No. | NEW Domain | OLD Domain | Skill | Course ID | Course Name | Content Provider | Instructor Name | Duration | DSD ID | col10 | col11 | To Do List Type | To-Do | col14 | col15 | col16 | col17 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Digital | Legacy | Data Analytics | | | | | 3:00:00 | | | | Submit Assignment File | https://example.com/todo1 | | | | |
| | | | | DA101 | Intro to Data | Coursera | John Doe | 1:00:00 | | | | | | | | | |
| | | | | DA102 | Advanced Data | Udemy | Jane Smith | 2:00:00 | | | | | | | | | |
| 2 | Thinking | Legacy2 | Critical Thinking | | | | | 2:30:00 | | | | Chat to Assess | | | | | |
| | | | | CT201 | Logic 101 | edX | Bob Lee | 1:15:00 | | | | | | | | | |
"""


def test_parse_courses_returns_correct_skills():
    result = parse_courses(SAMPLE_TABLE)
    assert isinstance(result, CourseParseResult)
    assert "Data Analytics" in result.skill_courses
    assert "Critical Thinking" in result.skill_courses


def test_parse_courses_correct_course_count():
    result = parse_courses(SAMPLE_TABLE)
    assert len(result.skill_courses["Data Analytics"]) == 2
    assert len(result.skill_courses["Critical Thinking"]) == 1


def test_parse_courses_course_fields():
    result = parse_courses(SAMPLE_TABLE)
    courses = result.skill_courses["Data Analytics"]
    first = courses[0]
    assert first.course_code == "DA101"
    assert first.name == "Intro to Data"
    assert first.content_provider == "Coursera"
    assert first.instructor_name == "John Doe"
    assert first.duration == "1:00:00"
    assert first.order_index == 0

    second = courses[1]
    assert second.course_code == "DA102"
    assert second.name == "Advanced Data"
    assert second.order_index == 1


def test_parse_courses_skill_metadata():
    result = parse_courses(SAMPLE_TABLE)

    meta = result.skill_metadata["Data Analytics"]
    assert meta.domain == "Digital"
    assert meta.assessment_type == "Submit Assignment File"
    assert meta.todo_list_url == "https://example.com/todo1"
    assert meta.total_duration == "3:00:00"

    meta2 = result.skill_metadata["Critical Thinking"]
    assert meta2.domain == "Thinking"
    assert meta2.assessment_type == "Chat to Assess"
    assert meta2.todo_list_url is None


def test_parse_courses_empty_content():
    result = parse_courses("")
    assert result.skill_courses == {}
    assert result.skill_metadata == {}


def test_parse_courses_no_table_rows():
    result = parse_courses("# Just a heading\nSome text without pipes")
    assert result.skill_courses == {}


def test_parse_courses_skill_with_no_courses():
    table = """\
| No. | NEW Domain | OLD Domain | Skill | Course ID | Course Name | Content Provider | Instructor Name | Duration | DSD ID | col10 | col11 | To Do List Type | To-Do | col14 | col15 | col16 | col17 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Digital | Legacy | Solo Skill | | | | | 1:00:00 | | | | Chat to Assess | | | | | |
"""
    result = parse_courses(table)
    assert "Solo Skill" in result.skill_courses
    assert len(result.skill_courses["Solo Skill"]) == 0
    assert result.skill_metadata["Solo Skill"].domain == "Digital"
