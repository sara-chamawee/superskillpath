import { useState, useCallback, useRef } from 'react';
import Nav from './components/Nav';
import SkillCatalog from './components/SkillCatalog';
import Sidebar from './components/Sidebar';
import ContentArea from './components/ContentArea';
import ChatPanel from './components/ChatPanel';
import AdminSkillPath from './components/AdminSkillPath';
import { fetchSkillDetail, startChat, fetchProgress, assessSkill, streamMessage } from './utils/api';

const UID = 'user-' + Math.random().toString(36).substr(2, 6);
const now = () => new Date().toLocaleString('th-TH', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

export default function App() {
  const [view, setView] = useState('catalog');
  const [skill, setSkill] = useState(null);
  const [courses, setCourses] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatExpanded, setChatExpanded] = useState(false);
  const [path, setPath] = useState([]);
  const [todos, setTodos] = useState([]);
  const [simulations, setSimulations] = useState([]);
  const [progress, setProgress] = useState({});
  const [contentView, setContentView] = useState('overview');
  const [contentData, setContentData] = useState({});
  const chatSendRef = useRef(null);

  const [showContent, setShowContent] = useState(true);
  const [learningMode, setLearningMode] = useState(null);
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [quizzes, setQuizzes] = useState([]); // quiz sets: [{ id, title, day, createdAt, questions: [...] }]
  const [badgeEarned, setBadgeEarned] = useState(false);
  const [reviewRounds, setReviewRounds] = useState([
    { day: 2, label: 'Day 2', desc: 'Quick Recall — เรียกคืนสิ่งที่เรียนไปเมื่อ 2 วันก่อน', icon: '📋', quizId: null, status: 'pending' },
    { day: 7, label: 'Day 7', desc: 'Scenario — AI สร้างสถานการณ์ให้คุณตอบ', icon: '🎯', quizId: null, status: 'pending' },
    { day: 30, label: 'Day 30', desc: 'Deep Review — ประเมินว่าจำได้จริงในระยะยาว', icon: '📊', quizId: null, status: 'pending' },
  ]);

  const goHome = () => { setView('catalog'); setSkill(null); setSessionId(null); setPath([]); setTodos([]); setSimulations([]); setQuizzes([]); setChatExpanded(false); setShowContent(true); setLearningMode(null); setBadgeEarned(false); setReviewRounds(prev => prev.map(r => ({ ...r, quizId: null, status: 'pending' }))); };
  const goAdmin = () => setView('admin');

  const toggleSelectSkill = (s) => {
    setSelectedSkills(prev => prev.find(x => x.id === s.id) ? prev.filter(x => x.id !== s.id) : [...prev, s]);
  };

  const openSkill = async (id) => {
    const sd = await fetchSkillDetail(id);
    setSkill(sd); setCourses(sd.courses || []);
    setView('learn'); setContentView('overview');
    setShowContent(true); setChatExpanded(false); setLearningMode('auto');
    const cd = await startChat(UID, id);
    setSessionId(cd.session_id);

    // Auto-add courses to path (10%)
    const newPath = (sd.courses || []).map((c, i) => ({ type: 'course', idx: i, name: c.name, in: true }));
    setPath(newPath);

    // Auto-create simulation from first criteria (20%)
    const criteria = sd.assessment_criteria || [];
    const newSim = criteria.length > 0 ? [{
      title: `${sd.name} — Simulation 1`,
      scenario: `สถานการณ์จำลองสำหรับด้าน "${criteria[0].name}"\n\nAI Coach กำลังสร้างสถานการณ์ให้... กดปุ่ม "🔄 เปลี่ยนสถานการณ์" เพื่อให้ AI สร้างโจทย์ใหม่`,
      done: false, result: null, confirmed: false, attempts: [],
      criteriaIdx: 0, criteriaName: criteria[0].name,
    }] : [];
    setSimulations(newSim);

    // Auto-create todo list (70%)
    const newTodos = criteria.slice(0, 3).map((c, i) => ({
      title: `ฝึก${c.name}`,
      desc: `ลงมือฝึกทักษะด้าน "${c.name}" โดยนำไปใช้ในสถานการณ์จริง\n\nChecklist:\n${c.checklist_items?.map(it => `- ${it.description}`).join('\n') || ''}`,
      ok: false, attempts: [],
    }));
    setTodos(newTodos);

    // AI greeting only — no system command
    const msgs = cd.messages.map(m => ({ role: m.role, content: m.content, time: now() }));
    msgs.push({ role: 'assistant', time: now(), content: `📋 ฉันได้สร้างแผนการเรียนตาม **10-20-70** ให้คุณแล้วครับ!\n\n- 📚 **10% เนื้อหา** — ${newPath.length} คอร์สเพิ่มเข้า SuperPath แล้ว\n- 🎯 **20% Simulation** — กำลังสร้างสถานการณ์จำลองให้...\n- 🛠️ **70% To-Do** — ${newTodos.length} รายการพร้อมให้ลงมือทำ\n\nดูเส้นทางการเรียนได้ที่ sidebar ด้านซ้ายเลยครับ ถ้ามีคำถามหรืออยากให้ช่วยอะไร บอกได้เลย! 😊` });
    setMessages(msgs);
    updateProg(cd.session_id);

    // Auto-generate real simulation scenario silently (no user message shown)
    if (criteria.length > 0) {
      const simPrompt = `สร้างสถานการณ์จำลอง 1 ข้อสำหรับทักษะ "${sd.name}" ด้าน "${criteria[0].name}" ให้เป็นสถานการณ์ที่เหมือนจริงในการทำงาน อธิบายบริบทให้ชัดเจน แล้วถามคำถามให้ฉันตอบ`;
      try {
        const simRes = await streamMessage(cd.session_id, simPrompt);
        const reader = simRes.body.getReader();
        const dec = new TextDecoder();
        let simFull = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          for (const line of dec.decode(value).split('\n').filter(l => l.startsWith('data: '))) {
            try { const d = JSON.parse(line.slice(6)); if (d.text) simFull += d.text; } catch {}
          }
        }
        if (simFull.length > 50) {
          setSimulations(prev => prev.map((s, i) => i === 0 ? { ...s, scenario: simFull } : s));
          setMessages(prev => {
            // Update the greeting message to show simulation is ready
            return prev.map(m => m.content?.includes('กำลังสร้างสถานการณ์จำลองให้')
              ? { ...m, content: m.content.replace('กำลังสร้างสถานการณ์จำลองให้...', `สถานการณ์จำลอง ${newSim.length} ข้อพร้อมแล้ว`) }
              : m);
          });
        }
      } catch {}
    }
  };

  const pickMode = (mode) => {
    setLearningMode(mode);
    setShowContent(true); setChatExpanded(false);
    const labels = { courses: '📚 เรียนคอร์สก่อน', scenario: '🎯 จำลองสถานการณ์', todo: '🛠️ ลงมือทำจริง', auto: '🤖 AI จัดให้ตาม 10-20-70' };
    setMessages(prev => prev.filter(m => m.role !== 'mode-picker').concat({ role: 'user', content: labels[mode], time: now() }));
    const prompts = {
      courses: `ฉันเลือกเรียนแบบ "เรียนคอร์สก่อน" สำหรับทักษะ ${skill.name} ช่วยแนะนำคอร์สเรียนที่เหมาะสมให้หน่อย`,
      scenario: `ฉันเลือกเรียนแบบ "จำลองสถานการณ์" สำหรับทักษะ ${skill.name} ช่วยสรุปสิ่งสำคัญที่ควรรู้ แล้วสร้างสถานการณ์จำลอง 1 ข้อให้ฉันลองตอบ`,
      todo: `ฉันเลือกเรียนแบบ "ลงมือทำจริง" สำหรับทักษะ ${skill.name} ช่วยสร้าง To-Do List 3-5 ข้อที่ทำได้จริง`,
      auto: `ฉันเลือกให้ AI จัดเส้นทางการเรียนตามโมเดล 10-20-70 สำหรับทักษะ ${skill.name} ช่วยแนะนำ: 1) คอร์สเรียน (10%) 2) สถานการณ์จำลอง (20%) 3) To-Do List (70%) ให้ครบทั้ง 3 ส่วน`,
    };
    // Use ref to call ChatPanel's send
    setTimeout(() => { if (chatSendRef.current) chatSendRef.current(prompts[mode]); }, 300);
  };

  const updateProg = async (sid) => { const p = await fetchProgress(sid || sessionId); setProgress(p); };

  const toggleCourse = (i) => {
    setPath(prev => {
      const existing = prev.find(p => p.idx === i);
      if (existing) return prev.map(p => p.idx === i ? { ...p, in: !p.in } : p);
      return [...prev, { type: 'course', idx: i, name: courses[i]?.name, in: true }];
    });
  };

  const handleAIResponse = useCallback((msg, full) => {
    updateProg();

    // Detect quiz context — skip course/todo suggestions when answering quiz
    const isQuizContext = msg.includes('Quiz') || msg.includes('quiz') || msg.includes('ตอบ Quiz') || msg.includes('ทบทวน');
    const isQuizCreation = full.includes('Quiz 1') || full.includes('Quiz 2') || full.includes('quiz 1');
    const isSimAnswer = msg.includes('สถานการณ์จำลอง') || msg.includes('Simulation');
    const isTodoAnswer = msg.includes('To-Do') || msg.includes('to-do') || msg.includes('ทำ To-Do');

    // Show course suggestion cards — only when explicitly asking for courses, NOT during quiz/sim/todo
    const isSim = msg.includes('สถานการณ์') || msg.includes('Simulation') || msg.includes('simulation') || msg.includes('จำลอง') || full.includes('สถานการณ์จำลอง') || full.includes('สมมติว่า');
    const isTodoMsg = msg.toLowerCase().includes('to-do') || msg.includes('ลงมือทำ') || full.includes('To-Do') || full.includes('สิ่งที่ต้องทำ') || learningMode === 'todo';
    const mentionsCourse = msg.includes('คอร์ส') || msg.includes('เนื้อหา') || msg.includes('แนะนำเนื้อหา') || full.includes('คอร์ส') || learningMode === 'courses';
    // Only show course suggestions when it's a genuine course request, not quiz/sim/todo/assessment
    if (mentionsCourse && courses.length > 0 && !isSim && !isTodoMsg && !isQuizContext && !isQuizCreation && !isTodoAnswer && !isSimAnswer) {
      setMessages(prev => [...prev, { role: 'course-suggestions', courses: courses }]);
    }

    // Show todo suggestion cards — only when explicitly asking, not during quiz
    const mentionsTodo = isTodoMsg && !isQuizContext && !isQuizCreation;
    const todoLines = full.split('\n').map(l => l.replace(/^\s*\*\*/, '').trim()).filter(l => l.match(/^\d+[\.\)]/));
    if (mentionsTodo && todoLines.length >= 2 && !isSim) {
      const items = todoLines.map(l => l.replace(/^\d+[\.\)]\s*/, '').replace(/\*\*/g, '').trim()).filter(t => t.length > 5);
      if (items.length) {
        setMessages(prev => [...prev, { role: 'todo-suggestions', items }]);
      }
    }

    // Todo answer detection from chat
    if (isTodoAnswer && msg.length > 20 && !isQuizContext) {
      setTodos(prev => {
        const pending = prev.find(t => !t.ok);
        if (!pending) return prev;
        const fl = full.toLowerCase();
        let result = 'reviewed';
        if (fl.includes('ผ่าน') || fl.includes('ดีมาก') || fl.includes('ถูกต้อง')) result = 'passed';
        else if (fl.includes('ไม่ผ่าน') || fl.includes('ควรปรับ')) result = 'failed';
        return prev.map(t => t === pending ? {
          ...t, ok: result === 'passed', lastFeedback: full,
          attempts: [...(t.attempts || []), { answer: msg, timestamp: new Date().toLocaleString('th-TH'), result, feedback: full }],
        } : t);
      });
    }

    // Simulation detection — skip if quiz context
    if (isSim && full.length > 100 && !isQuizContext) {
      const isReplacement = msg.includes('ใหม่') || msg.includes('เปลี่ยน') || msg.includes('แตกต่าง');
      setSimulations(prev => {
        if (isReplacement && prev.length > 0) {
          const lastIdx = prev.length - 1;
          return prev.map((s, i) => i === lastIdx ? { ...s, scenario: full, done: false, result: null, attempts: [] } : s);
        }
        // Check if last sim has placeholder scenario — replace it with real one
        const last = prev.length ? prev[prev.length - 1] : null;
        if (last && !last.done && last.scenario?.includes('กำลังสร้างสถานการณ์ให้')) {
          return prev.map((s, i) => i === prev.length - 1 ? { ...s, scenario: full } : s);
        }
        if (prev.length && last && last.result !== 'passed') return prev;
        const title = (skill?.name || '') + ' — Simulation ' + (prev.length + 1);
        const criteria = skill?.assessment_criteria || [];
        const tested = prev.map(s => s.criteriaIdx).filter(x => x != null);
        const nextIdx = criteria.findIndex((_, i) => !tested.includes(i));
        return [...prev, { title, scenario: full, done: false, result: null, attempts: [], criteriaIdx: nextIdx >= 0 ? nextIdx : null, criteriaName: nextIdx >= 0 ? criteria[nextIdx]?.name : 'ทักษะโดยรวม' }];
      });
      // Update content area if viewing simulation
      if (contentView === 'simulation') {
        setTimeout(() => {
          setSimulations(prev => {
            const lastSim = prev[prev.length - 1];
            if (lastSim) setContentData({ sim: lastSim });
            return prev;
          });
        }, 100);
      }
      if (!isReplacement) setMessages(prev => [...prev, { role: 'sim-added', title: (skill?.name || '') + ' — Simulation', time: now() }]);
    }

    // Simulation answer detection — skip if quiz or todo context
    if (!isSim && !isQuizContext && !isTodoAnswer && msg.length > 20) {
      setSimulations(prev => {
        const pending = prev.find(s => !s.done || (s.done && s.result !== 'passed'));
        if (!pending) return prev;
        const fl = full.toLowerCase();
        let result = 'reviewed';
        if (fl.includes('ผ่าน') || fl.includes('ดีมาก') || fl.includes('ถูกต้อง')) result = 'passed';
        else if (fl.includes('ไม่ผ่าน') || fl.includes('ควรปรับ')) result = 'failed';
        return prev.map(s => s === pending ? { ...s, answer: msg, done: result !== 'failed', result, lastFeedback: full, attempts: [...(s.attempts || []), { answer: msg, timestamp: new Date().toLocaleString('th-TH'), result, feedback: full }] } : s);
      });
    }

    // Quiz detection from AI response — parse into a quiz set with choice + text questions
    if (isQuizCreation) {
      const questions = [];
      // Split by Quiz N pattern
      const parts = full.split(/(?=Quiz\s*\d+)/i).filter(p => p.match(/^Quiz\s*\d+/i));
      parts.forEach((part, idx) => {
        const qText = part.replace(/^Quiz\s*\d+\s*[:.]\s*/i, '').replace(/\*\*/g, '').trim();
        // Detect choice questions: lines starting with A) B) C) D) or ก) ข) ค) ง)
        const choiceLines = part.split('\n').filter(l => l.trim().match(/^[A-Da-dก-ง][\)\.]\s/));
        if (choiceLines.length >= 2) {
          const questionLine = qText.split('\n')[0].trim();
          const choices = choiceLines.map(l => l.trim().replace(/^[A-Da-dก-ง][\)\.]\s*/, ''));
          questions.push({ id: `q-${Date.now()}-${idx}`, type: 'choice', question: questionLine, choices, answer: null, result: null, feedback: '' });
        } else {
          const questionLine = qText.split('\n')[0].trim();
          questions.push({ id: `q-${Date.now()}-${idx}`, type: 'text', question: questionLine, answer: null, result: null, feedback: '' });
        }
      });
      if (questions.length > 0) {
        const quizSet = {
          id: `qs-${Date.now()}`,
          title: `ทบทวน 2-7-30 — ชุดที่ ${quizzes.length + 1}`,
          createdAt: now(),
          questions,
        };
        setQuizzes(prev => [...prev, quizSet]);
        setMessages(prev => [...prev, { role: 'quiz-added', time: now(), count: questions.length }]);
      }
    }

    // Quiz answer detection — update the pending question in the latest quiz set
    const isQuizAnswer = msg.includes('Quiz') || msg.includes('quiz') || msg.includes('ตอบ Quiz');
    if (isQuizAnswer && msg.length > 5 && !isQuizCreation) {
      setQuizzes(prev => {
        const updated = [...prev];
        // Find latest quiz set with a pending question
        for (let si = updated.length - 1; si >= 0; si--) {
          const qs = updated[si];
          const qi = qs.questions.findIndex(q => !q.result || q.result === 'reviewing');
          if (qi >= 0) {
            const fl = full.toLowerCase();
            let result = 'reviewed';
            if (fl.includes('ถูกต้อง') || fl.includes('ผ่าน') || fl.includes('correct') || fl.includes('เยี่ยม')) result = 'passed';
            else if (fl.includes('ไม่ถูก') || fl.includes('ผิด') || fl.includes('incorrect') || fl.includes('ไม่ใช่')) result = 'failed';
            const newQ = { ...qs.questions[qi], result, feedback: full, answer: msg };
            const newQuestions = [...qs.questions];
            newQuestions[qi] = newQ;
            updated[si] = { ...qs, questions: newQuestions };
            break;
          }
        }
        return updated;
      });
    }
  }, [skill, sessionId, courses, learningMode]);

  const doAssess = async () => {
    setContentView('assessment'); setContentData({ loading: true });
    const cc = path.filter(p => p.in).map(p => courses[p.idx]?.name).filter(Boolean);
    const ct = todos.filter(t => t.ok).map(t => t.title);
    const d = await assessSkill(UID, skill.id, cc, ct);
    let a = d.assessment;
    if (typeof a === 'string') try { a = JSON.parse(a.replace(/^```\w*\n?/, '').replace(/\n?```$/, '')); } catch {}
    setContentData(a || d.raw || {});
  };

  const doReview = () => {
    setContentView('review'); setShowContent(true); setChatExpanded(false);
  };

  const startReviewRound = async (dayIdx) => {
    const round = reviewRounds[dayIdx];
    if (round.status === 'generating') return;
    setReviewRounds(prev => prev.map((r, i) => i === dayIdx ? { ...r, status: 'generating' } : r));

    const prompt = `สร้าง Quiz ทบทวนบทเรียน ${round.label} สำหรับทักษะ "${skill?.name}" จำนวน 5 ข้อ โดยมีทั้งแบบตัวเลือก (4 ตัวเลือก A) B) C) D)) และแบบเขียนตอบ ` +
      `ให้แต่ละข้อขึ้นต้นด้วย "Quiz 1:" "Quiz 2:" ตามลำดับ ` +
      `ข้อที่เป็นตัวเลือกให้ใส่ตัวเลือกแต่ละบรรทัดเป็น A) B) C) D) ` +
      `ข้อที่เป็นเขียนตอบไม่ต้องมีตัวเลือก`;

    try {
      const res = await streamMessage(sessionId, prompt);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let full = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of dec.decode(value).split('\n').filter(l => l.startsWith('data: '))) {
          try { const d = JSON.parse(line.slice(6)); if (d.text) full += d.text; } catch {}
        }
      }
      // Parse quiz questions
      const questions = [];
      const parts = full.split(/(?=Quiz\s*\d+)/i).filter(p => p.match(/^Quiz\s*\d+/i));
      parts.forEach((part, idx) => {
        const qText = part.replace(/^Quiz\s*\d+\s*[:.]\s*/i, '').replace(/\*\*/g, '').trim();
        const choiceLines = part.split('\n').filter(l => l.trim().match(/^[A-Da-dก-ง][\)\.]\s/));
        if (choiceLines.length >= 2) {
          const questionLine = qText.split('\n')[0].trim();
          const choices = choiceLines.map(l => l.trim().replace(/^[A-Da-dก-ง][\)\.]\s*/, ''));
          questions.push({ id: `q-${Date.now()}-${idx}`, type: 'choice', question: questionLine, choices, answer: null, result: null, feedback: '' });
        } else {
          const questionLine = qText.split('\n')[0].trim();
          questions.push({ id: `q-${Date.now()}-${idx}`, type: 'text', question: questionLine, answer: null, result: null, feedback: '' });
        }
      });

      if (questions.length > 0) {
        const qsId = `qs-${Date.now()}`;
        const quizSet = { id: qsId, title: `ทบทวน ${round.label}`, day: round.day, createdAt: now(), questions };
        setQuizzes(prev => [...prev, quizSet]);
        setReviewRounds(prev => prev.map((r, i) => i === dayIdx ? { ...r, quizId: qsId, status: 'ready' } : r));
      } else {
        setReviewRounds(prev => prev.map((r, i) => i === dayIdx ? { ...r, status: 'pending' } : r));
      }
    } catch {
      setReviewRounds(prev => prev.map((r, i) => i === dayIdx ? { ...r, status: 'pending' } : r));
    }
  };

  const openReviewQuiz = (dayIdx) => {
    const round = reviewRounds[dayIdx];
    const qs = quizzes.find(q => q.id === round.quizId);
    if (qs) { setContentView('quiz'); setContentData({ quizSet: qs, idx: quizzes.indexOf(qs) }); }
  };

  const doSkillBadge = async () => {
    const passedSim = simulations.filter(s => s.result === 'passed').length;
    const passedTodo = todos.filter(t => t.ok).length;
    const totalQuizQ = quizzes.reduce((sum, qs) => sum + qs.questions.length, 0);
    const passedQuiz = quizzes.reduce((sum, qs) => sum + qs.questions.filter(q => q.result === 'passed').length, 0);
    const totalDone = passedSim + passedTodo + passedQuiz;
    const totalItems = simulations.length + todos.length + totalQuizQ;
    const pct = totalItems > 0 ? Math.round((totalDone / totalItems) * 100) : 0;
    const quizPct = totalQuizQ > 0 ? Math.round((passedQuiz / totalQuizQ) * 100) : 0;

    // Load admin quest data
    let questData = null;
    try {
      const r = await fetch(`/api/dashboard/skill-path/`);
      const d = await r.json();
      const match = (d.results || []).find(t => t.skill_name === skill?.name || t.title === skill?.name);
      if (match) {
        const r2 = await fetch(`/api/dashboard/skill-path/${match.id}`);
        questData = await r2.json();
      }
    } catch {}

    // Evaluate badge per level using admin criteria
    const levelResults = [];
    const levels = questData?.badge_levels?.sort((a, b) => a.order - b.order) || [];
    let allLevelsEarned = levels.length > 0;

    for (const bl of levels) {
      const criteria = bl.criteria || [];
      const levelMissions = (questData?.items || []).filter(it => it.badge_level_order === bl.order);
      const totalLevelMissions = levelMissions.length;
      const requiredMissions = levelMissions.filter(it => it.required !== false);

      const criteriaResults = criteria.map(c => {
        let actual = 0, passed = false;
        if (c.criteria_type === 'completion_rate') {
          actual = totalItems > 0 ? Math.round((totalDone / totalItems) * 100) : 0;
          passed = actual >= c.value;
        } else if (c.criteria_type === 'quiz_score') {
          actual = quizPct;
          passed = actual >= c.value;
        } else if (c.criteria_type === 'min_hours') {
          // Estimate from completed items (each ~30min)
          actual = Math.round((totalDone * 0.5) * 10) / 10;
          passed = actual >= c.value;
        } else if (c.criteria_type === 'project') {
          actual = passedSim + passedTodo;
          passed = actual >= c.value;
        } else if (c.criteria_type === 'todo_list') {
          actual = passedTodo;
          passed = actual >= c.value;
        } else {
          // Default: check if missions done
          actual = totalDone;
          passed = actual >= c.value;
        }
        return { ...c, actual, passed };
      });

      // Level earned if ALL criteria pass (or no criteria = all missions done)
      const levelEarned = criteria.length > 0
        ? criteriaResults.every(cr => cr.passed)
        : (totalLevelMissions > 0 && totalDone >= requiredMissions.length);

      if (!levelEarned) allLevelsEarned = false;
      levelResults.push({ ...bl, criteriaResults, levelEarned, totalLevelMissions });
    }

    // Fallback: no admin data → use 70% rule
    const earned = levels.length > 0 ? allLevelsEarned : pct >= 70;

    if (earned) setBadgeEarned(true);
    setContentView('badge');
    setContentData({
      skillName: skill?.name, pct, passedSim, passedTodo, passedQuiz, totalItems, totalDone, quizPct,
      questData, levelResults, earned, notYet: !earned,
    });
  };

  if (view === 'admin') return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav onHome={goHome} currentView="admin" onAdmin={goAdmin} />
      <AdminSkillPath onBack={goHome} />
    </div>
  );

  if (view === 'catalog') return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav onHome={goHome} currentView="catalog" onAdmin={goAdmin} />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}><SkillCatalog onSelectSkill={openSkill} selectedSkills={selectedSkills} onToggleSelect={toggleSelectSkill} /></div>
    </div>
  );

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav onHome={goHome} currentView="learn" onAdmin={goAdmin} />
      <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden', minHeight: 0 }}>
        <Sidebar skillName={skill?.name} progress={progress} path={path} courses={courses} todos={todos} simulations={simulations} quizzes={quizzes}
          onOverview={() => { setContentView('overview'); setChatExpanded(false); setShowContent(true); }} onHome={goHome}
          onReview={doReview} onSkillBadge={doSkillBadge} badgeEarned={badgeEarned}
          onViewCourse={(i) => { setContentView('course'); setContentData({ course: courses[i], idx: i }); setShowContent(true);
            setMessages(prev => [...prev, { role: 'assistant', time: now(), content: `📚 เห็นว่าคุณกำลังดูคอร์ส **${courses[i]?.name}** อยู่นะครับ ถ้ามีคำถามเกี่ยวกับเนื้อหา หรืออยากให้สรุปให้ บอกได้เลย!` }]);
          }}
          onViewSim={(i) => { setContentView('simulation'); setContentData({ sim: simulations[i] }); setShowContent(true);
            setMessages(prev => [...prev, { role: 'assistant', time: now(), content: `🎯 คุณกำลังทำ Simulation อยู่นะครับ ลองอ่านสถานการณ์แล้วพิมพ์คำตอบได้เลย ถ้าติดตรงไหน ถามผมได้!` }]);
          }}
          onViewTodo={(i) => { setContentView('todo'); setContentData({ todo: todos[i], idx: i }); setShowContent(true);
            setMessages(prev => [...prev, { role: 'assistant', time: now(), content: `🛠️ คุณกำลังทำ To-Do **${todos[i]?.title}** อยู่นะครับ ลงมือทำแล้วพิมพ์ผลลัพธ์ส่งมาได้เลย!` }]);
          }}
          onViewQuiz={(i) => { setContentView('quiz'); setContentData({ quizSet: quizzes[i], idx: i }); setShowContent(true); setChatExpanded(false); }}
          onCollapseChat={() => setChatExpanded(false)} />
        <ContentArea skill={skill} view={contentView} viewData={contentData}
          onExpandChat={() => setChatExpanded(true)} onExplore={() => setContentView('explore')}
          onAssess={doAssess} onOverview={() => setContentView('overview')}
          onToggleCourse={toggleCourse} path={path} courses={courses}
          style={{ display: showContent && !chatExpanded ? undefined : 'none' }}
          reviewRounds={reviewRounds} onStartReviewRound={startReviewRound} onOpenReviewQuiz={openReviewQuiz}
          onSubmitTodo={(todo, answer) => {
            setTodos(prev => prev.map(t => t.title === todo.title ? {
              ...t,
              attempts: [...(t.attempts || []), { answer, timestamp: new Date().toLocaleString('th-TH'), result: 'reviewing', feedback: '' }],
              answer,
            } : t));
            if (chatSendRef.current) chatSendRef.current(`ฉันทำ To-Do "${todo.title}" เสร็จแล้ว คำตอบ: "${answer}" ช่วยตรวจสอบหน่อยว่าผ่านหรือไม่ผ่าน พร้อมเหตุผล`);
          }}
          todos={todos}
          onSubmitSim={(sim, answer) => {
            setSimulations(prev => prev.map(s => s.title === sim.title ? {
              ...s, answer, done: true, result: 'reviewing',
              attempts: [...(s.attempts || []), { answer, timestamp: new Date().toLocaleString('th-TH'), result: 'reviewing', feedback: '' }],
            } : s));
            if (chatSendRef.current) chatSendRef.current(`ฉันตอบสถานการณ์จำลอง "${sim.title}" ว่า: "${answer}" ช่วยประเมินหน่อยว่าผ่านหรือไม่ผ่าน พร้อมเหตุผล`);
          }}
          onChangeSim={() => {
            const currentSim = simulations.find(s => s.title === contentData.sim?.title);
            if (currentSim?.confirmed) return; // Can't change after confirmed
            if (chatSendRef.current) chatSendRef.current(
              `สร้างสถานการณ์จำลองใหม่สำหรับทักษะ ${skill?.name} ด้าน "${currentSim?.criteriaName || ''}" ให้เป็นสถานการณ์ที่เหมือนจริงในการทำงาน แล้วถามคำถามให้ฉันตอบ`
            );
          }}
          onAskCoach={(sim) => {
            setChatExpanded(true);
            if (chatSendRef.current) chatSendRef.current(`ช่วยให้คำแนะนำสำหรับสถานการณ์จำลอง "${sim?.title}" หน่อย ฉันต้องคิดยังไงถึงจะตอบได้ดี`);
          }}
          simulations={simulations}
          onConfirmSim={(sim) => {
            setSimulations(prev => prev.map(s => s.title === sim.title ? { ...s, confirmed: true } : s));
            setMessages(prev => [...prev, { role: 'assistant', time: now(), content: `✅ ยืนยันสถานการณ์จำลอง **${sim.title}** แล้วครับ! ลองอ่านโจทย์แล้วพิมพ์คำตอบได้เลย ถ้าติดตรงไหนถามผมได้นะ 💪` }]);
          }}
          quizzes={quizzes}
          onSubmitQuiz={(quizSetId, questionId, answer) => {
            setQuizzes(prev => prev.map(qs => qs.id === quizSetId ? {
              ...qs,
              questions: qs.questions.map(q => q.id === questionId ? { ...q, answer, result: 'reviewing' } : q),
            } : qs));
            const qs = quizzes.find(q => q.id === quizSetId);
            const question = qs?.questions.find(q => q.id === questionId);
            if (chatSendRef.current && question) chatSendRef.current(`ฉันตอบ Quiz "${question.question}" ว่า: "${answer}" ช่วยตรวจหน่อยว่าถูกต้องหรือไม่ พร้อมอธิบาย`);
          }} />
        <ChatPanel sessionId={sessionId} expanded={chatExpanded} onToggle={() => setChatExpanded(!chatExpanded)}
          messages={messages} setMessages={setMessages} onAIResponse={handleAIResponse} onPickMode={pickMode}
          path={path} courses={courses} onToggleCourse={toggleCourse}
          todos={todos} onAddTodo={(title, desc) => setTodos(prev => prev.find(t => t.title === title) ? prev : [...prev, { title, desc, ok: false }])}
          sendRef={chatSendRef} />
      </div>
    </div>
  );
}
