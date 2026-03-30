"""Application entry point — wires all services together."""

import logging
from typing import Optional

from src.models.chat import ChatSession
from src.parsers import course_content_parser, skill_seed_parser, skill_courses_parser
from src.services.ai_chat_engine import AIChatEngineService, ChatResponse
from src.services.progress_tracker import ProgressTrackerService
from src.services.skill_catalog import SkillCatalogService
from src.services.skill_manager import SkillManagerService
from src.services.skill_path_admin import SkillPathAdminService

logger = logging.getLogger(__name__)


class App:
    """Main application that wires all services together.

    Initialises SkillManager, SkillCatalog, ProgressTracker and AIChatEngine.
    Optionally loads seed skills and course content on startup.
    """

    def __init__(
        self,
        skills_file: Optional[str] = None,
        courses_file: Optional[str] = None,
        skill_courses_file: Optional[str] = None,
    ) -> None:
        # Core services
        self._skill_manager = SkillManagerService()
        self._skill_catalog = SkillCatalogService(self._skill_manager)
        self._progress_tracker = ProgressTrackerService()
        self._chat_engine = AIChatEngineService(
            self._skill_catalog, self._progress_tracker
        )
        self._skill_path_admin = SkillPathAdminService()

        # Load seed data if file paths provided
        if skills_file is not None:
            self._load_seed_skills(skills_file)

        if courses_file is not None:
            self._load_courses(courses_file)

        if skill_courses_file is not None:
            self._load_skill_courses(skill_courses_file)

        # Auto-seed admin templates from skills with complete data
        self._seed_admin_templates()

    # ------------------------------------------------------------------
    # Service accessors
    # ------------------------------------------------------------------

    def get_skill_manager(self) -> SkillManagerService:
        return self._skill_manager

    def get_skill_catalog(self) -> SkillCatalogService:
        return self._skill_catalog

    def get_progress_tracker(self) -> ProgressTrackerService:
        return self._progress_tracker

    def get_chat_engine(self) -> AIChatEngineService:
        return self._chat_engine

    def get_skill_path_admin(self) -> SkillPathAdminService:
        return self._skill_path_admin

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def start_learning(self, user_id: str, skill_id: str) -> ChatSession:
        """Start a chat session for a user on a specific skill."""
        return self._chat_engine.start_session(user_id, skill_id)

    def send_chat(self, session_id: str, message: str) -> ChatResponse:
        """Send a message in an existing chat session."""
        return self._chat_engine.send_message(session_id, message)

    # ------------------------------------------------------------------
    # Private — seed data loading
    # ------------------------------------------------------------------

    def _load_seed_skills(self, skills_file: str) -> None:
        """Read Skills Name.md, parse, and add to skill manager if catalog is empty."""
        try:
            with open(skills_file, "r", encoding="utf-8") as fh:
                content = fh.read()
        except FileNotFoundError:
            logger.warning("Skills seed file not found: %s — starting with empty catalog", skills_file)
            return

        catalog_size = len(self._skill_catalog.list_skills())
        if not skill_seed_parser.should_import(catalog_size):
            logger.info("Catalog already has data (%d skills) — skipping seed import", catalog_size)
            return

        result = skill_seed_parser.parse(content)

        if result.skipped_rows:
            for sr in result.skipped_rows:
                logger.warning("Skipped seed row %d: %s", sr.row_index, sr.reason)

        if result.skills:
            self._skill_manager.add_seed_skills(result.skills)
            logger.info("Imported %d skills from seed data", len(result.skills))

    def _load_courses(self, courses_file: str) -> None:
        """Read skill-content-mapping.md, parse, and add courses to catalog."""
        try:
            with open(courses_file, "r", encoding="utf-8") as fh:
                content = fh.read()
        except FileNotFoundError:
            logger.warning("Courses file not found: %s — continuing without course data", courses_file)
            return

        parse_result = course_content_parser.parse_courses(content)

        if parse_result.skill_courses or parse_result.skill_metadata:
            # Convert SkillMetadata dataclasses to plain dicts for add_courses
            metadata_dicts: dict = {}
            for skill_name, meta in parse_result.skill_metadata.items():
                metadata_dicts[skill_name] = {
                    "domain": meta.domain,
                    "assessment_type": meta.assessment_type,
                    "todo_list_url": meta.todo_list_url,
                }

            self._skill_catalog.add_courses(parse_result.skill_courses, metadata_dicts)
            total_courses = sum(len(c) for c in parse_result.skill_courses.values())
            logger.info(
                "Imported %d courses for %d skills",
                total_courses,
                len(parse_result.skill_courses),
            )

    def _load_skill_courses(self, skill_courses_file: str) -> None:
        """Read skill-courses.md, parse, and add courses to catalog."""
        try:
            with open(skill_courses_file, "r", encoding="utf-8") as fh:
                content = fh.read()
        except FileNotFoundError:
            logger.warning("Skill courses file not found: %s", skill_courses_file)
            return

        skill_courses = skill_courses_parser.parse_skill_courses(content)
        if skill_courses:
            self._skill_catalog.add_courses(skill_courses, {})
            total = sum(len(c) for c in skill_courses.values())
            logger.info("Imported %d courses for %d skills from skill-courses.md", total, len(skill_courses))

    def _seed_admin_templates(self) -> None:
        """Auto-create admin templates from skills that have complete data (areas + checklist)."""
        if self._skill_path_admin.list_templates():
            return  # Already have templates

        skills = self._skill_catalog.list_skills()
        count = 0
        for skill in skills:
            if not skill.assessment_criteria:
                continue
            # Only seed skills with at least 1 area that has checklist items
            areas_with_data = [
                c for c in skill.assessment_criteria
                if c.name and c.checklist_items
            ]
            if not areas_with_data:
                continue

            # Build areas for badge level
            areas = [
                {
                    "name": c.name,
                    "checklist_items": [item.description for item in c.checklist_items],
                }
                for c in areas_with_data
            ]

            # Build course items
            courses = self._skill_catalog.get_courses_for_skill(skill.name)
            items = [
                {
                    "title": c.name,
                    "item_type": "fixed",
                    "content_type": "material",
                    "learning_type": "formal",
                    "order": i + 1,
                    "estimated_minutes": 60,
                    "badge_level_order": 1,
                    "required": True,
                    "ai_generated": False,
                }
                for i, c in enumerate(courses)
            ]

            try:
                template = self._skill_path_admin.create_template({
                    "title": skill.name,
                    "skill_name": skill.name,
                    "description": skill.definition or "",
                    "created_by": "system",
                    "items": items,
                    "badge_levels": [
                        {
                            "name": "Explorer",
                            "order": 1,
                            "description": f"ระดับเริ่มต้นสำหรับ {skill.name}",
                            "areas": areas,
                        }
                    ],
                    "criteria": [
                        {"criteria_type": "completion_rate", "value": 80, "badge_level_order": 1},
                    ],
                })
                # Auto-publish templates with complete data (must have items)
                if template.items:
                    try:
                        self._skill_path_admin.publish_template(str(template.id))
                    except Exception:
                        pass  # Stay as draft if publish fails
                count += 1
            except Exception as e:
                logger.warning("Failed to seed template for %s: %s", skill.name, e)

        if count:
            logger.info("Auto-seeded %d admin templates from skills with complete data", count)
