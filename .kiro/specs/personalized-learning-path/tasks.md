# แผนการ Implement: Personalized Learning Path

## ภาพรวม

Implement ระบบ Personalized Learning Path ด้วย Python โดยแบ่งเป็นขั้นตอนที่ต่อเนื่องกัน เริ่มจาก Data Models → Seed Data Parser → Skill Manager → Skill Catalog → AI Chat Engine → Progress Tracker แล้วเชื่อมทุกส่วนเข้าด้วยกัน ใช้ข้อมูลทักษะจากไฟล์ `Skills Name.md` และข้อมูลคอร์สจากไฟล์ `skill-content-mapping.md` เป็น Seed Data

## Tasks

- [x] 1. สร้างโครงสร้างโปรเจกต์และ Data Models
  - [x] 1.1 สร้างโครงสร้างไดเรกทอรีและไฟล์ตั้งต้น
    - สร้างโฟลเดอร์ `src/`, `src/models/`, `src/services/`, `src/parsers/`, `tests/`
    - สร้างไฟล์ `requirements.txt` พร้อม dependencies (pytest, hypothesis สำหรับ property-based testing)
    - สร้างไฟล์ `src/__init__.py`, `src/models/__init__.py`, `src/services/__init__.py`, `src/parsers/__init__.py`, `tests/__init__.py`
    - _Requirements: ทั้งหมด_

  - [x] 1.2 Implement Data Models ทั้งหมด
    - สร้างไฟล์ `src/models/skill.py` — class `Skill`, `AssessmentCriteria`, `ChecklistItem` พร้อม fields ตาม ER Diagram ในเอกสารออกแบบ
    - สร้างไฟล์ `src/models/course.py` — class `Course` ที่ผูกกับ Skill (courseCode, name, contentProvider, instructorName, duration, orderIndex)
    - สร้างไฟล์ `src/models/user.py` — class `User`, `UserSelectedSkill`, `UserChecklistProgress`
    - สร้างไฟล์ `src/models/chat.py` — class `ChatSession`, `ChatMessage`, `LearningPath`, `LearningStep`
    - สร้างไฟล์ `src/models/errors.py` — class `ValidationError`, `NotFoundError`
    - ทุก model ใช้ dataclass หรือ Pydantic model พร้อม type hints
    - _Requirements: 1.2, 1.5.2, 2.2, 3.2, 5.2_

  - [ ]* 1.3 เขียน property test สำหรับ Skill CRUD Round-Trip
    - **Property 4: Skill CRUD Round-Trip** — สร้าง Skill ด้วยข้อมูลที่ถูกต้องแล้วดึงกลับมา ต้องได้ข้อมูลตรงกัน
    - **Validates: Requirements 2.2, 3.2**

  - [ ]* 1.4 เขียน property test สำหรับ Validation ปฏิเสธข้อมูลไม่สมบูรณ์
    - **Property 7: Validation ปฏิเสธข้อมูลทักษะที่ไม่สมบูรณ์** — ข้อมูลที่ขาด field จำเป็นต้องถูกปฏิเสธพร้อม ValidationError
    - **Validates: Requirements 2.7, 3.4**

- [x] 2. Implement Seed Data Parser
  - [x] 2.1 Implement Skills Seed Data Parser
    - สร้างไฟล์ `src/parsers/skill_seed_parser.py`
    - Implement function `parse(file_content: str) -> ParseResult` ที่อ่านตาราง Markdown จากไฟล์ `Skills Name.md`
    - จัดการ multi-row merging: แถวที่ Skills Name ว่าง = Area of Measurement เพิ่มเติมของทักษะก่อนหน้า
    - Parse Checklist items ที่คั่นด้วย `\-` ในแต่ละ cell
    - Implement function `should_import(catalog_size: int) -> bool` ที่คืน False เมื่อ catalog มีข้อมูลแล้ว
    - ข้ามแถวที่ไม่สมบูรณ์ (ไม่มี Areas of Measurement หรือ Checklist) พร้อมบันทึก skipped rows
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [x] 2.2 Implement Course Content Parser
    - สร้างไฟล์ `src/parsers/course_content_parser.py`
    - Implement function `parse_courses(file_content: str) -> list[Course]` ที่อ่านตาราง Markdown จากไฟล์ `skill-content-mapping.md`
    - จับคู่คอร์สกับทักษะที่ตรงกัน โดยแถวที่มี Skill = ชื่อทักษะ เป็นแถวสรุป, แถวที่ Skill ว่าง = คอร์สย่อย
    - บันทึก Course ID, ชื่อคอร์ส, Content Provider, Instructor Name, Duration, To Do List Type, To-Do link
    - _Requirements: 1.5.1, 1.5.2, 1.5.3, 1.5.4_

  - [ ]* 2.3 เขียน property test สำหรับ Seed Data Parsing
    - **Property 1: Seed Data Parsing จับคู่คอลัมน์ถูกต้อง** — แถวข้อมูลที่ถูกต้อง parse แล้วต้องได้ Skill object ที่มี fields ตรงกัน
    - **Validates: Requirements 1.2**

  - [ ]* 2.4 เขียน property test สำหรับ Incomplete Seed Data
    - **Property 2: แถว Seed Data ที่ไม่สมบูรณ์ถูกข้ามพร้อม log** — จำนวน skills ที่ได้ต้องเท่ากับแถวที่สมบูรณ์ และ skipped rows ต้องเท่ากับแถวที่ไม่สมบูรณ์
    - **Validates: Requirements 1.4**

  - [ ]* 2.5 เขียน property test สำหรับ Import Idempotency
    - **Property 3: การนำเข้า Seed Data เป็น Idempotent** — เมื่อ catalog มีข้อมูลแล้ว should_import ต้องคืน False
    - **Validates: Requirements 1.5**

- [x] 3. Checkpoint — ตรวจสอบ Seed Data Parser
  - ตรวจสอบว่า tests ทั้งหมดผ่าน ถามผู้ใช้หากมีข้อสงสัย

- [x] 4. Implement Skill Manager Service
  - [x] 4.1 Implement Skill Manager CRUD
    - สร้างไฟล์ `src/services/skill_manager.py`
    - Implement class `SkillManagerService` พร้อม methods: `create_skill()`, `update_skill()`, `delete_skill()`, `get_skill()`
    - Implement validation: ชื่อทักษะต้องไม่ว่าง, รายละเอียดต้องไม่ว่าง, ต้องมี assessment criteria อย่างน้อย 1 รายการ, แต่ละ criteria ต้องมี checklist items อย่างน้อย 1 รายการ
    - คืน `ValidationError` เมื่อข้อมูลไม่ถูกต้อง, คืน `NotFoundError` เมื่อไม่พบทักษะ
    - ใช้ in-memory storage (dict) สำหรับ prototype
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4_

  - [ ]* 4.2 เขียน property test สำหรับ Skill Update
    - **Property 5: การอัปเดตทักษะสะท้อนผลถูกต้อง** — อัปเดตแล้วดึงกลับมาต้องได้ข้อมูลใหม่
    - **Validates: Requirements 2.4**

  - [ ]* 4.3 เขียน property test สำหรับ Skill Deletion
    - **Property 6: การลบทักษะออกจาก Catalog** — ลบแล้วต้องไม่พบทักษะนั้น และจำนวนลดลง 1
    - **Validates: Requirements 2.6**

  - [ ]* 4.4 เขียน unit tests สำหรับ Skill Manager
    - ทดสอบสร้างทักษะด้วยชื่อว่าง → ได้ ValidationError
    - ทดสอบสร้างทักษะด้วย Checklist 0 รายการ → ได้ ValidationError
    - ทดสอบลบ checklist item จากทักษะที่มี 2 items → เหลือ 1 item
    - ทดสอบแก้ไข/ลบทักษะที่ไม่มีอยู่ → ได้ NotFoundError
    - _Requirements: 2.7, 3.3, 3.4_

- [x] 5. Implement Skill Catalog Service
  - [x] 5.1 Implement Skill Catalog
    - สร้างไฟล์ `src/services/skill_catalog.py`
    - Implement class `SkillCatalogService` พร้อม methods: `list_skills()`, `get_skill_detail()`, `select_skills_for_learning()`, `get_selected_skills()`
    - `list_skills()` แสดงทักษะทั้งหมด (ทั้งจาก Seed Data และสร้างเพิ่มเติม)
    - `get_skill_detail()` แสดงรายละเอียดครบทุก field รวม Assessment Criteria และ Checklist
    - `select_skills_for_learning()` บันทึกทักษะที่ผู้ใช้เลือก (รองรับหลายทักษะ)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.2 เขียน property test สำหรับ Catalog Completeness
    - **Property 8: Catalog แสดงทักษะทั้งหมดครบถ้วน** — ทักษะทั้งหมดที่สร้างต้องปรากฏใน catalog
    - **Validates: Requirements 1.3, 4.1**

  - [ ]* 5.3 เขียน property test สำหรับ Skill Detail Completeness
    - **Property 9: รายละเอียดทักษะแสดงข้อมูลครบทุกฟิลด์** — ดูรายละเอียดต้องแสดง Assessment Criteria และ Checklist ครบ
    - **Validates: Requirements 4.2**

  - [ ]* 5.4 เขียน property test สำหรับ Skill Selection Persistence
    - **Property 10: การเลือกทักษะหลายรายการถูกบันทึกครบถ้วน** — เลือกทักษะแล้วดึงกลับมาต้องได้ครบ
    - **Validates: Requirements 4.3, 4.4**

- [x] 6. Checkpoint — ตรวจสอบ Skill Manager และ Catalog
  - ตรวจสอบว่า tests ทั้งหมดผ่าน ถามผู้ใช้หากมีข้อสงสัย

- [x] 7. Implement Progress Tracker Service
  - [x] 7.1 Implement Progress Tracker
    - สร้างไฟล์ `src/services/progress_tracker.py`
    - Implement class `ProgressTrackerService` พร้อม methods: `get_progress()`, `mark_checklist_item_complete()`, `get_all_progress()`, `is_skill_completed()`
    - คำนวณ `percent_complete` = (completed / total) × 100
    - `is_skill_completed()` คืน True เมื่อ checklist ครบทุกรายการ
    - การ mark item ที่สำเร็จแล้วซ้ำต้องเป็น idempotent (ไม่เปลี่ยนแปลงสถานะ)
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 7.2 เขียน property test สำหรับ Progress Percentage
    - **Property 13: การคำนวณเปอร์เซ็นต์ความก้าวหน้าถูกต้อง** — (C / T) × 100 ต้องถูกต้องเสมอ
    - **Validates: Requirements 7.2, 7.4**

  - [ ]* 7.3 เขียน property test สำหรับ Skill Completion
    - **Property 14: ทักษะสำเร็จเมื่อ Checklist ครบ** — ครบทุกข้อ = True, ไม่ครบ = False
    - **Validates: Requirements 7.3**

  - [ ]* 7.4 เขียน property test สำหรับ Progress Status Completeness
    - **Property 15: Progress แสดงสถานะ Checklist ครบทุกรายการ** — จำนวน checklistStatus ต้องเท่ากับจำนวน checklist items ทั้งหมด
    - **Validates: Requirements 7.1**

  - [ ]* 7.5 เขียน unit tests สำหรับ Progress Tracker
    - ทดสอบ checklist ครบ 100% → isCompleted = True
    - ทดสอบ checklist 0% → percentComplete = 0, isCompleted = False
    - ทดสอบ mark item ซ้ำ → ไม่เปลี่ยนแปลง (idempotent)
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 8. Implement AI Chat Engine Service
  - [x] 8.1 Implement Chat Session Management
    - สร้างไฟล์ `src/services/ai_chat_engine.py`
    - Implement class `AIChatEngineService` พร้อม methods: `start_session()`, `send_message()`, `get_session_history()`, `get_learning_path()`, `summarize_progress()`
    - `start_session()` สร้าง ChatSession แยกต่อทักษะ พร้อมสร้าง LearningPath จาก Assessment Criteria + Checklist
    - LearningPath ต้องครอบคลุม checklist items ทั้งหมดของทักษะ
    - _Requirements: 4.5, 5.1, 5.2, 5.4_

  - [x] 8.2 Implement 7-Step Learning Flow
    - Implement logic สำหรับ 7 ขั้นตอนการเรียนรู้ตามเอกสารออกแบบ:
      - Step 1: แนะนำตัวและอธิบายภาพรวมทักษะ
      - Step 2: ประเมินพื้นฐานผู้เรียน
      - Step 3: สร้างแผนการเรียนรู้เฉพาะบุคคล
      - Step 4: ให้เนื้อหาและอธิบายแนวคิด (วนซ้ำตาม Area)
      - Step 5: ให้แบบฝึกหัดและสถานการณ์จำลอง (วนซ้ำตาม Area)
      - Step 6: ประเมินผลและอัปเดต Checklist (วนซ้ำตาม Area)
      - Step 7: สรุปผลและแนะนำขั้นตอนถัดไป
    - Implement loop rules: Step 4→5→6 วนซ้ำสำหรับแต่ละ Area of Measurement
    - สร้าง system prompt ที่มีข้อมูลทักษะ (definition, criteria, checklist) + ข้อมูล Course ที่ผูกกับทักษะเป็นบริบท
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 6.1, 6.2, 6.3, 6.4_

  - [x] 8.3 Implement Course Recommendation ใน Chat
    - เพิ่ม logic ให้ AI แนะนำคอร์สเรียนที่เกี่ยวข้องกับขั้นตอนการเรียนรู้ปัจจุบัน
    - ใส่ข้อมูล Course (ชื่อคอร์ส, ผู้สอน, ระยะเวลา) ใน system prompt ของ AI
    - รองรับทั้ง assessment type: "Submit Assignment File" และ "Chat to Assess"
    - _Requirements: 1.5.5, 1.5.6_

  - [x] 8.4 Implement Inactivity Nudge
    - Implement logic ตรวจสอบ `last_activity_at` ของ ChatSession
    - เมื่อไม่มี activity เกิน threshold → สร้างข้อความกระตุ้นให้ผู้ใช้กลับมาเรียนต่อ
    - _Requirements: 6.5_

  - [ ]* 8.5 เขียน property test สำหรับ Separate Chat Sessions
    - **Property 11: Chat Session แยกต่อทักษะ** — เลือก N ทักษะ ต้องได้ N sessions แยกกัน
    - **Validates: Requirements 4.5, 5.4**

  - [ ]* 8.6 เขียน property test สำหรับ Learning Path Coverage
    - **Property 12: Learning Path ครอบคลุม Checklist ทั้งหมด** — relatedChecklistItems รวมกันต้องครอบคลุม checklist items ทั้งหมด
    - **Validates: Requirements 5.2**

  - [ ]* 8.7 เขียน unit tests สำหรับ AI Chat Engine
    - ทดสอบเริ่มเรียนทักษะ → สร้าง ChatSession สำเร็จ
    - ทดสอบ session ไม่มี activity เกิน threshold → trigger nudge
    - _Requirements: 4.5, 6.5_

- [x] 9. Checkpoint — ตรวจสอบ AI Chat Engine และ Progress Tracker
  - ตรวจสอบว่า tests ทั้งหมดผ่าน ถามผู้ใช้หากมีข้อสงสัย

- [x] 10. เชื่อมทุกส่วนเข้าด้วยกัน
  - [x] 10.1 สร้าง Application Entry Point
    - สร้างไฟล์ `src/app.py` เป็น main entry point
    - เชื่อม Seed Data Parser → Skill Catalog (นำเข้าข้อมูลตั้งต้นเมื่อเริ่มระบบครั้งแรก)
    - เชื่อม Course Content Parser → Skill (นำเข้าข้อมูลคอร์สที่ผูกกับทักษะ)
    - เชื่อม Skill Manager → Skill Catalog (CRUD สะท้อนผลใน catalog)
    - เชื่อม Skill Catalog → AI Chat Engine (เลือกทักษะ → เริ่ม chat session)
    - เชื่อม AI Chat Engine → Progress Tracker (อัปเดต checklist จากการสนทนา)
    - _Requirements: 1.1, 1.3, 1.5.1, 4.5, 7.2_

  - [ ]* 10.2 เขียน integration tests
    - ทดสอบ flow: seed data → catalog → เลือกทักษะ → เริ่ม chat → อัปเดต progress
    - ทดสอบ flow: สร้างทักษะใหม่ → ปรากฏใน catalog → เลือกเรียน
    - _Requirements: 1.1, 1.3, 4.1, 4.5, 7.2_

- [x] 11. Checkpoint สุดท้าย — ตรวจสอบทั้งระบบ
  - ตรวจสอบว่า tests ทั้งหมดผ่าน ถามผู้ใช้หากมีข้อสงสัย

## หมายเหตุ

- Tasks ที่มีเครื่องหมาย `*` เป็น optional สามารถข้ามได้เพื่อ MVP ที่เร็วขึ้น
- แต่ละ task อ้างอิง requirements เฉพาะเพื่อให้ตรวจสอบย้อนกลับได้
- Checkpoints ช่วยให้ตรวจสอบความถูกต้องเป็นระยะ
- Property tests ใช้ library `hypothesis` สำหรับ Python
- Unit tests ใช้ `pytest`
- ใช้ in-memory storage (dict) สำหรับ prototype — สามารถเปลี่ยนเป็น database จริงได้ภายหลัง
