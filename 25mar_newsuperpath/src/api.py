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

    system_prompt = f"""คุณคือ Sorc AI Learning Companion ภาษาไทย ใช้ markdown
ทักษะ: {skill.name} | ด้าน: {area_name} | ขั้นตอน: {step_name}
คำนิยาม: {skill.definition[:200]}
ตอบกระชับ ใช้ตัวอย่างจริง ถามคำถามกระตุ้นการคิด ตอบให้ครบถ้วนทุกประเด็น"""

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


# Serve frontend
FRONTEND_DIR = os.path.join(_ROOT, "frontend")
if os.path.exists(FRONTEND_DIR):
    api.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    @api.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
