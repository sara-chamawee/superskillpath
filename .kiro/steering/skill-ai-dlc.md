---
inclusion: manual
---

# Skill AI-DLC (AI-Driven Learning Companion)

## ภาพรวม

ระบบ Personalized Learning Path ที่ใช้ AI เป็นตัวขับเคลื่อนการเรียนรู้ผ่านการสนทนาแบบ Chat-based โดยผู้ใช้ทุกคนมีบทบาทเดียวกัน สามารถทั้งจัดการข้อมูลทักษะและเรียนรู้ทักษะได้

## แนวคิดหลัก

- ผู้ใช้ทุกคนเป็นทั้ง Learner และ Admin (single role)
- AI ขับเคลื่อนการเรียนรู้ (AI-driven) ผ่านระบบแชท ไม่ใช่ UI แบบดั้งเดิม
- ใช้ข้อมูลทักษะตั้งต้นจากไฟล์ Seed Data: `aidlc-skill-feat-skill-based-execution 3/Skills Name.md`
- ทักษะแต่ละตัวประกอบด้วย: ชื่อ, คำนิยาม, เกณฑ์การวัดผล (Areas of Measurement), Checklist

## โครงสร้างข้อมูลทักษะ (Skill Data Model)

แต่ละ Skill ประกอบด้วย:
- **Skills Name**: ชื่อทักษะ (เช่น Cognitive Flexibility, Analytical Thinking)
- **Skill Definition**: คำนิยามและรายละเอียดของทักษะ
- **Areas of Measurement**: เกณฑ์การวัดผล แบ่งเป็นหลายด้าน (เช่น ด้านที่ 1, 2, 3)
- **Checklist**: รายการตรวจสอบ 3-5 ข้อต่อแต่ละ Area of Measurement

หมายเหตุ: ทักษะหนึ่งตัวอาจมีหลาย Areas of Measurement และแต่ละ Area มี Checklist ของตัวเอง

## โมดูลหลัก

| โมดูล | หน้าที่ |
|-------|---------|
| Skill_Manager | CRUD ทักษะ (สร้าง อ่าน แก้ไข ลบ) |
| Skill_Catalog | แสดงรายการทักษะทั้งหมดให้ผู้ใช้เลือก |
| AI_Chat_Engine | สนทนากับผู้ใช้เพื่อนำทางการเรียนรู้ |
| Chat_Session | เซสชันสนทนาระหว่างผู้ใช้กับ AI สำหรับแต่ละทักษะ |
| Learning_Path | เส้นทางการเรียนรู้ที่ AI สร้างขึ้นจาก Assessment Criteria และ Checklist |
| Progress_Tracker | ติดตามความก้าวหน้าตาม Checklist |

## Flow หลัก

1. ระบบ seed ข้อมูลทักษะจากไฟล์ Skills Name.md เมื่อเริ่มต้นครั้งแรก
2. ผู้ใช้ดู Skill Catalog และเลือกทักษะที่ต้องการพัฒนา
3. ผู้ใช้กดเริ่มเรียน → เปิด Chat Session กับ AI
4. AI สร้าง Learning Path จาก Assessment Criteria + Checklist
5. AI นำทางการเรียนรู้ผ่านแชท: ให้เนื้อหา ถามคำถาม ให้แบบฝึกหัด
6. AI อัปเดต Progress ตาม Checklist ที่ผู้ใช้ทำสำเร็จ
7. เมื่อ Checklist ครบ → ผู้ใช้บรรลุทักษะ

## หลักการออกแบบ

- AI-first: AI เป็นผู้ขับเคลื่อนการเรียนรู้ ไม่ใช่ผู้ใช้นำทางเอง
- Chat-based UX: การเรียนรู้เกิดขึ้นผ่านการสนทนา ไม่ใช่หน้า UI แบบ step-by-step
- Proactive AI: AI ถามคำถาม ให้แบบฝึกหัด แนะนำขั้นตอนถัดไปโดยอัตโนมัติ
- Personalized: AI ปรับเนื้อหาตามพื้นฐานและความเข้าใจของผู้ใช้แต่ละคน

## ไฟล์อ้างอิง

- Seed Data: `aidlc-skill-feat-skill-based-execution 3/Skills Name.md`
- Spec: `.kiro/specs/personalized-learning-path/`
