import { useState, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL || '';
const LEVEL_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
const LEVEL_ICONS = ['🔍', '🛡️', '⚔️', '👑', '🌟'];

export default function Sidebar({ skillName, progress, path, courses, todos, simulations, quizzes, onOverview, onHome, onViewCourse, onViewSim, onViewTodo, onViewQuiz, onCollapseChat, onReview, onSkillBadge, badgeEarned }) {
  const [questData, setQuestData] = useState(null);
  const [activeLevel, setActiveLevel] = useState(1);
  const inP = path.filter(p => p.in);
  const pct = Math.round(progress.percent_complete || 0);

  // Try to load admin-created quest data for this skill
  useEffect(() => {
    if (!skillName) return;
    fetch(`${API}/api/dashboard/skill-path/`).then(r => r.json()).then(d => {
      const match = (d.results || []).find(t => t.skill_name === skillName || t.title === skillName);
      if (match) {
        fetch(`${API}/api/dashboard/skill-path/${match.id}`).then(r => r.json()).then(full => {
          setQuestData(full);
        }).catch(() => {});
      }
    }).catch(() => {});
  }, [skillName]);

  // If we have quest data with levels, show level-based sidebar
  if (questData && questData.badge_levels?.length > 0) {
    const levels = questData.badge_levels.sort((a, b) => a.order - b.order);
    const allItems = questData.items || [];

    return (
      <div className="sb">
        <div className="sb-top">
          <div className="label">SuperPath Quest</div>
          <h2>{questData.title || skillName}</h2>
          <div className="sb-bar"><div className="sb-bar-fill" style={{ width: `${pct}%` }} /></div>
          <div className="sb-pct">{pct}% EXP</div>
          <button className="sb-btn" onClick={onOverview}>📋 ภาพรวม Quest</button>
          <button className="sb-btn sb-btn-review" onClick={onReview}>📅 ทบทวน 2-7-30</button>
          <button className="sb-btn sb-btn-badge" onClick={onSkillBadge}>{badgeEarned ? '🏆 ดู Badge' : '🏆 รับ Badge!'}</button>
          <button className="sb-back" onClick={onHome}>← ย้อนกลับ</button>
        </div>
        <div>
          {levels.map((bl, i) => {
            const levelItems = allItems.filter(it => it.badge_level_order === bl.order);
            const isActive = activeLevel === bl.order;
            const levelCourses = levelItems.filter(it => it.content_type === 'material');
            const levelSims = levelItems.filter(it => it.content_type === 'simulation');
            const levelTodos = levelItems.filter(it => it.content_type === 'todo');
            const levelQuizzes = levelItems.filter(it => it.content_type === 'quiz');

            return (
              <div key={i}>
                <div className="sb-level-header" style={{ borderLeftColor: LEVEL_COLORS[i] || '#6366f1' }}
                  onClick={() => setActiveLevel(isActive ? null : bl.order)}>
                  <span className="sb-level-icon" style={{ background: LEVEL_COLORS[i] }}>{LEVEL_ICONS[i] || '⭐'}</span>
                  <div className="sb-level-info">
                    <div className="sb-level-name">Lv.{bl.order} {bl.name}</div>
                    <div className="sb-level-meta">{levelItems.length} missions</div>
                  </div>
                  <span className="sb-level-chevron">{isActive ? '▲' : '▼'}</span>
                </div>

                {isActive && (
                  <div className="sb-level-content">
                    {levelCourses.length > 0 && (
                      <>
                        <div className="sb-sec" style={{ color: '#5dade2' }}>📚 Courses ({levelCourses.length})</div>
                        {levelCourses.map((item, ci) => {
                          const courseIdx = courses.findIndex(c => c.name === item.title);
                          return (
                            <div key={ci} className="si" onClick={() => { onCollapseChat(); if (courseIdx >= 0) onViewCourse(courseIdx); }}>
                              <div className="dot c" /><div className="inf"><div className="tp">Course{item.required === false ? ' · Optional' : ''}</div><div className="nm">{item.title}</div></div>
                            </div>
                          );
                        })}
                      </>
                    )}
                    {levelSims.length > 0 && (
                      <>
                        <div className="sb-sec" style={{ color: '#e74c3c' }}>🎯 Simulation ({levelSims.length})</div>
                        {levelSims.map((item, si) => {
                          const simIdx = simulations.findIndex(s => s.title?.includes(item.title) || s.criteriaName === item.title);
                          return (
                            <div key={si} className="si" onClick={() => { onCollapseChat(); if (simIdx >= 0) onViewSim(simIdx); }}>
                              <div className="dot" style={{ background: '#e74c3c' }} /><div className="inf"><div className="tp">Simulation</div><div className="nm">{item.title}</div></div>
                            </div>
                          );
                        })}
                      </>
                    )}
                    {levelTodos.length > 0 && (
                      <>
                        <div className="sb-sec" style={{ color: '#f5b041' }}>✅ To-Do ({levelTodos.length})</div>
                        {levelTodos.map((item, ti) => {
                          const todoIdx = todos.findIndex(t => t.title === item.title);
                          return (
                            <div key={ti} className="si" onClick={() => { onCollapseChat(); if (todoIdx >= 0) onViewTodo(todoIdx); }}>
                              <div className="dot t" /><div className="inf"><div className="tp">To-Do</div><div className="nm">{item.title}</div></div>
                            </div>
                          );
                        })}
                      </>
                    )}
                    {levelQuizzes.length > 0 && (
                      <>
                        <div className="sb-sec" style={{ color: '#2ecc71' }}>📝 Quiz ({levelQuizzes.length})</div>
                        {levelQuizzes.map((item, qi) => (
                          <div key={qi} className="si"><div className="dot" style={{ background: '#2ecc71' }} /><div className="inf"><div className="tp">Quiz</div><div className="nm">{item.title}</div></div></div>
                        ))}
                      </>
                    )}
                    {levelItems.length === 0 && <div style={{ padding: '8px 20px', fontSize: '.7em', color: 'rgba(255,255,255,.25)' }}>ยังไม่มี mission</div>}
                  </div>
                )}
              </div>
            );
          })}

          {/* Fallback: show quizzes from chat */}
          {quizzes?.length > 0 && (
            <>
              <div className="sb-sec" style={{ color: '#2ecc71' }}>📝 Quiz ทบทวน ({quizzes.length} ชุด)</div>
              {quizzes.map((qs, i) => {
                const total = qs.questions.length;
                const passed = qs.questions.filter(q => q.result === 'passed').length;
                return (
                  <div key={qs.id} className="si" onClick={() => { onCollapseChat(); onViewQuiz(i); }}>
                    <div className="dot" style={{ background: passed === total ? '#27ae60' : '#95a5b6' }} />
                    <div className="inf"><div className="tp">Quiz ชุดที่ {i + 1}</div><div className="nm">{qs.title}</div><div className="du">{passed}/{total} ข้อถูก</div></div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      </div>
    );
  }

  // Fallback: original sidebar (no admin quest data)
  return (
    <div className="sb">
      <div className="sb-top">
        <div className="label">SuperPath</div>
        <h2>{skillName}</h2>
        <div className="sb-bar"><div className="sb-bar-fill" style={{ width: `${pct}%` }} /></div>
        <div className="sb-pct">{pct}% ({progress.completed_checklist_items || 0}/{progress.total_checklist_items || 0})</div>
        <button className="sb-btn" onClick={onOverview}>📋 ดูภาพรวมทักษะ</button>
        <button className="sb-btn sb-btn-review" onClick={onReview}>📅 ทบทวน 2-7-30</button>
        <button className="sb-btn sb-btn-badge" onClick={onSkillBadge}>{badgeEarned ? '🏆 ดู Skill Badge' : '🏆 รับ Skill Badge!'}</button>
        <button className="sb-back" onClick={onHome}>← ย้อนกลับ</button>
      </div>
      <div>
        <div className="sb-sec" style={{ color: '#5dade2' }}>📚 10% เรียนรู้จากเนื้อหา{inP.length ? ` (${inP.length})` : ''}</div>
        {inP.length ? inP.map(p => {
          const c = courses[p.idx];
          return c ? (
            <div key={p.idx} className="si" onClick={() => { onCollapseChat(); onViewCourse(p.idx); }}>
              <div className="dot c" /><div className="inf"><div className="tp">Course</div><div className="nm">{c.name}</div><div className="du">{c.duration}</div></div>
            </div>
          ) : null;
        }) : <div style={{ padding: '8px 20px', fontSize: '.7em', color: 'rgba(255,255,255,.25)' }}>ยังไม่มีคอร์ส</div>}

        <div className="sb-sec" style={{ color: '#e74c3c' }}>🎯 20% Simulation{simulations.length ? ` (${simulations.length})` : ''}</div>
        {simulations.length ? simulations.map((s, i) => (
          <div key={i} className="si" onClick={() => { onCollapseChat(); onViewSim(i); }}>
            <div className="dot" style={{ background: s.result === 'passed' ? '#27ae60' : '#e74c3c' }} />
            <div className="inf"><div className="tp">Simulation · {s.criteriaName}</div><div className="nm">{s.title}</div>
              <div className="du">{s.done ? (s.result === 'passed' ? '✅ ผ่าน' : '❌ ไม่ผ่าน') : '⏳ รอตอบ'}</div></div>
          </div>
        )) : <div style={{ padding: '8px 20px', fontSize: '.7em', color: 'rgba(255,255,255,.25)' }}>ยังไม่มี Simulation</div>}

        <div className="sb-sec" style={{ color: '#f5b041' }}>🛠️ 70% To-Do{todos.length ? ` (${todos.length})` : ''}</div>
        {todos.length ? todos.map((t, i) => (
          <div key={i} className="si" onClick={() => { onCollapseChat(); onViewTodo(i); }}>
            <div className="dot t" /><div className="inf"><div className="tp">To-Do</div><div className="nm">{t.title}</div>
              <div className="du">{t.ok ? '✅ Verified' : '⏳ รอส่งงาน'}</div></div>
          </div>
        )) : <div style={{ padding: '8px 20px', fontSize: '.7em', color: 'rgba(255,255,255,.25)' }}>ยังไม่มี To-Do</div>}

        {quizzes?.length > 0 && (
          <>
            <div className="sb-sec" style={{ color: '#2ecc71' }}>📝 Quiz ทบทวน ({quizzes.length} ชุด)</div>
            {quizzes.map((qs, i) => {
              const total = qs.questions.length;
              const passed = qs.questions.filter(q => q.result === 'passed').length;
              return (
                <div key={qs.id} className="si" onClick={() => { onCollapseChat(); onViewQuiz(i); }}>
                  <div className="dot" style={{ background: passed === total ? '#27ae60' : '#95a5b6' }} />
                  <div className="inf"><div className="tp">Quiz ชุดที่ {i + 1}</div><div className="nm">{qs.title}</div><div className="du">{passed}/{total} ข้อถูก</div></div>
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
}
