"""FastAPI backend for Personalized Learning Path."""

import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.app import App

_ROOT = os.path.dirname(os.path.dirname(__file__))
SKILLS_FILE = os.path.join(_ROOT, "seed-data", "skills-name.md")
COURSES_FILE = os.path.join(_ROOT, "seed-data", "skill-content-mapping.md")
SKILL_COURSES_FILE = os.path.join(_ROOT, "seed-data", "skill-courses.md")

app_instance = App(
    skills_file=SKILLS_FILE if os.path.exists(SKILLS_FILE) else None,
    courses_file=COURSES_FILE if os.path.exists(COURSES_FILE) else None,
    skill_courses_file=SKILL_COURSES_FILE if os.path.exists(SKILL_COURSES_FILE) else None,
)

api = FastAPI(title="Personalized Learning Path API")
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SelectSkillsRequest(BaseModel):
    user_id: str
    skill_ids: list[str]

class StartLearningRequest(BaseModel):
    user_id: str
    skill_id: str

class SendMessageRequest(BaseModel):
    message: str

class AssessSkillRequest(BaseModel):
    user_id: str
    skill_id: str
    completed_courses: list[str] = []
    completed_todos: list[str] = []


@api.get("/api/skills")
def list_skills(q: str = "", page: int = 1, limit: int = 20):
    skills = app_instance.get_skill_catalog().list_skills()
    seen = set()
    unique = []
    for s in skills:
        if s.name not in seen:
            seen.add(s.name)
            unique.append(s)
    skills = unique
    if q:
        ql = q.lower()
        skills = [s for s in skills if ql in s.name.lower() or ql in (s.definition or "").lower()]
    total = len(skills)
    page_skills = skills[(page-1)*limit : page*limit]
    return {"total": total, "page": page, "limit": limit, "skills": [
        {"id": str(s.id), "name": s.name,
         "definition": s.definition[:150]+"..." if len(s.definition)>150 else s.definition,
         "domain": s.domain, "assessment_type": s.assessment_type,
         "num_areas": len(s.assessment_criteria),
         "num_checklist_items": sum(len(c.checklist_items) for c in s.assessment_criteria)}
        for s in page_skills]}


@api.get("/api/skills/{skill_id}")
def get_skill_detail(skill_id: str):
    try:
        s = app_instance.get_skill_catalog().get_skill_detail(skill_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Skill not found")
    courses = app_instance.get_skill_catalog().get_courses_for_skill(s.name)
    return {
        "id": str(s.id), "name": s.name, "definition": s.definition,
        "domain": s.domain, "assessment_type": s.assessment_type,
        "todo_list_url": s.todo_list_url,
        "assessment_criteria": [
            {"id": str(c.id), "name": c.name,
             "checklist_items": [{"id": str(it.id), "description": it.description} for it in c.checklist_items]}
            for c in s.assessment_criteria],
        "courses": [{"course_code": c.course_code, "name": c.name, "instructor": c.instructor_name,
                      "duration": c.duration, "provider": c.content_provider} for c in courses]}


@api.post("/api/chat/start")
def start_chat(req: StartLearningRequest):
    try:
        session = app_instance.start_learning(req.user_id, req.skill_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"session_id": str(session.id), "skill_id": str(session.skill_id),
            "current_step": session.current_step,
            "messages": [{"role": m.role, "content": m.content} for m in session.messages]}


@api.post("/api/chat/{session_id}/message")
def send_message(session_id: str, req: SendMessageRequest):
    try:
        resp = app_instance.send_chat(session_id, req.message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": {"role": resp.message.role, "content": resp.message.content},
            "completed_checklist_items": resp.completed_checklist_items}


@api.post("/api/chat/{session_id}/stream")
def stream_message(session_id: str, req: SendMessageRequest):
    """Streaming chat — single Gemini call."""
    from src.services import llm_client
    import json as _json
    from src.models.chat import ChatMessage
    from datetime import datetime
    from uuid import uuid4

    try:
        engine = app_instance.get_chat_engine()
        session = engine._get_session(session_id)
        skill = app_instance.get_skill_catalog().get_skill_detail(str(session.skill_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    session.last_activity_at = datetime.now()
    user_msg = ChatMessage(session_id=session.id, role="user", content=req.message, id=uuid4(), timestamp=datetime.now())
    session.messages.append(user_msg)

    from src.services.ai_chat_engine import StepType
    step = session.current_step
    area_idx = engine._area_indices.get(session_id, 0)
    if step < 6:
        nxt = {0:1, 1:2, 2:3, 3:4, 4:5}
        if step == 5:
            if area_idx + 1 < len(skill.assessment_criteria):
                engine._area_indices[session_id] = area_idx + 1
                session.current_step = 3
            else:
                session.current_step = 6
        elif step in nxt:
            session.current_step = nxt[step]

    completed = []
    if step == 4 and area_idx < len(skill.assessment_criteria):
        for item in skill.assessment_criteria[area_idx].checklist_items:
            app_instance.get_progress_tracker().mark_checklist_item_complete(str(session.user_id), str(item.id))
            completed.append(str(item.id))

    area_name = skill.assessment_criteria[area_idx].name if area_idx < len(skill.assessment_criteria) else ""
    step_name = StepType(session.current_step).name if session.current_step <= 6 else "WRAP_UP"

    system_prompt = f"""คุณคือ "Sorc" — AI Learning Coach ที่ไม่เหมือนใคร คุณไม่ใช่แชทบอทตอบคำถาม แต่คุณคือโค้ชส่วนตัวที่พาผู้เรียนผ่านประสบการณ์การเรียนรู้แบบใหม่

📅 วันนี้: {datetime.now().strftime('%d %B %Y')}

🌍 บริบทโลกปัจจุบัน (ใช้อ้างอิงเมื่อเหมาะสม):
- AI และ Automation กำลังเปลี่ยนแปลงวิธีการทำงานทุกอุตสาหกรรม
- Remote/Hybrid work ทำให้ทักษะการสื่อสารและเจรจาต่อรองสำคัญมากขึ้น
- องค์กรในไทยและทั่วโลกกำลังเน้น upskilling/reskilling พนักงาน
- Gen Z เข้าสู่ตลาดแรงงานมากขึ้น ทำให้ต้องปรับวิธีการทำงานร่วมกัน
- เศรษฐกิจโลกมีความไม่แน่นอน ทักษะการเจรจาและปรับตัวจึงสำคัญมาก
(อ้างอิงบริบทเหล่านี้เมื่อเกี่ยวข้องกับทักษะที่สอน ทำให้ผู้เรียนรู้สึกว่าสิ่งที่เรียนมีความเกี่ยวข้องกับโลกจริงตอนนี้)

🎯 ทักษะ: {skill.name}
📍 ด้าน: {area_name} | ขั้นตอน: {step_name}
📝 คำนิยาม: {skill.definition[:300]}

═══ วิธีการสอนของคุณ ═══

1. **Socratic Method** — ไม่บอกคำตอบตรงๆ แต่ถามคำถามที่ทำให้ผู้เรียน "อ๋อ!" ด้วยตัวเอง
2. **Storytelling** — เล่าเรื่องจริง เคสจริง สถานการณ์จริงที่เกิดขึ้นในองค์กร ให้ผู้เรียนรู้สึกว่า "เคยเจอแบบนี้!"
3. **Challenge-Based** — ท้าทายผู้เรียนด้วยโจทย์ที่ยากขึ้นเรื่อยๆ ให้รู้สึกว่ากำลังเติบโต
4. **Micro-Wins** — ให้ผู้เรียนรู้สึกว่าประสบความสำเร็จเล็กๆ ทุกขั้นตอน

═══ บุคลิกของคุณ ═══

- พูดเหมือนรุ่นพี่ที่เก่งและใจดี ไม่ใช่ครูที่เข้มงวด
- ใช้ภาษาที่เป็นธรรมชาติ ไม่เป็นทางการเกินไป
- เมื่อผู้เรียนตอบ ให้ acknowledge สิ่งที่เขาพูดก่อนเสมอ แล้วค่อยต่อยอด
- ใช้ emoji อย่างเป็นธรรมชาติ (ไม่ยัดทุกประโยค)
- สร้างความรู้สึก "เราเรียนรู้ด้วยกัน" ไม่ใช่ "ฉันสอน คุณฟัง"

═══ รูปแบบการตอบ ═══

- ใช้ markdown: หัวข้อ, bullet, bold, blockquote
- ความยาว: 3-6 ย่อหน้า (ไม่สั้นเกินจนไม่มีเนื้อหา ไม่ยาวเกินจนน่าเบื่อ)
- ทุกข้อความต้องจบด้วย 1 คำถามที่กระตุ้นให้ผู้เรียนคิดและตอบ
- ถ้าผู้เรียนตอบดี → ชมเฉพาะเจาะจง + ยกระดับด้วยคำถามที่ยากขึ้น
- ถ้าผู้เรียนตอบไม่ตรง → ไม่บอกว่าผิด แต่ถามคำถามนำให้คิดใหม่
- แทรก "💡 Insight" หรือ "🔥 Pro Tip" เมื่อมีข้อมูลที่น่าสนใจ

═══ ห้าม ═══
- ห้ามตอบแบบ FAQ (ถาม-ตอบ สั้นๆ จบ)
- ห้ามเป็นแค่ textbook ที่อ่านให้ฟัง
- ห้ามพูดซ้ำๆ เหมือนเดิมทุกข้อความ"""

    recent = [{"role": m.role, "content": m.content} for m in session.messages[-6:]]

    if llm_client.is_available():
        def generate():
            try:
                from google import genai
                from google.genai import types
                client = llm_client._get_client()
                contents = [types.Content(role="user" if m["role"]=="user" else "model",
                            parts=[types.Part(text=m["content"])]) for m in recent]
                response = client.models.generate_content_stream(
                    model=llm_client._model_name, contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.7, max_output_tokens=4096),
                )
                full = ""
                for chunk in response:
                    if chunk.text:
                        full += chunk.text
                        yield f"data: {_json.dumps({'text':chunk.text,'done':False})}\n\n"
                yield f"data: {_json.dumps({'text':'','done':True,'completed':completed})}\n\n"
                session.messages.append(ChatMessage(session_id=session.id, role="assistant", content=full, id=uuid4(), timestamp=datetime.now()))
            except Exception as e:
                fb = f"ขออภัย เกิดข้อผิดพลาด: {e}"
                yield f"data: {_json.dumps({'text':fb,'done':True})}\n\n"
                session.messages.append(ChatMessage(session_id=session.id, role="assistant", content=fb, id=uuid4(), timestamp=datetime.now()))
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        template = f"[Template] ขั้นตอน {step_name} สำหรับทักษะ {skill.name}"
        session.messages.append(ChatMessage(session_id=session.id, role="assistant", content=template, id=uuid4(), timestamp=datetime.now()))
        def fallback():
            yield f"data: {_json.dumps({'text':template,'done':True,'completed':completed})}\n\n"
        return StreamingResponse(fallback(), media_type="text/event-stream")


@api.get("/api/chat/{session_id}/progress")
def get_session_progress(session_id: str):
    try:
        return app_instance.get_chat_engine().summarize_progress(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@api.post("/api/assess-skill")
def assess_skill(req: AssessSkillRequest):
    from src.services import llm_client
    import json as _json
    try:
        skill = app_instance.get_skill_catalog().get_skill_detail(req.skill_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Skill not found")

    criteria_list = [{"area": c.name, "checklist": [it.description for it in c.checklist_items]} for c in skill.assessment_criteria]
    evidence = ""
    if req.completed_courses:
        evidence += "คอร์สที่เรียน:\n" + "\n".join(f"- {n}" for n in req.completed_courses) + "\n"
    if req.completed_todos:
        evidence += "To-Do สำเร็จ:\n" + "\n".join(f"- {n}" for n in req.completed_todos) + "\n"
    if not evidence:
        evidence = "ยังไม่มีเนื้อหาใน SuperPath"

    system_prompt = f"""คุณคือ Sorc AI ผู้ประเมินทักษะ ตอบเป็น JSON เท่านั้น
ทักษะ: {skill.name}
เกณฑ์: {_json.dumps(criteria_list, ensure_ascii=False)}
หลักฐาน: {evidence}
ตอบ JSON: {{"overall":"passed"|"partial"|"not_passed","overall_reason":"...","areas":[{{"area":"...","status":"passed"|"not_passed","reason":"...","checklist":[{{"item":"...","status":"passed"|"not_passed","note":"..."}}]}}],"recommendations":["..."]}}"""

    messages = [{"role": "user", "content": "ประเมินทักษะ"}]
    result_text = llm_client.chat_completion(system_prompt, messages, temperature=0.2)
    if result_text:
        try:
            clean = result_text.strip()
            # Strip markdown code fences: ```json ... ``` or ``` ... ```
            import re
            clean = re.sub(r'^```\w*\n?', '', clean)
            clean = re.sub(r'\n?```$', '', clean)
            clean = clean.strip()
            return {"assessment": _json.loads(clean), "raw": None}
        except Exception:
            # Try to find JSON object in the text
            try:
                start = result_text.index('{')
                end = result_text.rindex('}') + 1
                return {"assessment": _json.loads(result_text[start:end]), "raw": None}
            except Exception:
                return {"assessment": None, "raw": result_text}

    areas = [{"area": c.name, "status": "not_passed", "reason": "ไม่มีหลักฐาน",
              "checklist": [{"item": it.description, "status": "not_passed", "note": ""} for it in c.checklist_items]}
             for c in skill.assessment_criteria]
    return {"assessment": {"overall": "not_passed", "overall_reason": "ยังไม่มีเนื้อหา",
            "areas": areas, "recommendations": ["เพิ่มคอร์สใน SuperPath"]}, "raw": None}


# --- Spaced Repetition 2-7-30 Review System ---
from datetime import datetime, timedelta

# In-memory review schedule store: user_id -> list of review entries
_review_schedules: dict[str, list[dict]] = {}

class ScheduleReviewRequest(BaseModel):
    user_id: str
    skill_id: str
    skill_name: str

@api.post("/api/reviews/schedule")
def schedule_review(req: ScheduleReviewRequest):
    """Schedule 2-7-30 spaced repetition reviews for a completed skill."""
    now = datetime.now()
    reviews = [
        {"day": 2, "date": (now + timedelta(days=2)).isoformat(), "type": "quick_recall",
         "label": "ทบทวนครั้งที่ 1 (Day 2)", "status": "pending",
         "description": "ทบทวนแบบ Quick Recall — เขียนสิ่งที่จำได้โดยไม่ดูเนื้อหา"},
        {"day": 7, "date": (now + timedelta(days=7)).isoformat(), "type": "scenario",
         "label": "ทบทวนครั้งที่ 2 (Day 7)", "status": "pending",
         "description": "ทบทวนด้วยสถานการณ์จำลอง — AI จะสร้างโจทย์ให้คุณลองตอบ"},
        {"day": 30, "date": (now + timedelta(days=30)).isoformat(), "type": "deep_review",
         "label": "ทบทวนครั้งที่ 3 (Day 30)", "status": "pending",
         "description": "ทบทวนเชิงลึก — ประเมินทักษะอีกครั้งเพื่อยืนยันความเข้าใจ"},
    ]
    entry = {
        "skill_id": req.skill_id, "skill_name": req.skill_name,
        "scheduled_at": now.isoformat(), "reviews": reviews,
    }
    if req.user_id not in _review_schedules:
        _review_schedules[req.user_id] = []
    # Replace existing schedule for same skill
    _review_schedules[req.user_id] = [
        e for e in _review_schedules[req.user_id] if e["skill_id"] != req.skill_id
    ]
    _review_schedules[req.user_id].append(entry)
    return {"scheduled": True, "reviews": reviews}

@api.get("/api/reviews/{user_id}")
def get_reviews(user_id: str):
    """Get all review schedules for a user."""
    return {"reviews": _review_schedules.get(user_id, [])}

class StartReviewRequest(BaseModel):
    user_id: str
    skill_id: str
    review_day: int

@api.post("/api/reviews/start")
def start_review_session(req: StartReviewRequest):
    """Start a review chat session for a specific review interval."""
    entries = _review_schedules.get(req.user_id, [])
    entry = next((e for e in entries if e["skill_id"] == req.skill_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="No review schedule found")
    review = next((r for r in entry["reviews"] if r["day"] == req.review_day), None)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Start a chat session for the review
    try:
        session = app_instance.start_learning(req.user_id, req.skill_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    review["status"] = "in_progress"
    review_type_prompts = {
        "quick_recall": "นี่คือ Review Session Day 2 (Quick Recall) ให้ผู้เรียนเขียนสิ่งที่จำได้เกี่ยวกับทักษะนี้โดยไม่ดูเนื้อหา แล้วให้ feedback",
        "scenario": "นี่คือ Review Session Day 7 (Scenario) สร้างสถานการณ์จำลอง 2 ข้อเกี่ยวกับทักษะนี้ให้ผู้เรียนตอบ",
        "deep_review": "นี่คือ Review Session Day 30 (Deep Review) ประเมินทักษะเชิงลึก ถามคำถามที่ต้องใช้ความเข้าใจระดับสูง",
    }
    return {
        "session_id": str(session.id), "skill_id": req.skill_id,
        "review_type": review["type"], "review_label": review["label"],
        "prompt_hint": review_type_prompts.get(review["type"], ""),
        "messages": [{"role": m.role, "content": m.content} for m in session.messages],
    }

@api.post("/api/reviews/complete")
def complete_review(req: StartReviewRequest):
    """Mark a review as completed."""
    entries = _review_schedules.get(req.user_id, [])
    entry = next((e for e in entries if e["skill_id"] == req.skill_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="No review schedule found")
    review = next((r for r in entry["reviews"] if r["day"] == req.review_day), None)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review["status"] = "completed"
    review["completed_at"] = datetime.now().isoformat()
    return {"completed": True, "review": review}


# --- Fast-forward endpoint ---
@api.post("/api/chat/{session_id}/fast-forward")
def fast_forward_session(session_id: str):
    """Fast-forward through all learning steps, marking all checklist items complete."""
    try:
        engine = app_instance.get_chat_engine()
        session = engine._get_session(session_id)
        skill = app_instance.get_skill_catalog().get_skill_detail(str(session.skill_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Mark all checklist items complete
    completed = []
    for criteria in skill.assessment_criteria:
        for item in criteria.checklist_items:
            app_instance.get_progress_tracker().mark_checklist_item_complete(
                str(session.user_id), str(item.id)
            )
            completed.append(str(item.id))

    # Set session to WRAP_UP
    session.current_step = 6
    engine._area_indices[session_id] = len(skill.assessment_criteria) - 1

    # Add wrap-up message
    from src.models.chat import ChatMessage
    from uuid import uuid4
    wrap_msg = ChatMessage(
        session_id=session.id, role="assistant",
        content=(
            f"🎉 ยินดีด้วยครับ! คุณผ่าน checklist ครบทุกข้อของทักษะ **{skill.name}** แล้ว!\n\n"
            f"**สิ่งที่เราเรียนรู้ด้วยกัน:**\n"
            + "\n".join(f"✅ {c.name}" for c in skill.assessment_criteria)
            + f"\n\n📅 **แนะนำ:** ตั้งเวลาทบทวนตามหลัก 2-7-30 เพื่อให้จำได้ยาวนาน\n"
            f"กดปุ่ม 'ตั้งเวลาทบทวน 2-7-30' ด้านล่างเพื่อเริ่มต้นครับ"
        ),
        id=uuid4(), timestamp=datetime.now(),
    )
    session.messages.append(wrap_msg)

    progress = app_instance.get_progress_tracker().get_progress(str(session.user_id), skill)
    return {
        "completed_items": completed,
        "message": {"role": "assistant", "content": wrap_msg.content},
        "progress": {
            "percent_complete": progress.percent_complete,
            "completed_checklist_items": progress.completed_checklist_items,
            "total_checklist_items": progress.total_checklist_items,
        },
    }


# Serve frontend
FRONTEND_DIR = os.path.join(_ROOT, "frontend")
if os.path.exists(FRONTEND_DIR):
    api.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    @api.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
