# SuperPath — Personalized Learning Path with AI Coach

ระบบเส้นทางการเรียนรู้แบบ Personalized ที่ใช้ AI เป็นตัวขับเคลื่อนการเรียนรู้ผ่านการสนทนาแบบ Chat-based

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# แก้ไข .env ใส่ Gemini API key

# 3. Run server
python -m uvicorn src.api:api --host 0.0.0.0 --port 8888 --reload

# 4. Open browser
open http://localhost:8888
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `PORT` | Server port (optional) | `8888` |

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **AI**: Google Gemini 2.5 Flash (streaming)
- **Frontend**: Vanilla HTML/JS, Marked.js (markdown), Web Speech API (TTS)
- **Testing**: pytest, hypothesis (property-based testing)

## Project Structure

```
src/
  api.py                    # FastAPI endpoints (REST + SSE streaming)
  app.py                    # Application entry point, wires all services
  models/                   # Data models (dataclasses)
    skill.py                # Skill, AssessmentCriteria, ChecklistItem
    course.py               # Course
    user.py                 # User, UserSelectedSkill, UserChecklistProgress
    chat.py                 # ChatSession, ChatMessage, LearningPath, LearningStep
    errors.py               # ValidationError, NotFoundError
  services/                 # Business logic
    skill_manager.py        # CRUD operations for skills
    skill_catalog.py        # Catalog browsing, skill selection, course lookup
    progress_tracker.py     # Checklist progress tracking
    ai_chat_engine.py       # 7-step AI learning flow
    llm_client.py           # Gemini API wrapper
  parsers/                  # Seed data parsers
    skill_seed_parser.py    # Parses Skills Name.md (skills + criteria + checklist)
    course_content_parser.py # Parses skill-content-mapping.md
    skill_courses_parser.py # Parses skill-courses.md (skill → course mapping)
frontend/
  index.html                # Single-page app (all-in-one HTML/CSS/JS)
seed-data/
  skills-name.md            # Skill definitions with assessment criteria & checklist
  skill-courses.md          # Skill → Course content mapping
  skill-content-mapping.md  # Additional course metadata
tests/                      # pytest test suite
.kiro/
  specs/                    # Feature specifications (requirements, design, tasks)
  steering/                 # AI steering rules for development
```

## Features

### 1. Skill Catalog
- 200+ ทักษะจาก seed data พร้อม search + pagination
- แต่ละทักษะมี: ชื่อ, คำนิยาม, เกณฑ์การวัดผล (Areas of Measurement), Checklist

### 2. AI-Driven Learning (3 Modes)
เมื่อเข้าทักษะ AI จะถามรูปแบบการเรียน:
- **📚 เรียนคอร์สก่อน** → AI แนะนำคอร์สจาก content library
- **🎯 จำลองสถานการณ์** → AI สรุปสิ่งสำคัญ แล้วสร้าง use case ให้ตอบ
- **🛠️ ลงมือทำจริง** → AI สร้าง To-Do List ให้ทำแล้วส่งงาน

### 3. SuperPath Builder
- ผู้เรียนเลือกเนื้อหาเพิ่มเข้า SuperPath จาก:
  - คอร์สที่ admin สร้างไว้
  - เนื้อหาที่ AI แนะนำ (content cards ในแชท)
  - To-Do List ที่ AI สร้าง
- Sidebar แสดงเนื้อหาใน SuperPath

### 4. AI Skill Assessment
- ปุ่ม "🎯 ประเมินทักษะ" เทียบผลการเรียนใน SuperPath กับ criteria
- แสดงผลเป็น checklist: แต่ละด้าน + แต่ละข้อ ผ่าน/ไม่ผ่าน + เหตุผล
- คำแนะนำสิ่งที่ต้องเรียนเพิ่ม

### 5. Chat Features
- Streaming response (SSE) — เห็นคำตอบทีละคำ
- Markdown rendering
- Text-to-Speech (🔊) — อ่านออกเสียงภาษาไทย
- Content suggestion cards — กดเพิ่มเข้า SuperPath ได้เลยในแชท
- Expandable chat panel — กางทับ content area ได้

### 6. To-Do List + AI Verify
- AI สร้าง To-Do List สำหรับฝึกทักษะ
- ผู้เรียนแนบไฟล์งาน → กด "🤖 ให้ AI ตรวจ"

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/skills?q=&page=&limit=` | List skills (paginated, searchable) |
| GET | `/api/skills/{id}` | Skill detail + courses |
| POST | `/api/chat/start` | Start chat session |
| POST | `/api/chat/{id}/stream` | Send message (streaming SSE) |
| POST | `/api/chat/{id}/message` | Send message (non-streaming) |
| GET | `/api/chat/{id}/progress` | Get progress |
| POST | `/api/assess-skill` | AI skill assessment |

## Seed Data Format

### Skills Name.md
```
| Skills Name | Skill Definition | Areas or Measurement | Checklist (3-5 points) |
| Cognitive Flexibility | คำนิยาม... | 1\. การคิดวิเคราะห์... | \- checklist item 1 \- item 2 |
|  |  | 2\. การปรับเปลี่ยน... | \- checklist item 1 \- item 2 |
```
- แถวที่มี Skills Name = ทักษะใหม่
- แถวที่ Skills Name ว่าง = Area of Measurement เพิ่มเติม

### skill-courses.md
```
| Skill | Course ID | Course Name | Content Provider | Instructor |
| Cognitive Flexibility | DEO21C018 | ชื่อคอร์ส | Provider | ผู้สอน |
```

## Testing

```bash
pytest -v          # Run all tests
pytest -v -k test_skill_manager  # Run specific test file
```

## Architecture Decisions

- **In-memory storage** — prototype ใช้ dict เก็บข้อมูล สามารถเปลี่ยนเป็น database ได้ภายหลัง
- **Single HTML frontend** — ไม่ใช้ framework เพื่อความเร็วในการ prototype
- **Gemini streaming** — ใช้ SSE (Server-Sent Events) สำหรับ real-time response
- **Template fallback** — ถ้าไม่มี API key จะใช้ template responses แทน
