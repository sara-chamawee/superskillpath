import { renderMarkdown } from '../utils/markdown';
import { useState, useEffect } from 'react';

export default function ContentArea({ skill, view, viewData, onExpandChat, onExplore, onAssess, onOverview, onToggleCourse, path, courses, style, onSubmitTodo, todos, onSubmitSim, onChangeSim, onAskCoach, onConfirmSim, simulations, quizzes, onSubmitQuiz, reviewRounds, onStartReviewRound, onOpenReviewQuiz }) {
  if (!skill) return <div className="ct" style={style}><div style={{ padding: 40, textAlign: 'center', color: '#95a5b6' }}>เลือกทักษะจากรายการ</div></div>;

  if (view === 'overview') return <SkillOverview skill={skill} onExpandChat={onExpandChat} onExplore={onExplore} onAssess={onAssess} style={style} />;
  if (view === 'explore') return <ExploreContent skill={skill} courses={courses} path={path} onToggle={onToggleCourse} onBack={onOverview} />;
  if (view === 'course') return <CourseDetail skill={skill} course={viewData.course} idx={viewData.idx} path={path} onToggle={onToggleCourse} />;
  if (view === 'simulation') { const freshSim = simulations?.find(s => s.title === viewData.sim?.title) || viewData.sim; return <SimulationView sim={freshSim} skill={skill} onSubmit={onSubmitSim} onChange={onChangeSim} onAskCoach={onAskCoach} onConfirm={onConfirmSim} />; }
  if (view === 'todo') { const freshTodo = todos?.find(t => t.title === viewData.todo?.title) || viewData.todo; return <TodoView todo={freshTodo} skill={skill} onSubmit={onSubmitTodo} />; }
  if (view === 'quiz') { const freshQs = quizzes?.find(q => q.id === viewData.quizSet?.id) || viewData.quizSet; return <QuizSetView quizSet={freshQs} idx={viewData.idx} skill={skill} onSubmit={onSubmitQuiz} />; }
  if (view === 'review') return <ReviewView skill={skill} rounds={reviewRounds} onStart={onStartReviewRound} onOpenQuiz={onOpenReviewQuiz} onBack={onOverview} />;
  if (view === 'badge') return <BadgeView data={viewData} skill={skill} onBack={onOverview} />;
  if (view === 'assessment') return <AssessmentView data={viewData} skill={skill} onBack={onOverview} />;
  return null;
}

function SkillOverview({ skill, onExpandChat, onExplore, onAssess, style }) {
  const [questData, setQuestData] = useState(null);
  const API = import.meta.env.VITE_API_URL || '';
  const LEVEL_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
  const LEVEL_ICONS = ['🔍', '🛡️', '⚔️', '👑', '🌟'];

  useEffect(() => {
    if (!skill?.name) return;
    fetch(`${API}/api/dashboard/skill-path/`).then(r => r.json()).then(d => {
      const match = (d.results || []).find(t => t.skill_name === skill.name || t.title === skill.name);
      if (match) {
        fetch(`${API}/api/dashboard/skill-path/${match.id}`).then(r => r.json()).then(full => setQuestData(full)).catch(() => {});
      }
    }).catch(() => {});
  }, [skill?.name]);

  // If admin quest data exists, show enhanced overview
  if (questData) {
    const levels = (questData.badge_levels || []).sort((a, b) => a.order - b.order);
    const totalMissions = (questData.items || []).length;
    return (
      <div className="ct" style={style}>
        <div className="ct-head">
          <div className="bc">← {skill.domain || 'Quest'} / {questData.title || skill.name}</div>
          <h2>⚔️ {questData.title || skill.name}</h2>
          <div className="row">
            <span className="pill pill-purple">🗺️ {levels.length} Levels</span>
            <span className="pill pill-green">📋 {totalMissions} Missions</span>
            <button className="btn btn-primary" onClick={onExpandChat}>💬 เรียนกับ AI</button>
            {skill.courses?.length > 0 && <button className="btn btn-blue" onClick={onExplore}>🔍 สำรวจเนื้อหา</button>}
            <button className="btn btn-green" onClick={onAssess}>🎯 ประเมินทักษะ</button>
          </div>
        </div>
        <div className="ct-body">
          {/* Quest Description */}
          <div style={{ color: 'var(--text2)', lineHeight: 1.7, marginBottom: 24 }}>{questData.description || skill.definition}</div>

          {/* Level Roadmap */}
          {levels.map((bl, i) => {
            const levelMissions = (questData.items || []).filter(it => it.badge_level_order === bl.order);
            const areas = bl.areas || bl.criteria || [];
            return (
              <div key={i} className="cl-card" style={{ borderLeft: `4px solid ${LEVEL_COLORS[i] || '#6366f1'}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                  <span style={{ width: 32, height: 32, borderRadius: 8, background: LEVEL_COLORS[i], color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1em' }}>{LEVEL_ICONS[i] || '⭐'}</span>
                  <div>
                    <h3 style={{ margin: 0 }}>Level {bl.order}: {bl.name}</h3>
                    <div style={{ fontSize: '.75em', color: 'var(--text3)' }}>{levelMissions.length} missions · {bl.description || ''}</div>
                  </div>
                </div>

                {/* Behavioral Index areas */}
                {Array.isArray(areas) && areas.map((area, ai) => {
                  const areaName = area.name || area.criteria_type || '';
                  const checklist = area.checklist_items || [];
                  if (!areaName) return null;
                  return (
                    <div key={ai} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <span style={{ color: LEVEL_COLORS[i] }}>●</span>
                        <span style={{ fontWeight: 600, fontSize: '.88em' }}>{areaName}</span>
                      </div>
                      {checklist.map((item, ci) => (
                        <div key={ci} className="cl-item">
                          <div className="cl-check">-</div>
                          <div className="cl-text">{typeof item === 'string' ? item : item.description || ''}</div>
                        </div>
                      ))}
                    </div>
                  );
                })}

                {/* Missions for this level */}
                {levelMissions.length > 0 && (
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '.78em', fontWeight: 600, color: 'var(--text3)', marginBottom: 6 }}>📋 Missions</div>
                    {levelMissions.map((m, mi) => (
                      <div key={mi} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: '.82em' }}>
                        <span>{m.content_type === 'material' ? '📖' : m.content_type === 'quiz' ? '📝' : m.content_type === 'simulation' ? '🎯' : '✅'}</span>
                        <span>{m.title}</span>
                        {m.required === false && <span style={{ fontSize: '.7em', color: '#95a5b6', background: '#f0f0f5', padding: '1px 6px', borderRadius: 4 }}>Optional</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {/* Original assessment criteria as fallback */}
          {levels.length === 0 && skill.assessment_criteria?.map((a, i) => (
            <div key={i} className="cl-card">
              <h3><span style={{ color: 'var(--purple)' }}>●</span> {a.name}</h3>
              {a.checklist_items?.map((it, j) => (
                <div key={j} className="cl-item"><div className="cl-check">-</div><div className="cl-text">{it.description}</div></div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Fallback: original overview
  return (
    <div className="ct" style={style}>
      <div className="ct-head">
        <div className="bc">← {skill.domain || 'Skill'} / {skill.name}</div>
        <h2>{skill.name}</h2>
        <div className="row">
          {skill.assessment_type && <span className="pill pill-green">{skill.assessment_type}</span>}
          <span className="pill pill-purple">📚 {skill.assessment_criteria?.length || 0} ด้าน</span>
          <button className="btn btn-primary" onClick={onExpandChat}>💬 เรียนกับ AI</button>
          {skill.courses?.length > 0 && <button className="btn btn-blue" onClick={onExplore}>🔍 สำรวจเนื้อหา ({skill.courses.length})</button>}
          <button className="btn btn-green" onClick={onAssess}>🎯 ประเมินทักษะ</button>
        </div>
      </div>
      <div className="ct-body">
        <div style={{ color: 'var(--text2)', lineHeight: 1.7, marginBottom: 24 }}>{skill.definition}</div>
        {skill.assessment_criteria?.map((a, i) => (
          <div key={i} className="cl-card">
            <h3><span style={{ color: 'var(--purple)' }}>●</span> {a.name}</h3>
            {a.checklist_items?.map((it, j) => (
              <div key={j} className="cl-item"><div className="cl-check">-</div><div className="cl-text">{it.description}</div></div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function ExploreContent({ skill, courses, path, onToggle, onBack }) {
  return (
    <div className="ct">
      <div className="ct-head">
        <div className="bc">← {skill.name} / สำรวจเนื้อหา</div>
        <h2>🔍 เนื้อหาทั้งหมด</h2>
        <div className="row"><span className="pill pill-purple">{courses.length} คอร์ส</span>
          <button className="btn btn-outline" onClick={onBack}>← กลับ</button></div>
      </div>
      <div className="ct-body">
        {courses.map((c, i) => {
          const inP = path.find(p => p.idx === i && p.in);
          return (
            <div key={i} className="course-card">
              <div className="course-thumb">{c.provider || '📹'}</div>
              <div style={{ flex: 1 }}><h4>{c.name}</h4><div style={{ fontSize: '.75em', color: '#95a5b6' }}>👤 {c.instructor}</div></div>
              <button className={`btn ${inP ? 'btn-green' : 'btn-blue'}`} style={{ fontSize: '.72em' }} onClick={() => onToggle(i)}>{inP ? '✓ ใน Path' : '+ เพิ่ม'}</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CourseDetail({ skill, course, idx, path, onToggle }) {
  if (!course) return null;
  const inP = path.find(p => p.idx === idx && p.in);
  const askSummary = () => {
    const input = document.querySelector('.ci-in');
    if (input) { input.value = `สรุปเนื้อหาคอร์ส "${course.name}" ให้หน่อย สรุปสั้นๆ ว่าจะได้เรียนรู้อะไรบ้าง`; input.dispatchEvent(new Event('input', { bubbles: true })); }
    const btn = document.querySelector('.ci-s');
    if (btn) btn.click();
  };
  return (
    <div className="ct">
      <div className="ct-head">
        <div className="bc">← {skill.name} / คอร์ส</div>
        <h2>{course.name}</h2>
        <div className="row">
          <span className="pill pill-purple">คอร์สออนไลน์</span>
          <button className={`btn ${inP ? 'btn-green' : 'btn-blue'}`} onClick={() => onToggle(idx)}>{inP ? '✓ อยู่ใน SuperPath' : '+ เพิ่มใน SuperPath'}</button>
          <button className="btn btn-primary" onClick={askSummary}>📝 สรุปเนื้อหา</button>
        </div>
      </div>
      <div className="ct-body">
        <div className="course-card" style={{ cursor: 'default' }}>
          <div className="course-thumb" style={{ width: 160, height: 95 }}>{course.provider || '📹'}</div>
          <div><h4>{course.name}</h4><div style={{ fontSize: '.78em', color: '#888' }}>👤 {course.instructor}</div><div style={{ fontSize: '.75em', color: '#aaa' }}>🏢 {course.provider}</div></div>
        </div>
      </div>
    </div>
  );
}

function SimulationView({ sim, skill, onSubmit, onChange, onAskCoach, onConfirm }) {
  const [answer, setAnswer] = useState('');
  if (!sim) return null;
  const handleSubmit = () => { if (answer.trim() && onSubmit) { onSubmit(sim, answer.trim()); setAnswer(''); } };
  const isLocked = sim.confirmed || sim.done;
  return (
    <div className="ct">
      <div className="ct-head">
        <div className="bc">← {skill.name} / Simulation</div>
        <h2>🎯 {sim.title}</h2>
        <div className="row">
          <span className="pill pill-purple">📋 {sim.criteriaName}</span>
          <span className={`pill ${sim.result === 'passed' ? 'pill-green' : ''}`}>{sim.done ? (sim.result === 'passed' ? '✅ ผ่าน' : '❌ ไม่ผ่าน') : sim.confirmed ? '🔒 ยืนยันแล้ว' : '⏳ รอยืนยัน'}</span>
          {!isLocked && <button className="btn btn-blue" style={{ fontSize: '.72em' }} onClick={onChange}>🔄 เปลี่ยนสถานการณ์</button>}
          {!sim.confirmed && !sim.done && <button className="btn btn-green" style={{ fontSize: '.72em' }} onClick={() => onConfirm(sim)}>✅ ยืนยันสถานการณ์นี้</button>}
          <button className="btn btn-primary" style={{ fontSize: '.72em' }} onClick={() => onAskCoach(sim)}>💬 ปรึกษา AI Coach</button>
        </div>
      </div>
      <div className="ct-body">
        <div className="cl-card" style={{ borderLeft: '4px solid var(--accent)' }}>
          <h3>📋 สถานการณ์</h3>
          <div style={{ fontSize: '.85em', color: 'var(--text2)', lineHeight: 1.7 }} dangerouslySetInnerHTML={{ __html: renderMarkdown(sim.scenario) }} />
        </div>

        {/* Answer box — show when not yet passed */}
        {(!sim.done || sim.result !== 'passed') && (
          <div className="cl-card">
            <h3>💬 {sim.attempts?.length ? 'ลองตอบใหม่' : 'ตอบคำถาม'}</h3>
            {!sim.confirmed && (
              <div style={{ background: '#fffde7', borderRadius: 8, padding: '8px 12px', fontSize: '.78em', color: '#92400e', marginBottom: 12 }}>
                💡 อ่านสถานการณ์ด้านบนแล้วพิมพ์คำตอบได้เลย หรือกด "ยืนยันสถานการณ์นี้" ก่อนก็ได้
              </div>
            )}
            <textarea value={answer} onChange={e => setAnswer(e.target.value)}
              style={{ width: '100%', minHeight: 120, border: '1.5px solid var(--border)', borderRadius: 8, padding: 12, fontFamily: 'inherit', fontSize: '.85em', resize: 'vertical' }}
              placeholder="พิมพ์คำตอบของคุณ..." />
            <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
              <button className="btn btn-primary" onClick={handleSubmit}>📤 ส่งคำตอบ</button>
              <button className="btn btn-outline" onClick={() => onAskCoach(sim)}>💡 ขอ Hint จาก AI</button>
            </div>
          </div>
        )}

        {sim.lastFeedback && (
          <div className="cl-card" style={{ borderLeft: `4px solid ${sim.result === 'passed' ? 'var(--green)' : '#f39c12'}` }}>
            <h3>🤖 ผลการประเมินล่าสุด</h3>
            <div style={{ fontSize: '.85em', color: 'var(--text2)', lineHeight: 1.7 }} dangerouslySetInnerHTML={{ __html: renderMarkdown(sim.lastFeedback) }} />
          </div>
        )}

        {sim.attempts?.length > 0 && (
          <div className="cl-card">
            <h3>📊 ประวัติการตอบ ({sim.attempts.length} ครั้ง)</h3>
            {sim.attempts.slice().reverse().map((a, j) => (
              <div key={j} style={{ padding: '14px 0', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.8em', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600 }}>ครั้งที่ {sim.attempts.length - j}</span>
                  <span style={{ padding: '2px 8px', borderRadius: 6, background: a.result === 'passed' ? '#e8f8f0' : '#fde8e8', color: a.result === 'passed' ? 'var(--green)' : 'var(--accent)', fontSize: '.85em' }}>
                    {a.result === 'passed' ? '✅ ผ่าน' : '❌ ไม่ผ่าน'}</span>
                </div>
                <div style={{ background: 'var(--bg)', borderRadius: 8, padding: '10px 12px', fontSize: '.82em', marginBottom: 8 }}>{a.answer}</div>
                {a.feedback && <div style={{ background: '#f8f6ff', borderRadius: 8, padding: '10px 12px', fontSize: '.8em' }} dangerouslySetInnerHTML={{ __html: renderMarkdown(a.feedback) }} />}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AssessmentView({ data, skill, onBack }) {
  if (!data) return null;
  const a = data;
  if (a.overall) {
    const colors = { passed: 'var(--green)', partial: '#f39c12', not_passed: 'var(--accent)' };
    const labels = { passed: '✅ ผ่าน', partial: '⚠️ ผ่านบางส่วน', not_passed: '❌ ยังไม่ผ่าน' };
    return (
      <div className="ct">
        <div className="ct-head"><h2>🎯 ผลการประเมิน</h2><div className="row"><button className="btn btn-outline" onClick={onBack}>← กลับ</button></div></div>
        <div className="ct-body">
          <div className="cl-card" style={{ borderLeft: `4px solid ${colors[a.overall]}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: '1.8em' }}>{a.overall === 'passed' ? '🎉' : '❌'}</span>
              <div><div style={{ fontSize: '1.05em', fontWeight: 700, color: colors[a.overall] }}>{labels[a.overall]}</div>
                <div style={{ fontSize: '.82em', color: 'var(--text2)' }}>{a.overall_reason}</div></div>
            </div>
          </div>
          {a.areas?.map((ar, i) => (
            <div key={i} className="cl-card" style={{ borderLeft: `4px solid ${ar.status === 'passed' ? 'var(--green)' : 'var(--accent)'}` }}>
              <h3><span style={{ color: ar.status === 'passed' ? 'var(--green)' : 'var(--accent)' }}>●</span> {ar.area}</h3>
              <div style={{ fontSize: '.8em', color: 'var(--text3)', marginBottom: 10 }}>{ar.reason}</div>
              {ar.checklist?.map((cl, j) => (
                <div key={j} className="cl-item">
                  <div className={`cl-check ${cl.status === 'passed' ? 'done' : ''}`}>{cl.status === 'passed' ? '✓' : ''}</div>
                  <div><div className="cl-text">{cl.item}</div>{cl.note && <div style={{ fontSize: '.72em', color: 'var(--text3)' }}>{cl.note}</div>}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }
  return <div className="ct"><div className="ct-body"><pre style={{ fontSize: '.8em', whiteSpace: 'pre-wrap' }}>{JSON.stringify(data, null, 2)}</pre></div></div>;
}


function TodoView({ todo, skill, onSubmit }) {
  const [answer, setAnswer] = useState('');
  if (!todo) return null;

  const handleSubmit = () => {
    if (!answer.trim()) return;
    if (onSubmit) onSubmit(todo, answer.trim());
    setAnswer('');
  };

  return (
    <div className="ct">
      <div className="ct-head">
        <div className="bc">← {skill.name} / To-Do</div>
        <h2>📝 {todo.title}</h2>
        <div className="row">
          <span className={`pill ${todo.ok ? 'pill-green' : 'pill-purple'}`}>{todo.ok ? '✅ Verified' : '⏳ รอส่งงาน'}</span>
        </div>
      </div>
      <div className="ct-body">
        <div className="cl-card">
          <h3>📋 รายละเอียด</h3>
          <div style={{ fontSize: '.85em', color: 'var(--text2)', lineHeight: 1.7 }}>{todo.desc}</div>
        </div>

        {/* Answer box */}
        {!todo.ok && (
          <div className="cl-card">
            <h3>💬 ส่งคำตอบ</h3>
            <textarea
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              style={{ width: '100%', minHeight: 120, border: '1.5px solid var(--border)', borderRadius: 8, padding: 12, fontFamily: 'inherit', fontSize: '.85em', resize: 'vertical' }}
              placeholder="พิมพ์คำตอบหรือสิ่งที่คุณทำ..."
            />
            <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
              <button className="btn btn-primary" onClick={handleSubmit}>📤 ส่งให้ AI ตรวจ</button>
            </div>
          </div>
        )}

        {/* AI Feedback */}
        {todo.lastFeedback && (
          <div className="cl-card" style={{ borderLeft: `4px solid ${todo.ok ? 'var(--green)' : '#f39c12'}` }}>
            <h3>🤖 ผลการตรวจล่าสุดจาก AI</h3>
            <div style={{ fontSize: '.85em', color: 'var(--text2)', lineHeight: 1.7 }} dangerouslySetInnerHTML={{ __html: renderMarkdown(todo.lastFeedback) }} />
          </div>
        )}

        {/* Attempt history */}
        {todo.attempts?.length > 0 && (
          <div className="cl-card">
            <h3>📊 ประวัติการส่งงาน ({todo.attempts.length} ครั้ง)</h3>
            {todo.attempts.slice().reverse().map((a, j) => (
              <div key={j} style={{ padding: '14px 0', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.8em', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, color: 'var(--primary)' }}>ครั้งที่ {todo.attempts.length - j}</span>
                  <div>
                    <span style={{ color: 'var(--text3)', marginRight: 8 }}>{a.timestamp}</span>
                    <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: '.85em', background: a.result === 'passed' ? '#e8f8f0' : '#fde8e8', color: a.result === 'passed' ? 'var(--green)' : 'var(--accent)' }}>
                      {a.result === 'passed' ? '✅ ผ่าน' : a.result === 'failed' ? '❌ ไม่ผ่าน' : '📝 ประเมินแล้ว'}
                    </span>
                  </div>
                </div>
                <div style={{ background: 'var(--bg)', borderRadius: 8, padding: '10px 12px', fontSize: '.82em', marginBottom: 8 }}>
                  <div style={{ fontSize: '.7em', color: 'var(--text3)', marginBottom: 4 }}>💬 คำตอบของคุณ:</div>
                  {a.answer}
                </div>
                {a.feedback && (
                  <div style={{ background: '#f8f6ff', borderRadius: 8, padding: '10px 12px', fontSize: '.8em' }}>
                    <div style={{ fontSize: '.7em', color: 'var(--purple)', marginBottom: 4 }}>🤖 AI Feedback:</div>
                    <div dangerouslySetInnerHTML={{ __html: renderMarkdown(a.feedback) }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function QuizSetView({ quizSet, idx, skill, onSubmit }) {
  const [answers, setAnswers] = useState({});
  if (!quizSet) return null;

  const total = quizSet.questions.length;
  const passed = quizSet.questions.filter(q => q.result === 'passed').length;

  const handleSubmit = (q) => {
    const ans = answers[q.id];
    if (!ans || !ans.trim()) return;
    if (onSubmit) onSubmit(quizSet.id, q.id, ans.trim());
    setAnswers(prev => ({ ...prev, [q.id]: '' }));
  };

  const handleChoice = (q, choice) => {
    if (q.result && q.result !== 'reviewing') return; // already answered
    if (onSubmit) onSubmit(quizSet.id, q.id, choice);
  };

  return (
    <div className="ct">
      <div className="ct-head">
        <div className="bc">← {skill.name} / Quiz ทบทวน</div>
        <h2>📝 {quizSet.title}</h2>
        <div className="row">
          <span className="pill pill-purple">📅 ทบทวน 2-7-30</span>
          <span className="pill pill-green">{passed}/{total} ข้อถูก</span>
          <span style={{ fontSize: '.75em', color: 'var(--text3)' }}>สร้างเมื่อ {quizSet.createdAt}</span>
        </div>
      </div>
      <div className="ct-body">
        {/* Progress bar */}
        <div style={{ background: 'var(--border)', borderRadius: 8, height: 8, marginBottom: 20 }}>
          <div style={{ background: 'var(--green)', height: '100%', borderRadius: 8, width: `${total > 0 ? (passed / total) * 100 : 0}%`, transition: 'width .3s' }} />
        </div>

        {quizSet.questions.map((q, qi) => (
          <div key={q.id} className="cl-card" style={{ borderLeft: `4px solid ${q.result === 'passed' ? 'var(--green)' : q.result === 'failed' ? 'var(--accent)' : '#ddd'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>ข้อ {qi + 1} {q.type === 'choice' ? '(ตัวเลือก)' : '(เขียนตอบ)'}</h3>
              {q.result && (
                <span style={{ padding: '3px 10px', borderRadius: 6, fontSize: '.75em', fontWeight: 600,
                  background: q.result === 'passed' ? '#e8f8f0' : q.result === 'failed' ? '#fde8e8' : '#f0f0f0',
                  color: q.result === 'passed' ? 'var(--green)' : q.result === 'failed' ? 'var(--accent)' : 'var(--text3)' }}>
                  {q.result === 'passed' ? '✅ ถูกต้อง' : q.result === 'failed' ? '❌ ผิด' : '⏳ กำลังตรวจ'}
                </span>
              )}
            </div>
            <div style={{ fontSize: '.88em', color: 'var(--text)', lineHeight: 1.7, marginBottom: 12, fontWeight: 500 }}>{q.question}</div>

            {/* Choice type */}
            {q.type === 'choice' && q.choices && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                {q.choices.map((c, ci) => {
                  const letter = String.fromCharCode(65 + ci);
                  const isSelected = q.answer === `${letter}) ${c}` || q.answer === c;
                  const canClick = !q.result || q.result === 'reviewing';
                  return (
                    <button key={ci} onClick={() => canClick && handleChoice(q, `${letter}) ${c}`)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
                        background: isSelected ? (q.result === 'passed' ? '#e8f8f0' : q.result === 'failed' ? '#fde8e8' : '#f0edff') : 'white',
                        border: `1.5px solid ${isSelected ? (q.result === 'passed' ? 'var(--green)' : q.result === 'failed' ? 'var(--accent)' : 'var(--purple)') : 'var(--border)'}`,
                        borderRadius: 10, cursor: canClick ? 'pointer' : 'default', fontFamily: 'inherit', fontSize: '.84em',
                        textAlign: 'left', transition: 'all .15s', color: 'var(--text)',
                      }}>
                      <span style={{ width: 28, height: 28, borderRadius: '50%', background: isSelected ? 'var(--purple)' : 'var(--bg)',
                        color: isSelected ? 'white' : 'var(--text2)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 700, fontSize: '.8em', flexShrink: 0 }}>{letter}</span>
                      {c}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Text type */}
            {q.type === 'text' && (!q.result || q.result === 'failed') && (
              <div style={{ marginBottom: 12 }}>
                <textarea
                  value={answers[q.id] || ''}
                  onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                  style={{ width: '100%', minHeight: 80, border: '1.5px solid var(--border)', borderRadius: 8, padding: 10, fontFamily: 'inherit', fontSize: '.84em', resize: 'vertical' }}
                  placeholder="พิมพ์คำตอบของคุณ..."
                />
                <button className="btn btn-primary" style={{ marginTop: 8, fontSize: '.8em' }} onClick={() => handleSubmit(q)}>📤 ส่งคำตอบ</button>
              </div>
            )}

            {/* Show submitted text answer */}
            {q.type === 'text' && q.answer && q.result && q.result !== 'failed' && (
              <div style={{ background: 'var(--bg)', borderRadius: 8, padding: '10px 12px', fontSize: '.82em', marginBottom: 8 }}>
                <span style={{ fontSize: '.7em', color: 'var(--text3)' }}>💬 คำตอบ:</span> {q.answer}
              </div>
            )}

            {/* Feedback */}
            {q.feedback && (
              <div style={{ background: q.result === 'passed' ? '#f0faf4' : '#fff8f0', borderRadius: 8, padding: '10px 12px', fontSize: '.8em' }}>
                <div style={{ fontSize: '.7em', color: 'var(--purple)', marginBottom: 4 }}>🤖 AI:</div>
                <div dangerouslySetInnerHTML={{ __html: renderMarkdown(q.feedback) }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function BadgeView({ data, skill, onBack }) {
  if (!data) return null;
  const earned = data.earned || !data.notYet;
  const quest = data.questData;
  const levelResults = data.levelResults || [];
  const LEVEL_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
  const LEVEL_ICONS = ['🔍', '🛡️', '⚔️', '👑', '🌟'];
  const CRITERIA_LABELS = {
    min_hours: 'ชั่วโมงเรียน', class_attendance: 'เข้าเรียน', quiz_score: 'คะแนน Quiz',
    completion_rate: 'อัตราสำเร็จ', project: 'โปรเจกต์/Simulation', coaching: 'Coaching',
    todo_list: 'To-Do List', skill_acquired: 'ทักษะที่ได้', competency: 'สมรรถนะ', offline_learning: 'เรียนรู้นอกระบบ',
  };
  const CRITERIA_UNITS = {
    min_hours: 'ชม.', quiz_score: '%', completion_rate: '%',
  };

  return (
    <div className="ct">
      <div className="ct-head">
        <div className="bc">← {skill.name} / Skill Badge</div>
        <h2>🏆 Skill Badge</h2>
        <div className="row"><button className="btn btn-outline" onClick={onBack}>← กลับ</button></div>
      </div>
      <div className="ct-body">
        {/* Overall status */}
        <div style={{ textAlign: 'center', padding: '28px 20px' }}>
          <div style={{ fontSize: earned ? '5em' : '3em', marginBottom: 12 }}>{earned ? '🏆' : '🔒'}</div>
          <h2 style={{ color: earned ? 'var(--green)' : 'var(--text3)', marginBottom: 8 }}>
            {earned ? `ยินดีด้วย! คุณได้รับ Badge "${data.skillName}"` : 'ยังไม่ได้รับ Badge'}
          </h2>
          <div style={{ fontSize: '.88em', color: 'var(--text2)', marginBottom: 8 }}>
            ทำสำเร็จ {data.totalDone}/{data.totalItems} รายการ ({data.pct}%)
          </div>
          <div style={{ maxWidth: 400, margin: '0 auto', background: '#f0f0f5', borderRadius: 8, height: 14, overflow: 'hidden' }}>
            <div style={{ height: '100%', borderRadius: 8, background: earned ? 'linear-gradient(90deg, #10b981, #059669)' : 'linear-gradient(90deg, #f59e0b, #f97316)', width: `${data.pct}%`, transition: 'width .5s' }} />
          </div>
        </div>

        {/* Per-level badge with evaluated criteria */}
        {levelResults.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '.95em', marginBottom: 12 }}>🏅 Badge ตาม Level</h3>
            {levelResults.map((lr, i) => (
              <div key={i} className="cl-card" style={{ borderLeft: `4px solid ${LEVEL_COLORS[i]}`, marginBottom: 14 }}>
                {/* Level header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <div style={{ width: 48, height: 48, borderRadius: 12, background: lr.levelEarned ? `${LEVEL_COLORS[i]}` : `${LEVEL_COLORS[i]}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5em', color: lr.levelEarned ? 'white' : LEVEL_COLORS[i] }}>
                    {lr.levelEarned ? '🏅' : LEVEL_ICONS[i]}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: '.95em' }}>Level {lr.order}: {lr.name}</div>
                    <div style={{ fontSize: '.75em', color: 'var(--text3)' }}>
                      {lr.totalLevelMissions} missions {lr.description ? `· ${lr.description}` : ''}
                    </div>
                  </div>
                  <span style={{ padding: '4px 14px', borderRadius: 20, fontSize: '.78em', fontWeight: 700,
                    background: lr.levelEarned ? '#d1fae5' : '#fef3c7', color: lr.levelEarned ? '#065f46' : '#92400e' }}>
                    {lr.levelEarned ? '✅ Badge Earned!' : '🔒 Not Yet'}
                  </span>
                </div>

                {/* Criteria checklist — show each condition with pass/fail */}
                {lr.criteriaResults?.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: '.78em', fontWeight: 600, color: 'var(--text2)', marginBottom: 8 }}>🎯 เงื่อนไขการได้รับ Badge:</div>
                    {lr.criteriaResults.map((cr, ci) => {
                      const unit = CRITERIA_UNITS[cr.criteria_type] || '';
                      const label = CRITERIA_LABELS[cr.criteria_type] || cr.criteria_type;
                      return (
                        <div key={ci} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: '1px solid #f0f0f5' }}>
                          <span style={{ fontSize: '1.1em' }}>{cr.passed ? '✅' : '❌'}</span>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '.85em', fontWeight: 500 }}>{label}</div>
                            <div style={{ fontSize: '.72em', color: 'var(--text3)' }}>เป้าหมาย: ≥ {cr.value}{unit}</div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '.95em', fontWeight: 700, color: cr.passed ? 'var(--green)' : 'var(--accent)' }}>
                              {cr.actual}{unit}
                            </div>
                            <div style={{ fontSize: '.68em', color: cr.passed ? 'var(--green)' : 'var(--accent)' }}>
                              {cr.passed ? 'ผ่าน' : `ขาดอีก ${Math.max(0, cr.value - cr.actual)}${unit}`}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* No criteria defined — mission-based */}
                {(!lr.criteriaResults || lr.criteriaResults.length === 0) && (
                  <div style={{ fontSize: '.82em', color: 'var(--text2)', padding: '6px 0' }}>
                    🎯 เงื่อนไข: ทำ Mission ทั้งหมดใน Level นี้ให้สำเร็จ ({lr.totalLevelMissions} missions)
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Achievement badges from admin */}
        {quest?.achievement_badges?.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '.95em', marginBottom: 12 }}>🏆 Achievement Badges</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
              {quest.achievement_badges.map((ab, i) => (
                <div key={i} className="cl-card" style={{ textAlign: 'center', padding: 16 }}>
                  <div style={{ fontSize: '2em', marginBottom: 4 }}>{ab.icon || '🏆'}</div>
                  <div style={{ fontWeight: 700, fontSize: '.82em' }}>{ab.name}</div>
                  <div style={{ fontSize: '.72em', color: 'var(--text3)', marginTop: 2 }}>
                    {(ab.desc || '').replace(`{${ab.variable}}`, ab.customVal || ab.defaultVal || '')}
                  </div>
                  <div style={{ marginTop: 6, fontSize: '.72em', color: '#95a5b6' }}>🔒 ยังไม่ได้รับ</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
          <div className="cl-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2em', marginBottom: 4 }}>🎯</div>
            <div style={{ fontSize: '.85em', fontWeight: 600 }}>Simulation</div>
            <div style={{ fontSize: '1.2em', fontWeight: 700, color: 'var(--green)' }}>{data.passedSim || 0} ผ่าน</div>
          </div>
          <div className="cl-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2em', marginBottom: 4 }}>🛠️</div>
            <div style={{ fontSize: '.85em', fontWeight: 600 }}>To-Do</div>
            <div style={{ fontSize: '1.2em', fontWeight: 700, color: 'var(--green)' }}>{data.passedTodo || 0} ผ่าน</div>
          </div>
          <div className="cl-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2em', marginBottom: 4 }}>📝</div>
            <div style={{ fontSize: '.85em', fontWeight: 600 }}>Quiz</div>
            <div style={{ fontSize: '1.2em', fontWeight: 700, color: 'var(--green)' }}>{data.passedQuiz || 0} ผ่าน</div>
          </div>
        </div>

        {!earned && (
          <div className="cl-card" style={{ borderLeft: '4px solid #f39c12', background: '#fffde7' }}>
            <h3>💡 ทำอะไรต่อดี?</h3>
            <div style={{ fontSize: '.85em', color: 'var(--text2)', lineHeight: 1.7 }}>
              {levelResults.length > 0
                ? levelResults.filter(lr => !lr.levelEarned).map(lr => {
                    const failed = (lr.criteriaResults || []).filter(cr => !cr.passed);
                    if (failed.length === 0) return `Level ${lr.order} (${lr.name}): ทำ Mission ให้ครบ`;
                    return `Level ${lr.order} (${lr.name}): ${failed.map(f => `${CRITERIA_LABELS[f.criteria_type] || f.criteria_type} ขาดอีก ${Math.max(0, f.value - f.actual)}${CRITERIA_UNITS[f.criteria_type] || ''}`).join(', ')}`;
                  }).join(' | ')
                : 'ลองทำ Simulation, To-Do หรือ Quiz ที่ยังไม่ผ่านให้ครบ เพื่อรับ Skill Badge!'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ReviewView({ skill, rounds, onStart, onOpenQuiz, onBack }) {
  const dayColors = { 2: '#e74c3c', 7: '#f39c12', 30: '#2ecc71' };

  return (
    <div className="ct">
      <div className="ct-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ color: '#e74c3c', fontWeight: 700, fontSize: '.85em' }}>Spaced Repetition</span>
          <button className="btn btn-outline" style={{ fontSize: '.72em' }} onClick={onBack}>← กลับ</button>
        </div>
      </div>
      <div className="ct-body">
        {/* Header card */}
        <div className="cl-card" style={{ borderLeft: '4px solid #e74c3c', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <span style={{ fontSize: '1.6em' }}>🧠</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1em' }}>หลักการ 2-7-30 Spaced Repetition</div>
              <div style={{ fontSize: '.82em', color: 'var(--text2)' }}>ทบทวนใน Day 2, 7, 30 เพื่อย้ำความรู้ระยะยาวให้คงอยู่ระยะยาว</div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-around', padding: '16px 0 8px' }}>
            {rounds.map((r, i) => (
              <div key={r.day} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.8em', marginBottom: 4 }}>{r.icon}</div>
                <div style={{ fontSize: '.78em', fontWeight: 700, color: dayColors[r.day] }}>{r.label}</div>
                <div style={{ fontSize: '.65em', color: 'var(--text3)' }}>
                  {r.day === 2 ? 'Quick Recall' : r.day === 7 ? 'Scenario' : 'Deep Review'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Round cards */}
        {rounds.map((r, i) => (
          <div key={r.day} className="cl-card" style={{ borderLeft: `4px solid ${dayColors[r.day]}`, marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', background: `${dayColors[r.day]}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2em' }}>{r.icon}</div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '.92em' }}>ทบทวนครั้งที่ {i + 1} ({r.label})</div>
                  <div style={{ fontSize: '.72em', color: 'var(--text3)' }}>📅 {r.day === 2 ? '2 วันหลังเรียน' : r.day === 7 ? '1 สัปดาห์หลังเรียน' : '1 เดือนหลังเรียน'}</div>
                </div>
              </div>
              {r.status === 'ready' && (
                <span style={{ fontSize: '.72em', color: '#2ecc71', fontWeight: 600 }}>✅ พร้อมทำ</span>
              )}
            </div>
            <div style={{ fontSize: '.82em', color: 'var(--text2)', margin: '10px 0', lineHeight: 1.6 }}>{r.desc}</div>
            {r.status === 'pending' && (
              <button className="btn" style={{ background: dayColors[r.day], color: 'white', border: 'none', fontSize: '.78em', padding: '8px 18px', borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit' }}
                onClick={() => onStart(i)}>🚀 เริ่มทบทวน</button>
            )}
            {r.status === 'generating' && (
              <div style={{ fontSize: '.78em', color: dayColors[r.day], fontWeight: 600 }}>⏳ กำลังสร้าง Quiz...</div>
            )}
            {r.status === 'ready' && (
              <button className="btn" style={{ background: dayColors[r.day], color: 'white', border: 'none', fontSize: '.78em', padding: '8px 18px', borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit' }}
                onClick={() => onOpenQuiz(i)}>📝 ทำ Quiz</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
