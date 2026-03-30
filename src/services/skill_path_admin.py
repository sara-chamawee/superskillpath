"""Admin Skill Path Template Service — CRUD, publish/archive, optimistic locking."""

import logging
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.models.errors import NotFoundError, ValidationError
from src.models.skill_path import (
    AuditLog,
    BadgeLevel,
    Enrollment,
    PathCriteria,
    PathItem,
    SafetyViolationLog,
    SkillPathTemplate,
    TokenUsageLog,
    VALID_CONTENT_TYPES,
    VALID_CRITERIA_TYPES,
    VALID_IMAGE_EXTENSIONS,
    VALID_ITEM_TYPES,
    VALID_LEARNING_TYPES,
    PERCENTAGE_CRITERIA,
)

logger = logging.getLogger(__name__)


class ConflictError(Exception):
    """Raised on optimistic locking conflict."""

    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(f"Version conflict. Current version: {current_version}")


class SkillPathAdminService:
    """Manages Skill Path Templates for Admin."""

    def __init__(self) -> None:
        self._templates: dict[str, SkillPathTemplate] = {}
        self._enrollments: dict[str, list[Enrollment]] = {}  # template_id -> list
        self._audit_logs: list[AuditLog] = []
        self._token_logs: list[TokenUsageLog] = []
        self._safety_violations: list[SafetyViolationLog] = []

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_template(self, data: dict) -> SkillPathTemplate:
        """Create a new SkillPathTemplate with nested objects."""
        errors = self._validate_template_data(data)
        if errors:
            raise ValidationError(errors)

        template_id = uuid4()
        now = datetime.now()

        badge_levels = self._build_badge_levels(data.get("badge_levels", []))
        items = self._build_items(data.get("items", []))
        criteria_list = data.get("criteria", [])
        self._attach_criteria_to_badges(badge_levels, criteria_list)

        template = SkillPathTemplate(
            title=data.get("title", "").strip(),
            skill_name=data.get("skill_name", "").strip(),
            description=data.get("description", "").strip(),
            status="draft",
            created_by=data.get("created_by", ""),
            version=1,
            cover_image=data.get("cover_image"),
            items=items,
            badge_levels=badge_levels,
            id=template_id,
            datetime_create=now,
            datetime_update=now,
        )

        self._templates[str(template_id)] = template
        return template

    def list_templates(self) -> list[dict]:
        """Return all templates sorted by datetime_create desc."""
        templates = sorted(
            self._templates.values(),
            key=lambda t: t.datetime_create,
            reverse=True,
        )
        return [self._serialize_list_item(t) for t in templates]

    def get_template(self, template_id: str) -> SkillPathTemplate:
        """Return a template by ID or raise NotFoundError."""
        if template_id not in self._templates:
            raise NotFoundError("SkillPathTemplate", template_id)
        return self._templates[template_id]

    def update_template(self, template_id: str, data: dict) -> dict:
        """Update template with optimistic locking (delete-and-recreate nested)."""
        template = self.get_template(template_id)

        # Optimistic locking
        request_version = data.get("version")
        if request_version is not None and request_version != template.version:
            raise ConflictError(template.version)

        errors = self._validate_template_data(data)
        if errors:
            raise ValidationError(errors)

        template.title = data.get("title", template.title).strip()
        template.skill_name = data.get("skill_name", template.skill_name).strip()
        template.description = data.get("description", template.description).strip()
        template.cover_image = data.get("cover_image", template.cover_image)
        template.datetime_update = datetime.now()
        template.version += 1

        # Delete-and-recreate nested
        if "badge_levels" in data:
            template.badge_levels = self._build_badge_levels(data["badge_levels"])
        if "criteria" in data:
            self._attach_criteria_to_badges(template.badge_levels, data["criteria"])
        if "items" in data:
            template.items = self._build_items(data["items"])

        # Warning for active enrollments
        warning = None
        has_enrollments = self._has_enrollments(template_id)
        if has_enrollments:
            warning = "การเปลี่ยนแปลงจะมีผลเฉพาะ enrollment ใหม่"
            self._log_audit(
                actor=data.get("created_by", "admin"),
                action="update",
                target_type="SkillPathTemplate",
                target_id=template_id,
                changes_summary="Updated template with active enrollments",
            )

        result = {"template": template, "version": template.version}
        if warning:
            result["warning"] = warning
        return result

    def delete_template(self, template_id: str) -> None:
        """Delete a template and all nested objects."""
        if template_id not in self._templates:
            raise NotFoundError("SkillPathTemplate", template_id)
        del self._templates[template_id]
        self._enrollments.pop(template_id, None)

    # ------------------------------------------------------------------
    # Publish / Archive
    # ------------------------------------------------------------------

    def publish_template(self, template_id: str) -> SkillPathTemplate:
        """Change status from draft to published."""
        template = self.get_template(template_id)

        if template.status == "published":
            raise ValidationError([{
                "field_name": "status",
                "message": "Template ถูก publish แล้ว",
            }])

        if not template.items:
            raise ValidationError([{
                "field_name": "items",
                "message": "ต้องมี Path items อย่างน้อย 1 รายการ",
            }])

        if not template.badge_levels:
            raise ValidationError([{
                "field_name": "badge_levels",
                "message": "ต้องมี Badge levels อย่างน้อย 1 ระดับ",
            }])

        old_status = template.status
        template.status = "published"
        template.datetime_update = datetime.now()

        self._log_audit(
            actor=template.created_by or "admin",
            action="publish",
            target_type="SkillPathTemplate",
            target_id=template_id,
            changes_summary=f"Status changed from {old_status} to published",
        )
        return template

    def archive_template(self, template_id: str) -> SkillPathTemplate:
        """Change status to archived."""
        template = self.get_template(template_id)

        if template.status == "archived":
            raise ValidationError([{
                "field_name": "status",
                "message": "Template ถูก archive แล้ว",
            }])

        old_status = template.status
        template.status = "archived"
        template.datetime_update = datetime.now()

        self._log_audit(
            actor=template.created_by or "admin",
            action="archive",
            target_type="SkillPathTemplate",
            target_id=template_id,
            changes_summary=f"Status changed from {old_status} to archived",
        )
        return template

    # ------------------------------------------------------------------
    # Cover Image
    # ------------------------------------------------------------------

    def upload_cover_image(self, template_id: str, filename: str, content: bytes) -> str:
        """Store cover image and return URL path."""
        template = self.get_template(template_id)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in VALID_IMAGE_EXTENSIONS:
            raise ValidationError([{
                "field_name": "cover_image",
                "message": f"Unsupported format. Allowed: {', '.join(VALID_IMAGE_EXTENSIONS)}",
            }])

        upload_dir = os.path.join("uploads", "cover_images")
        os.makedirs(upload_dir, exist_ok=True)
        stored_name = f"{template_id}{ext}"
        path = os.path.join(upload_dir, stored_name)
        with open(path, "wb") as f:
            f.write(content)

        url = f"/uploads/cover_images/{stored_name}"
        template.cover_image = url
        template.datetime_update = datetime.now()
        return url

    def upload_badge_image(self, template_id: str, badge_order: int, filename: str, content: bytes) -> str:
        """Store badge image and return URL path."""
        template = self.get_template(template_id)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in VALID_IMAGE_EXTENSIONS:
            raise ValidationError([{
                "field_name": "badge_image",
                "message": f"Unsupported format. Allowed: {', '.join(VALID_IMAGE_EXTENSIONS)}",
            }])

        badge = next((b for b in template.badge_levels if b.order == badge_order), None)
        if badge is None:
            raise NotFoundError("BadgeLevel", str(badge_order))

        upload_dir = os.path.join("uploads", "badge_images")
        os.makedirs(upload_dir, exist_ok=True)
        stored_name = f"{template_id}_badge_{badge_order}{ext}"
        path = os.path.join(upload_dir, stored_name)
        with open(path, "wb") as f:
            f.write(content)

        url = f"/uploads/badge_images/{stored_name}"
        badge.image = url
        template.datetime_update = datetime.now()
        return url

    # ------------------------------------------------------------------
    # Enrollments
    # ------------------------------------------------------------------

    def add_enrollment(self, template_id: str, enrollment: Enrollment) -> Enrollment:
        """Add an enrollment to a template."""
        self.get_template(template_id)  # validate exists
        if template_id not in self._enrollments:
            self._enrollments[template_id] = []
        self._enrollments[template_id].append(enrollment)
        return enrollment

    def list_enrollments(self, template_id: str) -> list[dict]:
        """Return enrollments for a template with progress summary."""
        self.get_template(template_id)
        enrollments = self._enrollments.get(template_id, [])
        return [
            {
                "id": str(e.id),
                "learner_name": e.learner_name,
                "status": e.status,
                "enrolled_at": e.enrolled_at.isoformat(),
                "progress_summary": {
                    "total_hours": e.total_hours,
                    "items_completed": e.items_completed,
                    "items_total": e.items_total,
                    "avg_quiz_score": e.avg_quiz_score,
                    "status": e.status,
                },
            }
            for e in enrollments
        ]

    def get_enrollment_detail(self, enrollment_id: str) -> dict:
        """Return detailed enrollment info."""
        for enrollments in self._enrollments.values():
            for e in enrollments:
                if str(e.id) == enrollment_id:
                    template = self._templates.get(str(e.template_id))
                    return {
                        "id": str(e.id),
                        "learner_name": e.learner_name,
                        "template_name": template.title if template else "",
                        "status": e.status,
                        "progress": {
                            "total_hours": e.total_hours,
                            "items_completed": e.items_completed,
                            "items_total": e.items_total,
                            "avg_quiz_score": e.avg_quiz_score,
                        },
                        "plan_items": sorted(e.plan_items, key=lambda x: x.get("order", 0)),
                        "quiz_attempts": sorted(
                            e.quiz_attempts,
                            key=lambda x: x.get("attempted_at", ""),
                            reverse=True,
                        )[:20],
                        "submissions": sorted(
                            e.submissions,
                            key=lambda x: x.get("submitted_at", ""),
                            reverse=True,
                        )[:20],
                        "nudges": sorted(
                            e.nudges,
                            key=lambda x: x.get("sent_at", ""),
                            reverse=True,
                        )[:20],
                    }
        raise NotFoundError("Enrollment", enrollment_id)

    # ------------------------------------------------------------------
    # AI Monitoring
    # ------------------------------------------------------------------

    def log_token_usage(self, log: TokenUsageLog) -> None:
        """Record a token usage log entry."""
        self._token_logs.append(log)

    def get_ai_monitoring(self) -> dict:
        """Return AI monitoring summary and per-module stats."""
        if not self._token_logs:
            return {
                "summary": {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "error_count": 0,
                    "avg_response_ms": 0,
                },
                "by_module": [],
            }

        total_requests = len(self._token_logs)
        total_tokens = sum(l.total_tokens for l in self._token_logs)
        error_count = sum(1 for l in self._token_logs if l.is_error)
        avg_ms = sum(l.response_ms for l in self._token_logs) / total_requests

        # Group by module
        modules: dict[str, list[TokenUsageLog]] = {}
        for log in self._token_logs:
            modules.setdefault(log.module_type, []).append(log)

        by_module = []
        for mod, logs in modules.items():
            by_module.append({
                "module_type": mod,
                "request_count": len(logs),
                "total_tokens": sum(l.total_tokens for l in logs),
                "error_count": sum(1 for l in logs if l.is_error),
                "avg_response_ms": sum(l.response_ms for l in logs) / len(logs),
            })

        return {
            "summary": {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "error_count": error_count,
                "avg_response_ms": round(avg_ms, 2),
            },
            "by_module": by_module,
        }

    # ------------------------------------------------------------------
    # Safety Violations
    # ------------------------------------------------------------------

    def log_safety_violation(self, violation: SafetyViolationLog) -> None:
        """Record a safety violation."""
        self._safety_violations.append(violation)

    def get_safety_violations(self) -> list[dict]:
        """Return violations sorted by timestamp desc, max 100."""
        sorted_violations = sorted(
            self._safety_violations,
            key=lambda v: v.timestamp,
            reverse=True,
        )[:100]
        return [
            {
                "id": str(v.id),
                "content_type": v.content_type,
                "original_content": v.original_content,
                "violation_type": v.violation_type,
                "timestamp": v.timestamp.isoformat(),
            }
            for v in sorted_violations
        ]

    # ------------------------------------------------------------------
    # Audit Logs
    # ------------------------------------------------------------------

    def get_audit_logs(self) -> list[AuditLog]:
        """Return all audit logs."""
        return list(self._audit_logs)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize_template(self, template: SkillPathTemplate) -> dict:
        """Serialize a template to dict for API response."""
        template_id = str(template.id)
        enrollments = self._enrollments.get(template_id, [])
        return {
            "id": template_id,
            "title": template.title,
            "description": template.description,
            "skill_name": template.skill_name,
            "status": template.status,
            "created_by": template.created_by,
            "version": template.version,
            "cover_image": template.cover_image,
            "items": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "item_type": item.item_type,
                    "content_type": item.content_type,
                    "material_id": item.material_id,
                    "order": item.order,
                    "learning_type": item.learning_type,
                    "estimated_minutes": item.estimated_minutes,
                    "badge_level_order": item.badge_level_order,
                    "area_index": getattr(item, 'area_index', None),
                    "required": getattr(item, 'required', True),
                    "ai_generated": getattr(item, 'ai_generated', False),
                }
                for item in sorted(template.items, key=lambda i: i.order)
            ],
            "badge_levels": [
                {
                    "id": str(bl.id),
                    "name": bl.name,
                    "order": bl.order,
                    "description": bl.description,
                    "content_provider": bl.content_provider,
                    "image": bl.image,
                    "areas": bl.areas,
                    "criteria": [
                        {
                            "id": str(c.id),
                            "criteria_type": c.criteria_type,
                            "value": c.value,
                        }
                        for c in bl.criteria
                    ],
                }
                for bl in sorted(template.badge_levels, key=lambda b: b.order)
            ],
            "has_enrollments": len(enrollments) > 0,
            "item_count": len(template.items),
            "enrollment_count": len(enrollments),
            "datetime_create": template.datetime_create.isoformat(),
            "datetime_update": template.datetime_update.isoformat(),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _has_enrollments(self, template_id: str) -> bool:
        return len(self._enrollments.get(template_id, [])) > 0

    def _serialize_list_item(self, template: SkillPathTemplate) -> dict:
        template_id = str(template.id)
        enrollments = self._enrollments.get(template_id, [])
        return {
            "id": template_id,
            "title": template.title,
            "skill_name": template.skill_name,
            "status": template.status,
            "version": template.version,
            "item_count": len(template.items),
            "enrollment_count": len(enrollments),
            "has_enrollments": len(enrollments) > 0,
            "datetime_create": template.datetime_create.isoformat(),
            "datetime_update": template.datetime_update.isoformat(),
        }

    def _validate_template_data(self, data: dict) -> list[dict]:
        errors: list[dict] = []
        title = data.get("title", "")
        if not title or not str(title).strip():
            errors.append({"field_name": "title", "message": "must not be empty"})

        skill_name = data.get("skill_name", "")
        if not skill_name or not str(skill_name).strip():
            errors.append({"field_name": "skill_name", "message": "must not be empty"})

        # Validate badge_levels count
        badge_levels = data.get("badge_levels", [])
        if badge_levels and len(badge_levels) > 3:
            errors.append({"field_name": "badge_levels", "message": "maximum 3 badge levels allowed"})

        # Validate badge_level order uniqueness
        if badge_levels:
            orders = [bl.get("order", 0) for bl in badge_levels]
            if len(orders) != len(set(orders)):
                errors.append({"field_name": "badge_levels", "message": "badge level orders must be unique"})

        # Validate criteria
        for i, c in enumerate(data.get("criteria", [])):
            ctype = c.get("criteria_type", "")
            if ctype and ctype not in VALID_CRITERIA_TYPES:
                errors.append({
                    "field_name": f"criteria[{i}].criteria_type",
                    "message": f"invalid criteria type: {ctype}",
                })
            value = c.get("value", 0)
            if isinstance(value, (int, float)) and value < 0:
                errors.append({
                    "field_name": f"criteria[{i}].value",
                    "message": "value must not be negative",
                })
            if ctype in PERCENTAGE_CRITERIA and isinstance(value, (int, float)) and value > 100:
                errors.append({
                    "field_name": f"criteria[{i}].value",
                    "message": f"{ctype} value must be between 0 and 100",
                })

        # Validate items
        for i, item in enumerate(data.get("items", [])):
            if item.get("item_type") and item["item_type"] not in VALID_ITEM_TYPES:
                errors.append({
                    "field_name": f"items[{i}].item_type",
                    "message": f"invalid item_type: {item['item_type']}",
                })
            if item.get("content_type") and item["content_type"] not in VALID_CONTENT_TYPES:
                errors.append({
                    "field_name": f"items[{i}].content_type",
                    "message": f"invalid content_type: {item['content_type']}",
                })
            if item.get("learning_type") and item["learning_type"] not in VALID_LEARNING_TYPES:
                errors.append({
                    "field_name": f"items[{i}].learning_type",
                    "message": f"invalid learning_type: {item['learning_type']}",
                })

        return errors

    def _build_badge_levels(self, data: list[dict]) -> list[BadgeLevel]:
        levels = []
        for bl in data:
            levels.append(BadgeLevel(
                name=bl.get("name", ""),
                order=bl.get("order", 1),
                description=bl.get("description", ""),
                content_provider=bl.get("content_provider", ""),
                image=bl.get("image"),
                areas=bl.get("areas", []),
            ))
        return levels

    def _build_items(self, data: list[dict]) -> list[PathItem]:
        items = []
        for item in data:
            items.append(PathItem(
                title=item.get("title", ""),
                item_type=item.get("item_type", "fixed"),
                content_type=item.get("content_type", "material"),
                learning_type=item.get("learning_type", "formal"),
                order=item.get("order", 0),
                material_id=item.get("material_id"),
                estimated_minutes=item.get("estimated_minutes", 0),
                badge_level_order=item.get("badge_level_order", 1),
                area_index=item.get("area_index"),
                required=item.get("required", True),
                ai_generated=item.get("ai_generated", False),
            ))
        return items

    def _attach_criteria_to_badges(self, badge_levels: list[BadgeLevel], criteria_data: list[dict]) -> None:
        """Attach criteria to badge levels by matching badge_level_order."""
        # Clear existing criteria
        for bl in badge_levels:
            bl.criteria = []

        for c in criteria_data:
            bl_order = c.get("badge_level_order", 1)
            badge = next((b for b in badge_levels if b.order == bl_order), None)
            if badge is not None:
                badge.criteria.append(PathCriteria(
                    criteria_type=c.get("criteria_type", ""),
                    value=c.get("value", 0),
                    badge_level_order=bl_order,
                ))

    def _log_audit(self, actor: str, action: str, target_type: str, target_id: str, changes_summary: str = "") -> None:
        """Best-effort audit logging."""
        try:
            self._audit_logs.append(AuditLog(
                actor=actor,
                action=action,
                target_type=target_type,
                target_id=target_id,
                changes_summary=changes_summary,
            ))
        except Exception:
            logger.warning("Audit logging failed for %s %s", action, target_id)
