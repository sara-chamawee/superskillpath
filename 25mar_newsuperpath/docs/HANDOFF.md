# Handoff Guide — SuperPath

เอกสารนี้สำหรับทีมที่จะรับช่วงต่อ project SuperPath

## สิ่งที่ทำเสร็จแล้ว (Prototype)

### Backend (Python/FastAPI)
- ✅ Data Models ครบ (Skill, Course, User, Chat, Progress)
- ✅ Seed Data Parsers 3 ตัว (skills, courses, skill-course mapping)
- ✅ Skill Manager Service (CRUD + validation)
- ✅ Skill Catalog Service (browse, search, select, course lookup)
- ✅ Progress Tracker Service (checklist tracking, percent calculation)
- ✅ AI Chat Engine (7-step learning flow, streaming, course recommendation)
- ✅ LLM Client (Gemini 2.5 Flash, streaming, fallback)
- ✅ REST API + SSE Streaming endpoints
- ✅ AI Skill Assessment (criteria-based, JSON structured)
- ✅ Unit tests (100+ tests)

### Frontend (HTML/JS)
- ✅ Skill Catalog with search + pagination
- ✅ 3-column learning view (sidebar + content + chat)
- ✅ 3 learning modes (courses, scenario, hands-on)
- ✅ SuperPath builder (add/remove courses + to-do)
- ✅ Streaming chat with markdown
- ✅ Content suggestion cards in chat
- ✅ AI skill assessment UI (criteria checklist)
- ✅ Text-to-Speech
- ✅ Expandable chat panel

## สิ่งที่ต้องทำต่อ (Production)

### Priority 1 — Database & Auth
- [ ] เปลี่ยนจาก in-memory storage เป็น database จริง (PostgreSQL/MongoDB)
- [ ] เพิ่ม user authentication (JWT/OAuth)
- [ ] เก็บ chat history ใน database
- [ ] เก็บ SuperPath ของแต่ละ user ใน database

### Priority 2 — Admin Panel
- [ ] สร้างหน้า admin สำหรับจัดการ skills (CRUD UI)
- [ ] สร้างหน้า admin สำหรับจัดการ courses (upload, link to skills)
- [ ] Dashboard แสดงสถิติการเรียนของ users

### Priority 3 — AI Enhancement
- [ ] ปรับ system prompt ให้ดีขึ้นตาม feedback
- [ ] เพิ่ม RAG (Retrieval-Augmented Generation) สำหรับ course content
- [ ] AI verify ไฟล์งานจริง (อ่าน PDF/image)
- [ ] เพิ่ม conversation memory ข้าม session

### Priority 4 — UX/UI
- [ ] แยก frontend เป็น React/Next.js
- [ ] Responsive design สำหรับ mobile
- [ ] Dark mode
- [ ] Notification system (nudge กลับมาเรียน)

### Priority 5 — Infrastructure
- [ ] Deploy บน cloud (AWS/GCP)
- [ ] CI/CD pipeline
- [ ] Monitoring & logging
- [ ] Rate limiting สำหรับ Gemini API

## Key Files ที่ต้องรู้

| File | ทำอะไร | ต้องแก้เมื่อ |
|------|--------|-------------|
| `src/api.py` | API endpoints ทั้งหมด | เพิ่ม endpoint ใหม่ |
| `src/app.py` | Wire services + load seed data | เปลี่ยน data source |
| `src/services/ai_chat_engine.py` | 7-step learning flow | ปรับ AI behavior |
| `src/services/llm_client.py` | Gemini API wrapper | เปลี่ยน LLM provider |
| `src/services/skill_manager.py` | Skill CRUD | เปลี่ยนเป็น database |
| `src/services/progress_tracker.py` | Progress tracking | เปลี่ยนเป็น database |
| `frontend/index.html` | UI ทั้งหมด | แยกเป็น React components |
| `seed-data/` | ข้อมูลตั้งต้น | เปลี่ยนเป็น database seeder |

## Data Flow

```
User → Frontend (index.html)
  → API (api.py)
    → App (app.py) wires:
      → SkillCatalog → SkillManager (CRUD)
      → AIChatEngine → LLMClient (Gemini)
      → ProgressTracker
    → Parsers load seed data on startup
```

## Spec Documents

อ่านเพิ่มเติมที่:
- `.kiro/specs/personalized-learning-path/requirements.md` — ข้อกำหนดทั้งหมด
- `.kiro/specs/personalized-learning-path/design.md` — สถาปัตยกรรม, data models, 7-step flow
- `.kiro/specs/personalized-learning-path/tasks.md` — task list ที่ implement แล้ว
- `.kiro/steering/skill-ai-dlc.md` — domain context ของระบบ

## Environment Setup

1. Python 3.10+ required
2. `pip install -r requirements.txt`
3. Copy `.env.example` → `.env` แล้วใส่ Gemini API key
4. Gemini API key สร้างได้ที่: https://aistudio.google.com/apikey
5. Model ที่ใช้: `gemini-2.5-flash`

## Testing

```bash
pytest -v                    # ทุก test
pytest -v tests/test_app.py  # Integration test (full flow)
```

Test ครอบคลุม: Seed data parsing, Skill CRUD, Catalog, Progress tracking, Chat engine
