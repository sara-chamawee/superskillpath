"""AI Chat Engine Service — drives personalized learning through chat sessions."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4

from src.models.chat import ChatMessage, ChatSession, LearningPath, LearningStep
from src.models.errors import NotFoundError
from src.services.progress_tracker import ProgressTrackerService
from src.services.skill_catalog import SkillCatalogService
from src.services import llm_client


class StepType(Enum):
    """The 7-step learning flow types."""

    INTRODUCTION = 0
    BASELINE_ASSESSMENT = 1
    PERSONALIZED_PLAN = 2
    CONTENT_DELIVERY = 3
    PRACTICE = 4
    ASSESSMENT = 5
    WRAP_UP = 6


@dataclass
class ChatResponse:
    """Response from sending a message in a chat session."""

    message: ChatMessage
    completed_checklist_items: list[str] = field(default_factory=list)


class AIChatEngineService:
    """Drives personalized learning through chat sessions with a 7-step flow."""

    def __init__(
        self,
        skill_catalog: SkillCatalogService,
        progress_tracker: ProgressTrackerService,
    ) -> None:
        self._skill_catalog = skill_catalog
        self._progress_tracker = progress_tracker
        self._sessions: dict[str, ChatSession] = {}

        # Track which area index we're on within the 4→5→6 loop per session
        self._area_indices: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_session(self, user_id: str, skill_id: str) -> ChatSession:
        """Create a new ChatSession for a user + skill.

        Generates a LearningPath from the skill's AssessmentCriteria and
        ChecklistItems.  Each LearningStep maps to an Area of Measurement.
        Sets currentStep to 0 and adds an initial assistant message.
        """
        skill = self._skill_catalog.get_skill_detail(skill_id)

        session_id = uuid4()
        path_id = uuid4()

        # Build learning steps — one per Area of Measurement
        steps: list[LearningStep] = []
        for idx, criteria in enumerate(skill.assessment_criteria):
            checklist_ids = [str(item.id) for item in criteria.checklist_items]
            checklist_descs = [item.description for item in criteria.checklist_items]
            step = LearningStep(
                learning_path_id=path_id,
                order_index=idx,
                title=criteria.name,
                description=f"Learn and practice: {criteria.name}",
                related_checklist_items=checklist_ids,
                activities=[f"Study: {desc}" for desc in checklist_descs],
            )
            steps.append(step)

        learning_path = LearningPath(
            session_id=session_id,
            skill_id=skill.id,
            id=path_id,
            steps=steps,
        )

        now = datetime.now()
        session = ChatSession(
            user_id=user_id,  # type: ignore[arg-type]
            skill_id=skill.id,
            learning_path=learning_path,
            current_step=0,
            id=session_id,
            created_at=now,
            last_activity_at=now,
        )

        # Generate the introduction message (Step 0 / INTRODUCTION)
        total_areas = len(skill.assessment_criteria)
        total_items = sum(
            len(c.checklist_items) for c in skill.assessment_criteria
        )
        intro_content = (
            f"สวัสดีครับ! ผมเป็น Learning Companion ของคุณ วันนี้เราจะมาพัฒนาทักษะ "
            f"{skill.name} ด้วยกัน\n\n"
            f"{skill.definition}\n\n"
            f"เราจะเรียนรู้ผ่าน {total_areas} ด้านหลัก "
            f"และมี checklist {total_items} ข้อที่จะช่วยวัดความก้าวหน้าของคุณ\n\n"
            f"พร้อมเริ่มกันเลยไหมครับ?"
        )

        intro_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=intro_content,
        )
        session.messages.append(intro_msg)

        self._sessions[str(session_id)] = session
        self._area_indices[str(session_id)] = 0
        return session

    def send_message(self, session_id: str, message: str) -> ChatResponse:
        """Process a user message and return an AI response.

        Adds the user message, generates a response based on the current
        step in the 7-step flow, checks for checklist completions, and
        advances the step when appropriate.
        """
        session = self._get_session(session_id)
        skill = self._skill_catalog.get_skill_detail(str(session.skill_id))
        session.last_activity_at = datetime.now()

        # Add user message
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=message,
        )
        session.messages.append(user_msg)

        # Determine current step type and generate response
        step_type = self._current_step_type(session)
        completed_items: list[str] = []

        if step_type == StepType.INTRODUCTION:
            # After user responds to intro, move to baseline assessment
            response_content = self._generate_baseline_assessment(skill)
            session.current_step = StepType.BASELINE_ASSESSMENT.value

        elif step_type == StepType.BASELINE_ASSESSMENT:
            # After user answers baseline questions, present the plan
            response_content = self._generate_personalized_plan(skill)
            session.current_step = StepType.PERSONALIZED_PLAN.value

        elif step_type == StepType.PERSONALIZED_PLAN:
            # After user acknowledges plan, start content delivery
            area_idx = self._area_indices[session_id]
            response_content = self._generate_content_delivery(skill, area_idx)
            session.current_step = StepType.CONTENT_DELIVERY.value

        elif step_type == StepType.CONTENT_DELIVERY:
            # After content, move to practice
            area_idx = self._area_indices[session_id]
            response_content = self._generate_practice(skill, area_idx)
            session.current_step = StepType.PRACTICE.value

        elif step_type == StepType.PRACTICE:
            # After practice, move to assessment
            area_idx = self._area_indices[session_id]
            response_content, completed_items = self._generate_assessment(
                skill, area_idx, session
            )
            session.current_step = StepType.ASSESSMENT.value

        elif step_type == StepType.ASSESSMENT:
            # After assessment, either loop to next area or wrap up
            area_idx = self._area_indices[session_id]
            if area_idx + 1 < len(skill.assessment_criteria):
                # Move to next area
                self._area_indices[session_id] = area_idx + 1
                new_area_idx = area_idx + 1
                response_content = self._generate_content_delivery(
                    skill, new_area_idx
                )
                session.current_step = StepType.CONTENT_DELIVERY.value
            else:
                # All areas done — wrap up
                response_content = self._generate_wrap_up(skill, session)
                session.current_step = StepType.WRAP_UP.value

        else:
            # WRAP_UP or beyond — session is complete
            response_content = (
                "ยินดีด้วยครับ! คุณได้เรียนรู้ทักษะนี้ครบทุกด้านแล้ว "
                "หากมีคำถามเพิ่มเติม สามารถถามได้เลยครับ"
            )

        # Try LLM override if available
        llm_response = self._try_llm_response(skill, session, step_type, message)
        if llm_response is not None:
            response_content = llm_response

        ai_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_content,
        )
        session.messages.append(ai_msg)

        return ChatResponse(
            message=ai_msg,
            completed_checklist_items=completed_items,
        )

    def get_session_history(self, session_id: str) -> list[ChatMessage]:
        """Return all messages in the session."""
        session = self._get_session(session_id)
        return list(session.messages)

    def get_learning_path(self, session_id: str) -> LearningPath:
        """Return the learning path for the session."""
        session = self._get_session(session_id)
        if session.learning_path is None:
            raise NotFoundError("LearningPath", session_id)
        return session.learning_path

    def summarize_progress(self, session_id: str) -> dict:
        """Return a progress summary for the skill in this session."""
        session = self._get_session(session_id)
        skill = self._skill_catalog.get_skill_detail(str(session.skill_id))
        progress = self._progress_tracker.get_progress(
            str(session.user_id), skill
        )
        return {
            "user_id": str(session.user_id),
            "skill_id": str(session.skill_id),
            "skill_name": progress.skill_name,
            "total_checklist_items": progress.total_checklist_items,
            "completed_checklist_items": progress.completed_checklist_items,
            "percent_complete": progress.percent_complete,
            "is_completed": progress.is_completed,
        }

    def check_inactivity(
        self, session_id: str, threshold_minutes: int = 30
    ) -> Optional[str]:
        """Return a nudge message if the session has been inactive.

        If last_activity_at is older than threshold_minutes, returns a
        nudge message.  Otherwise returns None.
        """
        session = self._get_session(session_id)
        elapsed = datetime.now() - session.last_activity_at
        if elapsed > timedelta(minutes=threshold_minutes):
            skill = self._skill_catalog.get_skill_detail(str(session.skill_id))
            return (
                f"สวัสดีครับ! ดูเหมือนว่าคุณไม่ได้กลับมาเรียนต่อสักพัก "
                f"เราเรียนทักษะ {skill.name} กันอยู่นะครับ "
                f"พร้อมกลับมาเรียนต่อไหมครับ?"
            )
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session(self, session_id: str) -> ChatSession:
        """Retrieve a session or raise NotFoundError."""
        if session_id not in self._sessions:
            raise NotFoundError("ChatSession", session_id)
        return self._sessions[session_id]

    def _current_step_type(self, session: ChatSession) -> StepType:
        """Map the session's current_step int to a StepType enum."""
        try:
            return StepType(session.current_step)
        except ValueError:
            return StepType.WRAP_UP

    # --- Template-based response generators (prototype, no real LLM) ---

    def _generate_baseline_assessment(self, skill: object) -> str:
        from src.models.skill import Skill as SkillModel

        s = skill if isinstance(skill, SkillModel) else skill  # type: ignore
        return (
            f"ก่อนเริ่มเรียน อยากถามก่อนนะครับ:\n\n"
            f"1. คุณมีประสบการณ์เกี่ยวกับ {s.name} มาก่อนไหมครับ?\n"  # type: ignore
            f"2. เคยเจอสถานการณ์ที่ต้องใช้ทักษะนี้ไหมครับ? ตอนนั้นรับมือยังไง?\n"
            f"3. คุณคาดหวังอะไรจากการเรียนรู้ครั้งนี้ครับ?"
        )

    def _generate_personalized_plan(self, skill: object) -> str:
        from src.models.skill import Skill as SkillModel

        s: SkillModel = skill  # type: ignore
        areas = [c.name for c in s.assessment_criteria]
        area_list = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(areas))
        return (
            f"ขอบคุณสำหรับข้อมูลครับ! จากที่คุยกัน ผมวางแผนการเรียนรู้ให้ดังนี้:\n\n"
            f"ทักษะ: {s.name}\n"
            f"ด้านที่จะเรียน:\n{area_list}\n\n"
            f"เราจะเรียนทีละด้าน โดยแต่ละด้านจะมีเนื้อหา แบบฝึกหัด "
            f"และการประเมินผลครับ พร้อมเริ่มกันเลยไหมครับ?"
        )

    def _generate_content_delivery(self, skill: object, area_idx: int) -> str:
        from src.models.skill import Skill as SkillModel

        s: SkillModel = skill  # type: ignore
        if area_idx >= len(s.assessment_criteria):
            return "ครบทุกด้านแล้วครับ!"

        criteria = s.assessment_criteria[area_idx]
        checklist_text = "\n".join(
            f"  - {item.description}" for item in criteria.checklist_items
        )

        # Include course recommendations if available
        courses = self._skill_catalog.get_courses_for_skill(s.name)
        course_text = ""
        if courses:
            course_lines = []
            for c in courses:
                course_lines.append(
                    f"  • {c.name} (ผู้สอน: {c.instructor_name}, "
                    f"ระยะเวลา: {c.duration})"
                )
            course_text = (
                f"\n\nคอร์สเรียนที่แนะนำ:\n" + "\n".join(course_lines)
            )

        return (
            f"มาเรียนด้าน '{criteria.name}' กันครับ\n\n"
            f"ในด้านนี้ คุณจะได้เรียนรู้เกี่ยวกับ:\n{checklist_text}\n\n"
            f"ผมจะอธิบายแนวคิดหลักและยกตัวอย่างให้ครับ "
            f"ถ้ามีคำถามระหว่างทาง ถามได้เลยนะครับ"
            f"{course_text}"
        )

    def _generate_practice(self, skill: object, area_idx: int) -> str:
        from src.models.skill import Skill as SkillModel

        s: SkillModel = skill  # type: ignore
        if area_idx >= len(s.assessment_criteria):
            return "ครบทุกด้านแล้วครับ!"

        criteria = s.assessment_criteria[area_idx]
        return (
            f"ดีมากครับ! ตอนนี้มาทำแบบฝึกหัดสำหรับด้าน '{criteria.name}' กัน\n\n"
            f"ลองนึกถึงสถานการณ์จริงที่คุณเคยเจอที่เกี่ยวข้องกับด้านนี้ "
            f"แล้วเล่าให้ผมฟังว่าคุณจะรับมือยังไงครับ"
        )

    def _generate_assessment(
        self, skill: object, area_idx: int, session: ChatSession
    ) -> tuple[str, list[str]]:
        """Generate assessment response and mark checklist items complete."""
        from src.models.skill import Skill as SkillModel

        s: SkillModel = skill  # type: ignore
        if area_idx >= len(s.assessment_criteria):
            return "ครบทุกด้านแล้วครับ!", []

        criteria = s.assessment_criteria[area_idx]
        completed_ids: list[str] = []

        # Mark all checklist items for this area as complete
        for item in criteria.checklist_items:
            item_id = str(item.id)
            self._progress_tracker.mark_checklist_item_complete(
                str(session.user_id), item_id
            )
            completed_ids.append(item_id)

        # Get updated progress
        progress = self._progress_tracker.get_progress(str(session.user_id), s)

        remaining_areas = len(s.assessment_criteria) - (area_idx + 1)
        next_area_text = ""
        if remaining_areas > 0:
            next_criteria = s.assessment_criteria[area_idx + 1]
            next_area_text = (
                f"\n\nเราไปต่อด้าน '{next_criteria.name}' กันเลยนะครับ"
            )
        else:
            next_area_text = "\n\nครบทุกด้านแล้ว เราไปสรุปผลกันครับ!"

        return (
            f"จากที่เราคุยกันและทำแบบฝึกหัด คุณผ่าน checklist ไปแล้ว "
            f"{progress.completed_checklist_items} จาก "
            f"{progress.total_checklist_items} ข้อ\n"
            f"ตอนนี้ progress รวมอยู่ที่ {progress.percent_complete:.0f}%"
            f"{next_area_text}",
            completed_ids,
        )

    def _generate_wrap_up(self, skill: object, session: ChatSession) -> str:
        from src.models.skill import Skill as SkillModel

        s: SkillModel = skill  # type: ignore
        progress = self._progress_tracker.get_progress(str(session.user_id), s)

        if progress.is_completed:
            return (
                f"ยินดีด้วยครับ! 🎉 คุณผ่าน checklist ครบทุกข้อของทักษะ "
                f"{s.name} แล้ว!\n\n"
                f"สิ่งที่เราเรียนรู้ด้วยกัน:\n"
                + "\n".join(
                    f"  - {c.name}" for c in s.assessment_criteria
                )
                + f"\n\nถ้าอยากพัฒนาต่อ สามารถเลือกทักษะอื่นได้เลยครับ"
            )
        else:
            incomplete = [
                st
                for st in progress.checklist_status
                if not st.is_completed
            ]
            incomplete_text = "\n".join(
                f"  - {st.description}" for st in incomplete
            )
            return (
                f"สรุปผลการเรียนทักษะ {s.name}:\n"
                f"ผ่านแล้ว {progress.completed_checklist_items} จาก "
                f"{progress.total_checklist_items} ข้อ "
                f"({progress.percent_complete:.0f}%)\n\n"
                f"ข้อที่ยังต้องพัฒนาเพิ่ม:\n{incomplete_text}\n\n"
                f"แนะนำให้ทบทวนด้านที่ยังไม่ผ่านอีกครั้งครับ"
            )


    def _try_llm_response(self, skill, session: ChatSession, step_type: StepType, user_message: str) -> Optional[str]:
        """Try to get a response from the real LLM. Returns None if unavailable."""
        if not llm_client.is_available():
            return None

        from src.models.skill import Skill as SkillModel
        s: SkillModel = skill  # type: ignore

        # Build system prompt with skill context
        area_idx = self._area_indices.get(str(session.id), 0)
        current_area = ""
        current_checklist = ""
        if area_idx < len(s.assessment_criteria):
            criteria = s.assessment_criteria[area_idx]
            current_area = criteria.name
            current_checklist = "\n".join(f"- {item.description}" for item in criteria.checklist_items)

        # Course recommendations
        courses = self._skill_catalog.get_courses_for_skill(s.name)
        course_text = ""
        if courses:
            course_text = "คอร์สเรียนที่เกี่ยวข้อง:\n" + "\n".join(
                f"- {c.name} (ผู้สอน: {c.instructor_name}, ระยะเวลา: {c.duration})"
                for c in courses[:5]
            )

        # Progress
        progress = self._progress_tracker.get_progress(str(session.user_id), s)

        step_instructions = {
            StepType.INTRODUCTION: "ทักทายอย่างเป็นกันเอง ทำให้ผู้เรียนตื่นเต้นกับการเรียนรู้ เล่าว่าทักษะนี้จะเปลี่ยนชีวิตการทำงานเขาอย่างไร ถามว่าเคยเจอสถานการณ์ที่ต้องใช้ทักษะนี้ไหม",
            StepType.BASELINE_ASSESSMENT: "สร้างสถานการณ์จำลองสั้นๆ 1 เรื่อง ให้ผู้เรียนบอกว่าจะทำอย่างไร (ไม่ใช่ถามคำถามแบบสัมภาษณ์) เพื่อวัดระดับความรู้เดิม",
            StepType.PERSONALIZED_PLAN: "สรุปจุดแข็งจุดอ่อนจากคำตอบ แล้วนำเสนอแผนการเรียนรู้แบบ personalized ทำให้รู้สึกว่าแผนนี้ออกแบบมาเพื่อเขาโดยเฉพาะ",
            StepType.CONTENT_DELIVERY: f"สอนด้าน '{current_area}' ด้วยการเล่าเรื่องจริง/เคสจริง ไม่ใช่อ่าน textbook ให้ฟัง ถามคำถาม Socratic ให้ผู้เรียนค้นพบคำตอบเอง",
            StepType.PRACTICE: f"สร้างสถานการณ์จำลองที่สมจริงสำหรับด้าน '{current_area}' ให้ผู้เรียนแสดงบทบาท ตัดสินใจ และรับผลลัพธ์",
            StepType.ASSESSMENT: f"วิเคราะห์คำตอบอย่างลึกซึ้ง ชมสิ่งที่ทำได้ดีอย่างเฉพาะเจาะจง แนะนำสิ่งที่พัฒนาได้ แสดง progress",
            StepType.WRAP_UP: "ฉลองความสำเร็จ สรุปสิ่งที่เรียนรู้ ให้ข้อคิดที่จะนำไปใช้ได้ทันที แนะนำให้ทบทวนด้วยหลัก 2-7-30",
        }

        system_prompt = f"""คุณคือ "Sorc" — AI Learning Coach ที่ไม่เหมือนใคร คุณไม่ใช่แชทบอทตอบคำถาม แต่คุณคือโค้ชส่วนตัวที่พาผู้เรียนผ่านประสบการณ์การเรียนรู้แบบใหม่

📅 วันนี้: {datetime.now().strftime('%d %B %Y')}

🌍 บริบทโลกปัจจุบัน (ใช้อ้างอิงเมื่อเหมาะสม):
- AI และ Automation กำลังเปลี่ยนแปลงวิธีการทำงานทุกอุตสาหกรรม
- Remote/Hybrid work ทำให้ทักษะการสื่อสารและเจรจาต่อรองสำคัญมากขึ้น
- องค์กรในไทยและทั่วโลกกำลังเน้น upskilling/reskilling พนักงาน
- Gen Z เข้าสู่ตลาดแรงงานมากขึ้น ทำให้ต้องปรับวิธีการทำงานร่วมกัน
- เศรษฐกิจโลกมีความไม่แน่นอน ทักษะการเจรจาและปรับตัวจึงสำคัญมาก
(อ้างอิงบริบทเหล่านี้เมื่อเกี่ยวข้องกับทักษะที่สอน ทำให้ผู้เรียนรู้สึกว่าสิ่งที่เรียนมีความเกี่ยวข้องกับโลกจริงตอนนี้)

🎯 ทักษะ: {s.name}
📍 ด้าน ({area_idx + 1}/{len(s.assessment_criteria)}): {current_area}
📝 คำนิยาม: {s.definition[:400]}

Checklist ของด้านนี้:
{current_checklist}

{course_text}

Progress: {progress.completed_checklist_items}/{progress.total_checklist_items} ({progress.percent_complete:.0f}%)

ขั้นตอน: {step_type.name}
สิ่งที่ต้องทำ: {step_instructions.get(step_type, 'ตอบคำถามผู้เรียน')}

═══ วิธีการสอนของคุณ ═══
1. **Socratic Method** — ไม่บอกคำตอบตรงๆ แต่ถามคำถามที่ทำให้ผู้เรียน "อ๋อ!" ด้วยตัวเอง
2. **Storytelling** — เล่าเรื่องจริง เคสจริง สถานการณ์จริงที่เกิดขึ้นในองค์กร
3. **Challenge-Based** — ท้าทายผู้เรียนด้วยโจทย์ที่ยากขึ้นเรื่อยๆ
4. **Micro-Wins** — ให้ผู้เรียนรู้สึกว่าประสบความสำเร็จเล็กๆ ทุกขั้นตอน

═══ บุคลิก ═══
- พูดเหมือนรุ่นพี่ที่เก่งและใจดี ไม่ใช่ครูที่เข้มงวด
- เมื่อผู้เรียนตอบ ให้ acknowledge สิ่งที่เขาพูดก่อนเสมอ แล้วค่อยต่อยอด
- สร้างความรู้สึก "เราเรียนรู้ด้วยกัน" ไม่ใช่ "ฉันสอน คุณฟัง"

═══ รูปแบบ ═══
- ใช้ markdown: หัวข้อ, bullet, bold, blockquote
- ความยาว: 3-6 ย่อหน้า
- ทุกข้อความจบด้วย 1 คำถามที่กระตุ้นให้คิดและตอบ
- ถ้าตอบดี → ชมเฉพาะเจาะจง + ยกระดับด้วยคำถามที่ยากขึ้น
- ถ้าตอบไม่ตรง → ไม่บอกว่าผิด แต่ถามคำถามนำให้คิดใหม่
- แทรก "💡 Insight" หรือ "🔥 Pro Tip" เมื่อมีข้อมูลที่น่าสนใจ

═══ ห้าม ═══
- ห้ามตอบแบบ FAQ สั้นๆ จบ
- ห้ามเป็นแค่ textbook ที่อ่านให้ฟัง
- ห้ามพูดซ้ำๆ เหมือนเดิมทุกข้อความ"""

        # Build message history for LLM (last 10 messages)
        recent_messages = []
        for m in session.messages[-10:]:
            recent_messages.append({"role": m.role, "content": m.content})
        recent_messages.append({"role": "user", "content": user_message})

        return llm_client.chat_completion(system_prompt, recent_messages)

