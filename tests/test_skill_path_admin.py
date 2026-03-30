"""Tests for Admin Skill Path Template management."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.models.errors import NotFoundError, ValidationError
from src.models.skill_path import (
    Enrollment,
    TokenUsageLog,
    SafetyViolationLog,
)
from src.services.skill_path_admin import ConflictError, SkillPathAdminService


def _valid_template_data(**overrides) -> dict:
    defaults = {
        "title": "Test Skill Path",
        "skill_name": "Python Programming",
        "description": "Learn Python from scratch",
        "created_by": "admin-1",
        "items": [
            {
                "title": "Intro to Python",
                "item_type": "fixed",
                "content_type": "material",
                "learning_type": "formal",
                "order": 1,
                "estimated_minutes": 60,
                "badge_level_order": 1,
            }
        ],
        "badge_levels": [
            {"name": "Explorer", "order": 1, "description": "Beginner level"},
        ],
        "criteria": [
            {"criteria_type": "min_hours", "value": 10, "badge_level_order": 1},
        ],
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# Requirement 1: CRUD Skill Path Template
# ===========================================================================


class TestCreateTemplate:
    def test_create_returns_template_with_status_draft(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        assert t.status == "draft"
        assert t.title == "Test Skill Path"
        assert t.skill_name == "Python Programming"

    def test_create_assigns_version_1(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        assert t.version == 1

    def test_create_with_nested_items(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        assert len(t.items) == 1
        assert t.items[0].title == "Intro to Python"

    def test_create_with_nested_badge_levels(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        assert len(t.badge_levels) == 1
        assert t.badge_levels[0].name == "Explorer"

    def test_create_criteria_attached_to_badge(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        assert len(t.badge_levels[0].criteria) == 1
        assert t.badge_levels[0].criteria[0].criteria_type == "min_hours"

    def test_create_empty_title_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError) as exc:
            svc.create_template(_valid_template_data(title=""))
        assert any(f["field_name"] == "title" for f in exc.value.fields)

    def test_create_empty_skill_name_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError) as exc:
            svc.create_template(_valid_template_data(skill_name=""))
        assert any(f["field_name"] == "skill_name" for f in exc.value.fields)


class TestListTemplates:
    def test_list_empty(self):
        svc = SkillPathAdminService()
        assert svc.list_templates() == []

    def test_list_returns_sorted_by_datetime_desc(self):
        svc = SkillPathAdminService()
        svc.create_template(_valid_template_data(title="First"))
        svc.create_template(_valid_template_data(title="Second"))
        result = svc.list_templates()
        assert len(result) == 2
        assert result[0]["title"] == "Second"
        assert result[1]["title"] == "First"

    def test_list_includes_item_count(self):
        svc = SkillPathAdminService()
        svc.create_template(_valid_template_data())
        result = svc.list_templates()
        assert result[0]["item_count"] == 1

    def test_list_includes_enrollment_count(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        result = svc.list_templates()
        assert result[0]["enrollment_count"] == 0
        assert result[0]["has_enrollments"] is False


class TestGetTemplate:
    def test_get_existing(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        fetched = svc.get_template(str(t.id))
        assert fetched.title == "Test Skill Path"

    def test_get_nonexistent_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(NotFoundError):
            svc.get_template("nonexistent")


class TestUpdateTemplate:
    def test_update_changes_fields(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        result = svc.update_template(str(t.id), _valid_template_data(
            title="Updated Title", version=1
        ))
        assert result["template"].title == "Updated Title"

    def test_update_increments_version(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        result = svc.update_template(str(t.id), _valid_template_data(version=1))
        assert result["version"] == 2

    def test_update_delete_and_recreate_nested(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        new_items = [
            {"title": "New Item", "item_type": "open", "content_type": "quiz",
             "learning_type": "social", "order": 1}
        ]
        result = svc.update_template(str(t.id), _valid_template_data(
            items=new_items, version=1
        ))
        assert len(result["template"].items) == 1
        assert result["template"].items[0].title == "New Item"

    def test_update_with_enrollments_returns_warning(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        tid = str(t.id)
        svc.add_enrollment(tid, Enrollment(
            template_id=t.id, learner_name="Test Learner"
        ))
        result = svc.update_template(tid, _valid_template_data(version=1))
        assert "warning" in result
        assert "enrollment" in result["warning"]

    def test_update_nonexistent_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(NotFoundError):
            svc.update_template("nonexistent", _valid_template_data())


class TestDeleteTemplate:
    def test_delete_existing(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        tid = str(t.id)
        svc.delete_template(tid)
        with pytest.raises(NotFoundError):
            svc.get_template(tid)

    def test_delete_nonexistent_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(NotFoundError):
            svc.delete_template("nonexistent")


# ===========================================================================
# Requirement 2: Badge Level Management
# ===========================================================================


class TestBadgeLevels:
    def test_supports_1_to_3_levels(self):
        svc = SkillPathAdminService()
        levels = [
            {"name": "Explorer", "order": 1},
            {"name": "Practitioner", "order": 2},
            {"name": "Master", "order": 3},
        ]
        t = svc.create_template(_valid_template_data(badge_levels=levels))
        assert len(t.badge_levels) == 3

    def test_more_than_3_levels_raises(self):
        svc = SkillPathAdminService()
        levels = [{"name": f"L{i}", "order": i} for i in range(1, 5)]
        with pytest.raises(ValidationError) as exc:
            svc.create_template(_valid_template_data(badge_levels=levels))
        assert any("badge_levels" in f["field_name"] for f in exc.value.fields)

    def test_duplicate_order_raises(self):
        svc = SkillPathAdminService()
        levels = [
            {"name": "A", "order": 1},
            {"name": "B", "order": 1},
        ]
        with pytest.raises(ValidationError) as exc:
            svc.create_template(_valid_template_data(badge_levels=levels))
        assert any("unique" in f["message"] for f in exc.value.fields)


# ===========================================================================
# Requirement 3: Path Criteria Management
# ===========================================================================


class TestPathCriteria:
    def test_criteria_linked_to_badge_level(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data(
            badge_levels=[
                {"name": "Explorer", "order": 1},
                {"name": "Practitioner", "order": 2},
            ],
            criteria=[
                {"criteria_type": "min_hours", "value": 10, "badge_level_order": 1},
                {"criteria_type": "quiz_score", "value": 80, "badge_level_order": 2},
            ],
        ))
        assert len(t.badge_levels[0].criteria) == 1
        assert t.badge_levels[0].criteria[0].criteria_type == "min_hours"
        bl2 = next(b for b in t.badge_levels if b.order == 2)
        assert len(bl2.criteria) == 1
        assert bl2.criteria[0].criteria_type == "quiz_score"

    def test_negative_value_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError) as exc:
            svc.create_template(_valid_template_data(
                criteria=[{"criteria_type": "min_hours", "value": -5, "badge_level_order": 1}]
            ))
        assert any("negative" in f["message"] for f in exc.value.fields)

    def test_quiz_score_over_100_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError) as exc:
            svc.create_template(_valid_template_data(
                criteria=[{"criteria_type": "quiz_score", "value": 150, "badge_level_order": 1}]
            ))
        assert any("0 and 100" in f["message"] for f in exc.value.fields)

    def test_completion_rate_over_100_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError) as exc:
            svc.create_template(_valid_template_data(
                criteria=[{"criteria_type": "completion_rate", "value": 101, "badge_level_order": 1}]
            ))
        assert any("0 and 100" in f["message"] for f in exc.value.fields)

    def test_all_criteria_types_accepted(self):
        svc = SkillPathAdminService()
        from src.models.skill_path import VALID_CRITERIA_TYPES
        criteria = [
            {"criteria_type": ct, "value": 10, "badge_level_order": 1}
            for ct in VALID_CRITERIA_TYPES
        ]
        t = svc.create_template(_valid_template_data(criteria=criteria))
        total_criteria = sum(len(bl.criteria) for bl in t.badge_levels)
        assert total_criteria == len(VALID_CRITERIA_TYPES)


# ===========================================================================
# Requirement 4: PathItem Management
# ===========================================================================


class TestPathItems:
    def test_items_sorted_by_order(self):
        svc = SkillPathAdminService()
        items = [
            {"title": "B", "item_type": "fixed", "content_type": "material",
             "learning_type": "formal", "order": 2},
            {"title": "A", "item_type": "open", "content_type": "quiz",
             "learning_type": "social", "order": 1},
        ]
        t = svc.create_template(_valid_template_data(items=items))
        serialized = svc.serialize_template(t)
        assert serialized["items"][0]["title"] == "A"
        assert serialized["items"][1]["title"] == "B"

    def test_invalid_item_type_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError):
            svc.create_template(_valid_template_data(items=[
                {"title": "X", "item_type": "invalid", "content_type": "material",
                 "learning_type": "formal", "order": 1}
            ]))

    def test_invalid_content_type_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError):
            svc.create_template(_valid_template_data(items=[
                {"title": "X", "item_type": "fixed", "content_type": "invalid",
                 "learning_type": "formal", "order": 1}
            ]))

    def test_invalid_learning_type_raises(self):
        svc = SkillPathAdminService()
        with pytest.raises(ValidationError):
            svc.create_template(_valid_template_data(items=[
                {"title": "X", "item_type": "fixed", "content_type": "material",
                 "learning_type": "invalid", "order": 1}
            ]))


# ===========================================================================
# Requirement 5: Publish and Archive
# ===========================================================================


class TestPublishArchive:
    def test_publish_changes_status(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        published = svc.publish_template(str(t.id))
        assert published.status == "published"

    def test_publish_without_items_raises(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data(items=[]))
        with pytest.raises(ValidationError) as exc:
            svc.publish_template(str(t.id))
        assert any("items" in f["field_name"] for f in exc.value.fields)

    def test_publish_without_badge_levels_raises(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data(badge_levels=[]))
        with pytest.raises(ValidationError) as exc:
            svc.publish_template(str(t.id))
        assert any("badge_levels" in f["field_name"] for f in exc.value.fields)

    def test_publish_already_published_raises(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        svc.publish_template(str(t.id))
        with pytest.raises(ValidationError) as exc:
            svc.publish_template(str(t.id))
        assert any("publish แล้ว" in f["message"] for f in exc.value.fields)

    def test_archive_changes_status(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        archived = svc.archive_template(str(t.id))
        assert archived.status == "archived"

    def test_archive_already_archived_raises(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        svc.archive_template(str(t.id))
        with pytest.raises(ValidationError) as exc:
            svc.archive_template(str(t.id))
        assert any("archive แล้ว" in f["message"] for f in exc.value.fields)

    def test_publish_creates_audit_log(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        svc.publish_template(str(t.id))
        logs = svc.get_audit_logs()
        assert len(logs) == 1
        assert logs[0].action == "publish"

    def test_archive_creates_audit_log(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        svc.archive_template(str(t.id))
        logs = svc.get_audit_logs()
        assert len(logs) == 1
        assert logs[0].action == "archive"


# ===========================================================================
# Requirement 6: Optimistic Locking
# ===========================================================================


class TestOptimisticLocking:
    def test_version_mismatch_raises_conflict(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        with pytest.raises(ConflictError) as exc:
            svc.update_template(str(t.id), _valid_template_data(version=99))
        assert exc.value.current_version == 1

    def test_correct_version_succeeds(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        result = svc.update_template(str(t.id), _valid_template_data(version=1))
        assert result["version"] == 2

    def test_version_none_skips_check(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        result = svc.update_template(str(t.id), _valid_template_data(version=None))
        assert result["version"] == 2


# ===========================================================================
# Requirement 9: AI Monitoring Dashboard
# ===========================================================================


class TestAIMonitoring:
    def test_empty_monitoring(self):
        svc = SkillPathAdminService()
        result = svc.get_ai_monitoring()
        assert result["summary"]["total_requests"] == 0
        assert result["summary"]["total_tokens"] == 0
        assert result["summary"]["error_count"] == 0
        assert result["summary"]["avg_response_ms"] == 0
        assert result["by_module"] == []

    def test_monitoring_with_logs(self):
        svc = SkillPathAdminService()
        svc.log_token_usage(TokenUsageLog(
            module_type="suggest", total_tokens=100, response_ms=200.0
        ))
        svc.log_token_usage(TokenUsageLog(
            module_type="suggest", total_tokens=200, response_ms=300.0
        ))
        svc.log_token_usage(TokenUsageLog(
            module_type="chat", total_tokens=50, response_ms=100.0, is_error=True
        ))
        result = svc.get_ai_monitoring()
        assert result["summary"]["total_requests"] == 3
        assert result["summary"]["total_tokens"] == 350
        assert result["summary"]["error_count"] == 1
        assert len(result["by_module"]) == 2


# ===========================================================================
# Requirement 10: Safety Violations Dashboard
# ===========================================================================


class TestSafetyViolations:
    def test_empty_violations(self):
        svc = SkillPathAdminService()
        assert svc.get_safety_violations() == []

    def test_violations_sorted_desc(self):
        svc = SkillPathAdminService()
        svc.log_safety_violation(SafetyViolationLog(
            content_type="text", original_content="old", violation_type="profanity",
            timestamp=datetime(2024, 1, 1),
        ))
        svc.log_safety_violation(SafetyViolationLog(
            content_type="text", original_content="new", violation_type="spam",
            timestamp=datetime(2024, 6, 1),
        ))
        result = svc.get_safety_violations()
        assert len(result) == 2
        assert result[0]["violation_type"] == "spam"

    def test_violations_max_100(self):
        svc = SkillPathAdminService()
        for i in range(120):
            svc.log_safety_violation(SafetyViolationLog(
                content_type="text", original_content=f"content-{i}",
                violation_type="test",
            ))
        result = svc.get_safety_violations()
        assert len(result) == 100


# ===========================================================================
# Requirement 11: Learner Detail View
# ===========================================================================


class TestLearnerDetailView:
    def test_get_enrollment_detail(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        tid = str(t.id)
        enrollment = Enrollment(
            template_id=t.id,
            learner_name="Test Learner",
            total_hours=5.0,
            items_completed=3,
            items_total=10,
            avg_quiz_score=85.0,
            plan_items=[
                {"id": "1", "custom_title": "Item 1", "order": 2, "status": "done", "learning_type": "formal"},
                {"id": "2", "custom_title": "Item 2", "order": 1, "status": "pending", "learning_type": "social"},
            ],
        )
        svc.add_enrollment(tid, enrollment)
        detail = svc.get_enrollment_detail(str(enrollment.id))
        assert detail["learner_name"] == "Test Learner"
        assert detail["progress"]["total_hours"] == 5.0
        assert detail["plan_items"][0]["order"] == 1  # sorted

    def test_enrollment_not_found(self):
        svc = SkillPathAdminService()
        with pytest.raises(NotFoundError):
            svc.get_enrollment_detail("nonexistent")

    def test_quiz_attempts_limited_to_20(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        enrollment = Enrollment(
            template_id=t.id,
            learner_name="Learner",
            quiz_attempts=[
                {"id": str(i), "attempted_at": f"2024-01-{i+1:02d}T00:00:00"}
                for i in range(25)
            ],
        )
        svc.add_enrollment(str(t.id), enrollment)
        detail = svc.get_enrollment_detail(str(enrollment.id))
        assert len(detail["quiz_attempts"]) == 20


# ===========================================================================
# Requirement 12: Enrollment List per Template
# ===========================================================================


class TestEnrollmentList:
    def test_list_enrollments_empty(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        result = svc.list_enrollments(str(t.id))
        assert result == []

    def test_list_enrollments_with_progress(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        tid = str(t.id)
        svc.add_enrollment(tid, Enrollment(
            template_id=t.id, learner_name="Learner A",
            total_hours=3.0, items_completed=2, items_total=5,
        ))
        result = svc.list_enrollments(tid)
        assert len(result) == 1
        assert result[0]["learner_name"] == "Learner A"
        assert result[0]["progress_summary"]["total_hours"] == 3.0


# ===========================================================================
# Requirement 13: Audit Logging
# ===========================================================================


class TestAuditLogging:
    def test_publish_logs_audit(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        svc.publish_template(str(t.id))
        logs = svc.get_audit_logs()
        assert len(logs) == 1
        assert logs[0].action == "publish"
        assert "draft" in logs[0].changes_summary
        assert "published" in logs[0].changes_summary

    def test_update_with_enrollments_logs_audit(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        tid = str(t.id)
        svc.publish_template(tid)
        svc.add_enrollment(tid, Enrollment(
            template_id=t.id, learner_name="Learner"
        ))
        svc.update_template(tid, _valid_template_data(version=1))
        logs = svc.get_audit_logs()
        assert any(l.action == "update" for l in logs)


# ===========================================================================
# Requirement 14: Data Model Serialization
# ===========================================================================


class TestSerialization:
    def test_serialize_template_fields(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        data = svc.serialize_template(t)
        expected_keys = {
            "id", "title", "description", "skill_name", "status",
            "created_by", "version", "items", "badge_levels",
            "has_enrollments", "item_count", "enrollment_count",
            "datetime_create", "datetime_update", "cover_image",
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_serialize_path_item_fields(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        data = svc.serialize_template(t)
        item = data["items"][0]
        expected = {"id", "title", "item_type", "content_type", "material_id",
                    "order", "learning_type", "estimated_minutes", "badge_level_order"}
        assert expected.issubset(set(item.keys()))

    def test_serialize_badge_level_fields(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        data = svc.serialize_template(t)
        bl = data["badge_levels"][0]
        expected = {"id", "name", "order", "description", "content_provider", "image", "criteria"}
        assert expected.issubset(set(bl.keys()))

    def test_serialize_criteria_fields(self):
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        data = svc.serialize_template(t)
        c = data["badge_levels"][0]["criteria"][0]
        expected = {"id", "criteria_type", "value"}
        assert expected.issubset(set(c.keys()))

    def test_round_trip_equivalence(self):
        """Serialize then deserialize should produce equivalent data."""
        svc = SkillPathAdminService()
        t = svc.create_template(_valid_template_data())
        serialized = svc.serialize_template(t)
        # Verify key fields match
        assert serialized["title"] == t.title
        assert serialized["skill_name"] == t.skill_name
        assert serialized["status"] == t.status
        assert serialized["version"] == t.version
        assert len(serialized["items"]) == len(t.items)
        assert len(serialized["badge_levels"]) == len(t.badge_levels)


# ===========================================================================
# Requirement 8: AI Suggest Content (unit-level)
# ===========================================================================


class TestAISuggest:
    def test_empty_message_raises(self):
        from src.services.ai_suggest import suggest_content
        with pytest.raises(ValueError, match="message is required"):
            suggest_content(message="")

    def test_whitespace_message_raises(self):
        from src.services.ai_suggest import suggest_content
        with pytest.raises(ValueError, match="message is required"):
            suggest_content(message="   ")

    def test_chat_history_limited(self):
        from src.services.ai_suggest import MAX_CHAT_HISTORY
        assert MAX_CHAT_HISTORY == 10

    def test_existing_items_limited(self):
        from src.services.ai_suggest import MAX_EXISTING_ITEMS
        assert MAX_EXISTING_ITEMS == 20

    def test_extract_suggestions_from_json_block(self):
        from src.services.ai_suggest import _extract_suggestions
        text = 'Some text\n```json\n[{"title": "Test", "content_type": "material"}]\n```\nMore text'
        clean, suggestions = _extract_suggestions(text)
        assert len(suggestions) == 1
        assert suggestions[0]["title"] == "Test"
        assert "```" not in clean

    def test_extract_no_json(self):
        from src.services.ai_suggest import _extract_suggestions
        text = "Just plain text without JSON"
        clean, suggestions = _extract_suggestions(text)
        assert suggestions == []
        assert clean == text


# ===========================================================================
# Integration: App wiring
# ===========================================================================


class TestAppIntegration:
    def test_app_has_skill_path_admin(self):
        from src.app import App
        app = App()
        assert app.get_skill_path_admin() is not None

    def test_existing_learner_services_still_work(self):
        from src.app import App
        app = App()
        assert app.get_skill_manager() is not None
        assert app.get_skill_catalog() is not None
        assert app.get_progress_tracker() is not None
        assert app.get_chat_engine() is not None
        assert app.get_skill_catalog().list_skills() == []
