import { useState, useEffect, useCallback, useRef } from 'react';
import '../styles/admin.css';

const API = import.meta.env.VITE_API_URL || '';
const LEVEL_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
const LEVEL_ICONS = ['🔍', '🛡️', '⚔️', '👑', '🌟'];
const DEFAULT_LEVEL_NAMES = ['Scout', 'Guardian', 'Champion', 'Master', 'Legend'];

const BADGE_TEMPLATES = [
  { id: 'streak-3', name: 'The Streak Master', desc: 'ทำภารกิจต่อเนื่อง {days} วัน', icon: '🔥', variable: 'days', defaultVal: 3 },
  { id: 'streak-5', name: 'The Streak Master+', desc: 'ทำภารกิจต่อเนื่อง {days} วัน', icon: '🔥', variable: 'days', defaultVal: 5 },
  { id: 'perfectionist', name: 'The Perfectionist', desc: 'ผ่าน 2-7-30 rhythm โดยไม่พลาดแม้แต่ครั้งเดียว', icon: '💎', variable: null },
  { id: 'speed-run', name: 'Speed Runner', desc: 'จบทุก mission ภายใน {hours} ชั่วโมง', icon: '⚡', variable: 'hours', defaultVal: 48 },
  { id: 'explorer', name: 'The Explorer', desc: 'ลองทำ simulation ครบทุกด้าน', icon: '🧭', variable: null },
];

export default function AdminSkillPath({ onBack }) {
  const [templates, setTemplates] = useState([]);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/dashboard/skill-path/`);
      const d = await r.json();
      setTemplates(d.results || []);
    } catch { setMsg('โหลดข้อมูลไม่สำเร็จ'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => setEditing({
    title: '', skill_name: '', description: '', items: [],
    badge_levels: [{ name: DEFAULT_LEVEL_NAMES[0], order: 1, description: '', content_provider: '', areas: [{ name: '', checklist_items: [''] }] }],
    criteria: [], achievement_badges: [], badge_auto_issue: true,
  });

  const openFromSkill = async (skillId) => {
    try {
      const r = await fetch(`${API}/api/skills/${skillId}`);
      const sd = await r.json();
      const areas = (sd.assessment_criteria || []).map(c => ({
        name: c.name, checklist_items: c.checklist_items.map(it => it.description),
      }));
      const courses = (sd.courses || []).map((c, i) => ({
        title: c.name, item_type: 'fixed', content_type: 'material', learning_type: 'formal',
        order: i + 1, estimated_minutes: 60, badge_level_order: 1, provider: c.provider,
      }));
      setEditing({
        title: sd.name, skill_name: sd.name, description: sd.definition, items: courses,
        badge_levels: [{ name: DEFAULT_LEVEL_NAMES[0], order: 1, description: `ระดับเริ่มต้นสำหรับ ${sd.name}`, content_provider: '', areas }],
        criteria: [{ criteria_type: 'completion_rate', value: 80, badge_level_order: 1 }],
        achievement_badges: [], badge_auto_issue: true,
      });
    } catch { setMsg('โหลดข้อมูล Skill ไม่สำเร็จ'); }
  };

  const openEdit = async (id) => {
    try {
      const r = await fetch(`${API}/api/dashboard/skill-path/${id}`);
      const d = await r.json();
      const criteria = [];
      (d.badge_levels || []).forEach(bl => (bl.criteria || []).forEach(c => criteria.push({ ...c, badge_level_order: bl.order })));
      const badge_levels = (d.badge_levels || []).map(bl => ({ ...bl, areas: bl.areas || [{ name: '', checklist_items: [''] }] }));
      setEditing({ ...d, criteria, badge_levels, achievement_badges: d.achievement_badges || [], badge_auto_issue: d.badge_auto_issue !== false });
    } catch { setMsg('โหลด template ไม่สำเร็จ'); }
  };

  const doAction = async (id, action) => {
    if (action === 'delete' && !confirm('ลบ Quest นี้?')) return;
    const map = { publish: { method: 'PATCH', url: `${id}/publish` }, archive: { method: 'PATCH', url: `${id}/archive` }, delete: { method: 'DELETE', url: id } };
    const { method, url } = map[action];
    const r = await fetch(`${API}/api/dashboard/skill-path/${url}`, { method });
    if (!r.ok && action !== 'delete') { const e = await r.json(); setMsg(e.detail?.errors?.[0]?.message || `${action} ไม่สำเร็จ`); return; }
    const icons = { publish: '🚀', archive: '📦', delete: '🗑️' };
    setMsg(`${icons[action]} ${action} สำเร็จ`);
    load();
  };

  const saveTemplate = async (data) => {
    const isNew = !data.id;
    const url = isNew ? `${API}/api/dashboard/skill-path/` : `${API}/api/dashboard/skill-path/${data.id}`;
    const body = {
      title: data.title || data.skill_name, skill_name: data.skill_name, description: data.description, items: data.items,
      badge_levels: data.badge_levels.map(bl => ({ name: bl.name, order: bl.order, description: bl.description, content_provider: bl.content_provider || '', areas: bl.areas || [] })),
      criteria: data.criteria, version: data.version || undefined,
    };
    const r = await fetch(url, { method: isNew ? 'POST' : 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) { const e = await r.json(); setMsg(e.detail?.errors?.map(x => x.message).join(', ') || 'บันทึกไม่สำเร็จ'); return; }
    const result = await r.json();
    setMsg(result.warning ? `⚠️ ${result.warning}` : '✅ Quest saved!');
    setEditing(null); load();
  };

  if (editing) return <QuestArchitect data={editing} onSave={saveTemplate} onCancel={() => setEditing(null)} msg={msg} setMsg={setMsg} />;

  // ── Quest List ──
  return (
    <div className="qa-page">
      <div className="qa-hero">
        <div className="qa-hero-text">
          <h1 className="qa-title">⚔️ Quest Architect</h1>
          <p className="qa-subtitle">สร้างและจัดการ Skill Quests สำหรับ Learner</p>
        </div>
        <div className="qa-hero-actions">
          <SkillPicker onPick={openFromSkill} />
          <button className="qa-btn-create" onClick={openCreate}>+ สร้าง Quest ใหม่</button>
        </div>
      </div>
      {msg && <div className="qa-toast" onClick={() => setMsg('')}>{msg}</div>}
      {loading ? <div className="qa-loading">⏳ กำลังโหลด...</div> : (
        <div className="qa-quest-grid">
          {templates.length === 0 && <div className="qa-empty">🗺️ ยังไม่มี Quest — สร้าง Quest แรกของคุณเลย!</div>}
          {templates.map(t => {
            const statusMap = { draft: { icon: '📝', label: 'Draft', cls: 'draft' }, published: { icon: '🟢', label: 'Live', cls: 'live' }, archived: { icon: '📦', label: 'Archived', cls: 'archived' } };
            const st = statusMap[t.status] || statusMap.draft;
            return (
              <div key={t.id} className="qa-quest-card">
                <div className="qa-quest-card-header">
                  <span className={`qa-quest-status qa-quest-status-${st.cls}`}>{st.icon} {st.label}</span>
                  <span className="qa-quest-version">v{t.version}</span>
                </div>
                <div className="qa-quest-card-body" onClick={() => openEdit(t.id)}>
                  <div className="qa-quest-card-icon">⚔️</div>
                  <div className="qa-quest-card-title">{t.title}</div>
                  <div className="qa-quest-card-meta">{t.skill_name}</div>
                  <div className="qa-quest-card-stats">
                    <span>📋 {t.item_count} missions</span>
                    <span>👥 {t.enrollment_count} learners</span>
                  </div>
                </div>
                <div className="qa-quest-card-actions">
                  {t.status === 'draft' && <button className="qa-btn-sm qa-btn-publish" onClick={() => doAction(t.id, 'publish')}>🚀 Publish</button>}
                  {t.status !== 'archived' && <button className="qa-btn-sm qa-btn-archive" onClick={() => doAction(t.id, 'archive')}>📦</button>}
                  <button className="qa-btn-sm qa-btn-delete" onClick={() => doAction(t.id, 'delete')}>🗑️</button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}


/* ── Skill Picker Dropdown ── */
function SkillPicker({ onPick }) {
  const [open, setOpen] = useState(false);
  const [skills, setSkills] = useState([]);
  const [q, setQ] = useState('');
  const ref = useRef(null);

  const search = async (query) => {
    setQ(query);
    try { const r = await fetch(`${API}/api/skills?q=${encodeURIComponent(query)}&limit=8`); const d = await r.json(); setSkills(d.skills || []); } catch {}
  };
  useEffect(() => { if (open) search(''); }, [open]);
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!open) return <button className="qa-btn-import" onClick={() => setOpen(true)}>📥 Import from Skill Catalog</button>;
  return (
    <div className="qa-picker" ref={ref}>
      <div className="qa-picker-head">
        <input className="qa-input" placeholder="🔍 ค้นหา Skill..." value={q} onChange={e => search(e.target.value)} autoFocus />
        <button className="qa-btn-x" onClick={() => setOpen(false)}>×</button>
      </div>
      <div className="qa-picker-list">
        {skills.map(s => (
          <div key={s.id} className="qa-picker-item" onClick={() => { onPick(s.id); setOpen(false); }}>
            <span className="qa-picker-icon">⚔️</span>
            <div><div className="qa-picker-name">{s.name}</div><div className="qa-picker-meta">{s.num_areas} areas · {s.num_checklist_items} checklist</div></div>
          </div>
        ))}
        {skills.length === 0 && <div className="qa-picker-empty">ไม่พบ Skill</div>}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   Quest Architect — Main Editor
   ══════════════════════════════════════════════════════════════ */
function QuestArchitect({ data, onSave, onCancel, msg, setMsg }) {
  const [form, setForm] = useState({ ...data });
  const [phase, setPhase] = useState(1); // 1=Goal, 2=Levels, 3=Missions, 4=Rewards
  const [activeLevel, setActiveLevel] = useState(1);
  const [previewMode, setPreviewMode] = useState(false);

  const set = (key, val) => setForm(prev => ({ ...prev, [key]: val }));
  const phases = [
    { num: 1, icon: '🎯', label: 'Goal' },
    { num: 2, icon: '🗺️', label: 'Levels' },
    { num: 3, icon: '⚔️', label: 'Missions' },
    { num: 4, icon: '🏅', label: 'Rewards' },
  ];

  const levelReady = (bl) => {
    const hasName = bl.name?.trim();
    const hasAreas = bl.areas?.some(a => a.name?.trim() && a.checklist_items?.some(c => c.trim()));
    return hasName && hasAreas;
  };

  const handleSave = () => {
    if (!form.skill_name.trim()) { setMsg('กรุณาใส่ชื่อ Skill'); return; }
    onSave({ ...form, title: form.title.trim() || form.skill_name.trim() });
  };

  if (previewMode) return <LearnerPreview form={form} onClose={() => setPreviewMode(false)} />;

  return (
    <div className="qa-page">
      {msg && <div className="qa-toast" onClick={() => setMsg('')}>{msg}</div>}

      {/* Phase Bar */}
      <div className="qa-phase-bar">
        <div className="qa-phase-track">
          {phases.map((p, i) => (
            <div key={i} className={`qa-phase ${phase === p.num ? 'active' : ''} ${phase > p.num ? 'done' : ''}`} onClick={() => setPhase(p.num)}>
              <div className="qa-phase-icon">{phase > p.num ? '✓' : p.icon}</div>
              <div className="qa-phase-label">{p.label}</div>
            </div>
          ))}
          <div className="qa-phase-exp-bar"><div className="qa-phase-exp-fill" style={{ width: `${(phase / 4) * 100}%` }} /></div>
        </div>
        <button className="qa-btn-preview" onClick={() => setPreviewMode(true)}>👁️ View as Learner</button>
      </div>

      {/* Phase Content */}
      {phase === 1 && <PhaseGoal form={form} set={set} />}
      {phase === 2 && <PhaseLevels form={form} set={set} activeLevel={activeLevel} setActiveLevel={setActiveLevel} setMsg={setMsg} levelReady={levelReady} />}
      {phase === 3 && <PhaseMissions form={form} set={set} activeLevel={activeLevel} setActiveLevel={setActiveLevel} setMsg={setMsg} />}
      {phase === 4 && <PhaseRewards form={form} set={set} levelReady={levelReady} />}

      {/* Bottom Nav */}
      <div className="qa-bottom-bar">
        <button className="qa-btn-back" onClick={phase === 1 ? onCancel : () => setPhase(phase - 1)}>
          {phase === 1 ? '✕ Cancel' : '← Back'}
        </button>
        <div className="qa-bottom-right">
          {phase < 4 ? (
            <button className="qa-btn-next" onClick={() => setPhase(phase + 1)}>Next →</button>
          ) : (
            <button className="qa-btn-save" onClick={handleSave}>💾 Save Quest</button>
          )}
        </div>
      </div>
    </div>
  );
}


/* ── Phase 1: Goal ── */
function PhaseGoal({ form, set }) {
  return (
    <div className="qa-card">
      <div className="qa-card-icon-big">🎯</div>
      <h2 className="qa-card-title">Define Your Quest</h2>
      <p className="qa-card-desc">ตั้งชื่อและอธิบาย Skill ที่ต้องการสร้างเส้นทางการเรียนรู้</p>
      <div className="qa-form-group">
        <label className="qa-label">Quest Name (Skill Name) <span className="qa-req">*</span></label>
        <input className="qa-input qa-input-lg" placeholder="e.g. Cognitive Flexibility" value={form.skill_name}
          onChange={e => { set('skill_name', e.target.value); if (!form.title || form.title === form.skill_name) set('title', e.target.value); }} />
      </div>
      <div className="qa-form-group">
        <label className="qa-label">Quest Description <span className="qa-req">*</span></label>
        <textarea className="qa-input qa-textarea" placeholder="อธิบายว่า Skill นี้คืออะไร ทำไมถึงสำคัญ..." value={form.description}
          onChange={e => set('description', e.target.value)} rows={4} />
      </div>
      <div className="qa-form-group">
        <label className="qa-label">Display Title (ถ้าต่างจาก Skill Name)</label>
        <input className="qa-input" placeholder="ถ้าไม่ระบุจะใช้ Quest Name" value={form.title} onChange={e => set('title', e.target.value)} />
      </div>

      {/* Level Architecture Setup */}
      <div className="qa-level-setup">
        <label className="qa-label">🗺️ จำนวน Level ของ Quest</label>
        <div className="qa-level-selector">
          {[1, 2, 3, 4, 5].map(n => (
            <button key={n} className={`qa-level-btn ${form.badge_levels.length === n ? 'active' : ''}`}
              onClick={() => {
                let levels = [...form.badge_levels];
                while (levels.length < n) { const o = levels.length + 1; levels.push({ name: DEFAULT_LEVEL_NAMES[o - 1] || `Level ${o}`, order: o, description: '', content_provider: '', areas: [{ name: '', checklist_items: [''] }] }); }
                while (levels.length > n) levels.pop();
                set('badge_levels', levels);
              }}>
              {n}
            </button>
          ))}
        </div>
        <div className="qa-level-preview">
          {form.badge_levels.map((bl, i) => (
            <div key={i} className="qa-level-tag" style={{ '--lc': LEVEL_COLORS[i] }}>
              <span>{LEVEL_ICONS[i]}</span> Lv.{bl.order} {bl.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Phase 2: Levels (Expandable Cards) ── */
function PhaseLevels({ form, set, activeLevel, setActiveLevel, setMsg, levelReady }) {
  const [aiLoading, setAiLoading] = useState(false);
  const [expanded, setExpanded] = useState(form.badge_levels[0]?.order || 1);

  const updateBL = (order, key, val) => {
    set('badge_levels', form.badge_levels.map(bl => bl.order === order ? { ...bl, [key]: val } : bl));
  };

  const aiSuggest = async (order) => {
    const bl = form.badge_levels.find(b => b.order === order);
    if (!form.skill_name.trim()) { setMsg('ใส่ชื่อ Skill ก่อน'); return; }
    setAiLoading(true);
    try {
      const r = await fetch(`${API}/api/dashboard/skill-path/ai-suggest`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `แนะนำ Behavioral Index (ด้านการประเมิน) และ checklist items สำหรับทักษะ "${form.skill_name}" ระดับ ${bl?.name || 'Level ' + order} ให้เป็นภาษาไทย แต่ละด้านควรมี 3-5 checklist items ที่เริ่มต้นด้วย "ฉัน..." ตอบเป็น JSON array: [{"name":"ชื่อด้าน","checklist_items":["ฉัน..."]}]`,
          skill_name: form.skill_name, description: form.description,
        }),
      });
      const d = await r.json();
      // Try to parse areas from response
      const text = d.clean_text || '';
      const jsonMatch = text.match(/\[[\s\S]*\]/);
      if (jsonMatch) {
        try {
          const areas = JSON.parse(jsonMatch[0]);
          if (Array.isArray(areas) && areas.length > 0) {
            updateBL(order, 'areas', areas.map(a => ({ name: a.name || '', checklist_items: a.checklist_items || [''] })));
            setMsg('🤖 AI สร้าง Behavioral Index แล้ว!');
          }
        } catch {}
      }
      if (!jsonMatch) setMsg('💡 AI ตอบแล้ว — ลองดูข้อมูลด้านล่าง');
    } catch { setMsg('AI ไม่พร้อมใช้งาน'); }
    setAiLoading(false);
  };

  return (
    <div className="qa-levels-phase">
      <div className="qa-phase-header">
        <div>
          <h2 className="qa-card-title">🗺️ Level Architecture</h2>
          <p className="qa-card-desc">กำหนด Behavioral Index (เกณฑ์ประเมิน) สำหรับแต่ละ Level — ข้อมูลเหล่านี้จะถูกใช้เป็น AI Context Data</p>
        </div>
      </div>

      {form.badge_levels.map((bl, i) => {
        const isExpanded = expanded === bl.order;
        const ready = levelReady(bl);
        const areas = bl.areas || [];
        const areaCount = areas.filter(a => a.name?.trim()).length;
        const checkCount = areas.reduce((s, a) => s + (a.checklist_items?.filter(c => c.trim()).length || 0), 0);

        return (
          <div key={i} className={`qa-level-card ${isExpanded ? 'expanded' : ''}`} style={{ '--lc': LEVEL_COLORS[i] }}>
            {/* Collapsed Header */}
            <div className="qa-level-card-header" onClick={() => setExpanded(isExpanded ? null : bl.order)}>
              <div className="qa-level-card-left">
                <span className={`qa-level-status ${ready ? 'ready' : 'missing'}`}>{ready ? '🟢' : '🔴'}</span>
                <span className="qa-level-card-icon" style={{ background: LEVEL_COLORS[i] }}>{LEVEL_ICONS[i]}</span>
                <div>
                  <div className="qa-level-card-name">Level {bl.order}: {bl.name}</div>
                  <div className="qa-level-card-summary">{areaCount} behavioral index · {checkCount} checklist</div>
                </div>
              </div>
              <span className="qa-level-card-chevron">{isExpanded ? '▲' : '▼'}</span>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
              <div className="qa-level-card-body">
                <div className="qa-level-name-row">
                  <label className="qa-label-sm">Level Name</label>
                  <input className="qa-input" value={bl.name} onChange={e => updateBL(bl.order, 'name', e.target.value)} />
                </div>

                <div className="qa-ai-context-banner">
                  <span>🤖 AI Context Data</span> — ข้อมูลด้านล่างจะถูกใช้สร้าง To-do Lists & Simulations ให้ Learner อัตโนมัติ
                  <button className="qa-btn-ai" onClick={() => aiSuggest(bl.order)} disabled={aiLoading}>
                    {aiLoading ? '⏳ Generating...' : '🤖 AI Generate'}
                  </button>
                </div>

                {/* Areas & Checklist */}
                {areas.map((area, ai) => (
                  <div key={ai} className="qa-area-block">
                    <div className="qa-area-head">
                      <span className="qa-area-dot" style={{ background: LEVEL_COLORS[i] }} />
                      <input className="qa-input qa-input-area" placeholder={`Behavioral Index ${ai + 1} เช่น "การคิดวิเคราะห์และสร้างทางเลือก"`}
                        value={area.name} onChange={e => {
                          const newAreas = [...areas]; newAreas[ai] = { ...area, name: e.target.value }; updateBL(bl.order, 'areas', newAreas);
                        }} />
                      {areas.length > 1 && <button className="qa-btn-x" onClick={() => updateBL(bl.order, 'areas', areas.filter((_, j) => j !== ai))}>×</button>}
                    </div>
                    <div className="qa-checklist-block">
                      {(area.checklist_items || ['']).map((item, ci) => (
                        <div key={ci} className="qa-checklist-row">
                          <span className="qa-checklist-dot" />
                          <input className="qa-input qa-input-check" placeholder='เช่น "ฉันมีความตื่นตัวอยู่เสมอและสามารถจับสัญญาณของการเปลี่ยนแปลงได้"'
                            value={item} onChange={e => {
                              const newItems = [...area.checklist_items]; newItems[ci] = e.target.value;
                              const newAreas = [...areas]; newAreas[ai] = { ...area, checklist_items: newItems }; updateBL(bl.order, 'areas', newAreas);
                            }} />
                          {area.checklist_items.length > 1 && <button className="qa-btn-x-sm" onClick={() => {
                            const newItems = area.checklist_items.filter((_, j) => j !== ci);
                            const newAreas = [...areas]; newAreas[ai] = { ...area, checklist_items: newItems }; updateBL(bl.order, 'areas', newAreas);
                          }}>×</button>}
                        </div>
                      ))}
                      <button className="qa-btn-add-sm" onClick={() => {
                        const newAreas = [...areas]; newAreas[ai] = { ...area, checklist_items: [...area.checklist_items, ''] }; updateBL(bl.order, 'areas', newAreas);
                      }}>+ Add Index</button>
                    </div>
                  </div>
                ))}
                <button className="qa-btn-add-area" onClick={() => updateBL(bl.order, 'areas', [...areas, { name: '', checklist_items: [''] }])}>
                  + Add Behavioral Index
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}


/* ── Phase 3: Missions (per Behavioral Index) ── */
function PhaseMissions({ form, set, activeLevel, setActiveLevel, setMsg }) {
  const [courseCatalog, setCourseCatalog] = useState([]);
  const [courseSearch, setCourseSearch] = useState('');
  const [showPicker, setShowPicker] = useState(null); // { levelOrder, areaIdx }
  const [expanded, setExpanded] = useState(null); // "levelOrder-areaIdx"

  // Load courses from catalog
  useEffect(() => {
    fetch(`${API}/api/skills?limit=200`).then(r => r.json()).then(d => {
      const allSkills = d.skills || [];
      // Fetch courses for the current skill
      const match = allSkills.find(s => s.name === form.skill_name);
      if (match) {
        fetch(`${API}/api/skills/${match.id}`).then(r => r.json()).then(sd => {
          setCourseCatalog(sd.courses || []);
        }).catch(() => {});
      }
    }).catch(() => {});
  }, [form.skill_name]);

  const addItem = (levelOrder, areaIdx, item) => {
    const maxOrder = form.items.reduce((m, it) => Math.max(m, it.order || 0), 0);
    set('items', [...form.items, { ...item, order: maxOrder + 1, badge_level_order: levelOrder, area_index: areaIdx }]);
  };
  const removeItem = (idx) => set('items', form.items.filter((_, i) => i !== idx));
  const setItem = (idx, key, val) => set('items', form.items.map((it, i) => i === idx ? { ...it, [key]: val } : it));

  const getAreaItems = (levelOrder, areaIdx) =>
    form.items.filter(it => it.badge_level_order === levelOrder && it.area_index === areaIdx).sort((a, b) => a.order - b.order);

  const typeIcons = { material: '📖', quiz: '📝', todo: '✅', simulation: '🎯' };
  const filteredCourses = courseCatalog.filter(c => !courseSearch || c.name.toLowerCase().includes(courseSearch.toLowerCase()));

  return (
    <div className="qa-missions-phase">
      <div className="qa-content-grid">
        <div className="qa-content-main">
          <h2 className="qa-card-title">⚔️ Mission Board</h2>
          <p className="qa-card-desc">กำหนดภารกิจสำหรับแต่ละ Behavioral Index — เลือก Course จากระบบ หรือให้ AI สร้างเนื้อหาให้ Learner</p>

          {form.badge_levels.map((bl, bi) => (
            <div key={bi} className="qa-mission-level" style={{ '--lc': LEVEL_COLORS[bi] }}>
              <div className="qa-mission-level-head">
                <span className="qa-mission-level-icon" style={{ background: LEVEL_COLORS[bi] }}>{LEVEL_ICONS[bi]}</span>
                <span>Level {bl.order}: {bl.name}</span>
                <span className="qa-mission-count">{form.items.filter(it => it.badge_level_order === bl.order).length} missions</span>
              </div>

              {/* Per Behavioral Index */}
              {(bl.areas || []).filter(a => a.name?.trim()).map((area, ai) => {
                const key = `${bl.order}-${ai}`;
                const isExp = expanded === key;
                const areaItems = getAreaItems(bl.order, ai);

                return (
                  <div key={ai} className="qa-bi-section">
                    <div className="qa-bi-header" onClick={() => setExpanded(isExp ? null : key)}>
                      <span className="qa-bi-dot" style={{ background: LEVEL_COLORS[bi] }} />
                      <span className="qa-bi-name">{area.name}</span>
                      <span className="qa-bi-count">{areaItems.length} missions</span>
                      <span className="qa-bi-chevron">{isExp ? '▲' : '▼'}</span>
                    </div>

                    {isExp && (
                      <div className="qa-bi-body">
                        {/* Existing missions */}
                        {areaItems.map((item, ii) => {
                          const realIdx = form.items.indexOf(item);
                          return (
                            <div key={ii} className="qa-mission-item">
                              <span className="qa-mission-type-icon">{typeIcons[item.content_type] || '📋'}</span>
                              <div className="qa-mission-item-body">
                                <input className="qa-input qa-input-mission" placeholder="Mission name..." value={item.title} onChange={e => setItem(realIdx, 'title', e.target.value)} />
                                <div className="qa-mission-item-meta">
                                  <select className="qa-select" value={item.content_type} onChange={e => setItem(realIdx, 'content_type', e.target.value)}>
                                    <option value="material">📖 Course</option><option value="quiz">📝 Quiz</option><option value="todo">✅ To-Do</option><option value="simulation">🎯 Simulation</option>
                                  </select>
                                  <label className="qa-required-toggle" title="ผู้เรียนต้องเรียน?">
                                    <input type="checkbox" checked={item.required !== false} onChange={e => setItem(realIdx, 'required', e.target.checked)} />
                                    <span>{item.required !== false ? '🔒 Required' : '📎 Optional'}</span>
                                  </label>
                                  <label className="qa-ai-gen-toggle" title="AI สร้างเนื้อหาให้ Learner">
                                    <input type="checkbox" checked={!!item.ai_generated} onChange={e => setItem(realIdx, 'ai_generated', e.target.checked)} />
                                    <span>{item.ai_generated ? '🤖 AI Content' : '📄 Manual'}</span>
                                  </label>
                                </div>
                              </div>
                              <button className="qa-btn-x" onClick={() => removeItem(realIdx)}>×</button>
                            </div>
                          );
                        })}

                        {/* Action buttons */}
                        <div className="qa-bi-actions">
                          <button className="qa-btn-add-mission" onClick={() => addItem(bl.order, ai, { title: '', item_type: 'fixed', content_type: 'todo', learning_type: 'experiential', estimated_minutes: 30, required: true, ai_generated: false })}>
                            + Add Mission
                          </button>
                          <button className="qa-btn-add-mission qa-btn-course-pick" onClick={() => setShowPicker(showPicker?.levelOrder === bl.order && showPicker?.areaIdx === ai ? null : { levelOrder: bl.order, areaIdx: ai })}>
                            📚 Pick Course
                          </button>
                          <button className="qa-btn-add-mission qa-btn-ai-gen" onClick={() => addItem(bl.order, ai, { title: `AI: ${area.name}`, item_type: 'fixed', content_type: 'simulation', learning_type: 'experiential', estimated_minutes: 30, required: true, ai_generated: true })}>
                            🤖 AI Generate Mission
                          </button>
                        </div>

                        {/* Course Picker inline */}
                        {showPicker?.levelOrder === bl.order && showPicker?.areaIdx === ai && (
                          <div className="qa-course-picker">
                            <input className="qa-input" placeholder="🔍 ค้นหา Course..." value={courseSearch} onChange={e => setCourseSearch(e.target.value)} />
                            <div className="qa-course-picker-list">
                              {filteredCourses.length === 0 && <div className="qa-picker-empty">ไม่พบ Course</div>}
                              {filteredCourses.map((c, ci) => (
                                <div key={ci} className="qa-course-picker-item" onClick={() => {
                                  addItem(bl.order, ai, { title: c.name, item_type: 'fixed', content_type: 'material', learning_type: 'formal', estimated_minutes: 60, required: true, ai_generated: false, provider: c.provider });
                                  setShowPicker(null); setCourseSearch('');
                                  setMsg(`✅ เพิ่ม "${c.name}" แล้ว`);
                                }}>
                                  <span>📖</span>
                                  <div>
                                    <div className="qa-course-picker-name">{c.name}</div>
                                    <div className="qa-course-picker-meta">{c.provider} · {c.instructor}</div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Areas with no name — show hint */}
              {(bl.areas || []).filter(a => !a.name?.trim()).length > 0 && (
                <div className="qa-bi-empty">💡 กลับไป Step "Levels" เพื่อเพิ่ม Behavioral Index ก่อน</div>
              )}
            </div>
          ))}
        </div>

        <div className="qa-content-side">
          <AIChat skillName={form.skill_name} description={form.description} badgeLevels={form.badge_levels} existingItems={form.items}
            onAddItem={(item) => {
              const maxOrder = form.items.reduce((m, it) => Math.max(m, it.order || 0), 0);
              const al = activeLevel || form.badge_levels[0]?.order || 1;
              const bl = form.badge_levels.find(b => b.order === al);
              const firstArea = bl?.areas?.findIndex(a => a.name?.trim()) ?? 0;
              set('items', [...form.items, { ...item, order: maxOrder + 1, badge_level_order: al, area_index: Math.max(0, firstArea), required: true, ai_generated: false }]);
              setMsg('✅ Mission added!');
            }} />
        </div>
      </div>
    </div>
  );
}

/* ── Phase 4: Rewards ── */
function PhaseRewards({ form, set, levelReady }) {
  const [selectedTemplates, setSelectedTemplates] = useState(form.achievement_badges || []);

  const toggleTemplate = (tmpl) => {
    setSelectedTemplates(prev => {
      const exists = prev.find(t => t.id === tmpl.id);
      const next = exists ? prev.filter(t => t.id !== tmpl.id) : [...prev, { ...tmpl, customVal: tmpl.defaultVal }];
      set('achievement_badges', next);
      return next;
    });
  };

  const setTemplateVal = (id, val) => {
    setSelectedTemplates(prev => {
      const next = prev.map(t => t.id === id ? { ...t, customVal: val } : t);
      set('achievement_badges', next);
      return next;
    });
  };

  const totalMissions = form.items.length;
  const totalAreas = form.badge_levels.reduce((s, bl) => s + (bl.areas?.filter(a => a.name?.trim()).length || 0), 0);

  return (
    <div className="qa-rewards-phase">
      <h2 className="qa-card-title">🏅 Victory Conditions & Rewards</h2>
      <p className="qa-card-desc">กำหนดเงื่อนไขการได้รับ Badge และ Achievement Rewards</p>

      {/* EXP Summary */}
      <div className="qa-exp-summary">
        <div className="qa-exp-item"><div className="qa-exp-num">{form.badge_levels.length}</div><div className="qa-exp-label">Levels</div></div>
        <div className="qa-exp-item"><div className="qa-exp-num">{totalAreas}</div><div className="qa-exp-label">Areas</div></div>
        <div className="qa-exp-item"><div className="qa-exp-num">{totalMissions}</div><div className="qa-exp-label">Missions</div></div>
        <div className="qa-exp-item">
          <div className="qa-exp-bar-container">
            <div className="qa-exp-bar-fill" style={{ width: `${Math.min(100, (totalMissions / Math.max(1, form.badge_levels.length * 3)) * 100)}%` }} />
          </div>
          <div className="qa-exp-label">Quest EXP</div>
        </div>
      </div>

      {/* Skill Badge Logic */}
      <div className="qa-reward-section">
        <div className="qa-reward-header">🎖️ Skill Badge (per Level)</div>
        <div className="qa-badge-toggle">
          <label className="qa-toggle">
            <input type="checkbox" checked={form.badge_auto_issue !== false} onChange={e => set('badge_auto_issue', e.target.checked)} />
            <span className="qa-toggle-slider" />
          </label>
          <span>Auto-issue badge upon mission completion</span>
        </div>

        {form.badge_levels.map((bl, i) => (
          <div key={i} className="qa-reward-level" style={{ '--lc': LEVEL_COLORS[i] }}>
            <div className="qa-reward-level-head">
              <span className={`qa-level-status ${levelReady(bl) ? 'ready' : 'missing'}`}>{levelReady(bl) ? '🟢' : '🔴'}</span>
              <span className="qa-reward-level-icon" style={{ background: LEVEL_COLORS[i] }}>{LEVEL_ICONS[i]}</span>
              <span>Level {bl.order}: {bl.name}</span>
            </div>
            <div className="qa-reward-level-body">
              <div className="qa-reward-condition">
                <span>🎯 Victory: Complete all missions in this level</span>
              </div>
              <div className="qa-reward-missions">{form.items.filter(it => it.badge_level_order === bl.order).length} missions assigned</div>
            </div>
          </div>
        ))}
      </div>

      {/* Achievement Badge Templates */}
      <div className="qa-reward-section">
        <div className="qa-reward-header">🏆 Achievement Badges (Template Gallery)</div>
        <div className="qa-badge-gallery">
          {BADGE_TEMPLATES.map(tmpl => {
            const selected = selectedTemplates.find(t => t.id === tmpl.id);
            return (
              <div key={tmpl.id} className={`qa-badge-tmpl ${selected ? 'selected' : ''}`} onClick={() => toggleTemplate(tmpl)}>
                <div className="qa-badge-tmpl-icon">{tmpl.icon}</div>
                <div className="qa-badge-tmpl-name">{tmpl.name}</div>
                <div className="qa-badge-tmpl-desc">{tmpl.desc.replace(`{${tmpl.variable}}`, selected?.customVal || tmpl.defaultVal || '—')}</div>
                {selected && tmpl.variable && (
                  <div className="qa-badge-tmpl-custom" onClick={e => e.stopPropagation()}>
                    <input type="number" className="qa-input qa-input-xs" value={selected.customVal || tmpl.defaultVal}
                      onChange={e => setTemplateVal(tmpl.id, parseInt(e.target.value) || tmpl.defaultVal)} />
                    <span>{tmpl.variable}</span>
                  </div>
                )}
                <div className="qa-badge-tmpl-check">{selected ? '✓' : '+'}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}


/* ── Learner Preview Mode ── */
function LearnerPreview({ form, onClose }) {
  return (
    <div className="qa-page">
      <div className="qa-preview-banner">
        <span>👁️ Learner Preview Mode</span>
        <button className="qa-btn-back" onClick={onClose}>✕ Exit Preview</button>
      </div>
      <div className="qa-preview-content">
        <div className="qa-preview-hero">
          <div className="qa-preview-hero-icon">⚔️</div>
          <h2>{form.title || form.skill_name || 'Quest Name'}</h2>
          <p>{form.description?.slice(0, 200) || 'Quest description...'}</p>
          <button className="qa-btn-join">🚀 Join Quest</button>
        </div>
        <div className="qa-preview-roadmap">
          <div className="qa-preview-roadmap-title">🗺️ Quest Roadmap</div>
          {form.badge_levels.map((bl, i) => {
            const missions = form.items.filter(it => it.badge_level_order === bl.order);
            return (
              <div key={i} className="qa-preview-level" style={{ '--lc': LEVEL_COLORS[i] }}>
                <div className="qa-preview-level-head">
                  <span className="qa-preview-level-icon" style={{ background: LEVEL_COLORS[i] }}>{LEVEL_ICONS[i]}</span>
                  <div>
                    <div className="qa-preview-level-name">Level {bl.order}: {bl.name}</div>
                    <div className="qa-preview-level-meta">{missions.length} missions · {bl.areas?.filter(a => a.name?.trim()).length || 0} areas</div>
                  </div>
                  {i > 0 && <span className="qa-preview-lock">🔒</span>}
                </div>
                <div className="qa-preview-missions">
                  {missions.map((m, mi) => (
                    <div key={mi} className="qa-preview-mission">
                      <span className="qa-preview-mission-dot" />{m.title || 'Unnamed mission'}
                    </div>
                  ))}
                  {missions.length === 0 && <div className="qa-preview-no-mission">No missions yet</div>}
                </div>
                <div className="qa-preview-exp-bar"><div className="qa-preview-exp-fill" style={{ width: '0%' }} /><span>0 / {missions.length} EXP</span></div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ── AI Chat (Missions sidebar) ── */
function AIChat({ skillName, description, badgeLevels, existingItems, onAddItem }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);

  const send = async (text) => {
    if (!text.trim() || streaming) return;
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput(''); setStreaming(true);
    try {
      const r = await fetch(`${API}/api/dashboard/skill-path/ai-suggest?stream=1`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, skill_name: skillName, description, badge_levels: badgeLevels, existing_items: existingItems, chat_history: messages.slice(-10) }),
      });
      const reader = r.body.getReader(); const dec = new TextDecoder();
      let full = '', suggestions = [];
      setMessages(prev => [...prev, { role: 'assistant', content: '', suggestions: [] }]);
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        for (const line of dec.decode(value).split('\n').filter(l => l.startsWith('data: '))) {
          try {
            const d = JSON.parse(line.slice(6));
            if (d.done) { suggestions = d.suggestions || []; if (d.clean_text) full = d.clean_text; } else if (d.text) full += d.text;
            setMessages(prev => { const c = [...prev]; c[c.length - 1] = { role: 'assistant', content: full, suggestions }; return c; });
          } catch {}
        }
      }
    } catch { setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error. Try again.', suggestions: [] }]); }
    setStreaming(false);
  };

  return (
    <div className="qa-ai-panel">
      <div className="qa-ai-head">🤖 AI Mission Advisor</div>
      <div className="qa-ai-msgs">
        {messages.length === 0 && (
          <div className="qa-ai-welcome">
            <p>Ask AI to suggest missions</p>
            <div className="qa-ai-quick">
              <button onClick={() => send(`Suggest learning missions for ${skillName || 'this skill'}`)}>💡 Suggest Missions</button>
              <button onClick={() => send(`Create a 10-20-70 learning plan for ${skillName || 'this skill'}`)}>📚 10-20-70 Plan</button>
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`qa-ai-msg qa-ai-msg-${m.role}`}>
            <div className="qa-ai-msg-text">{m.content}</div>
            {m.suggestions?.length > 0 && (
              <div className="qa-ai-sugs">
                {m.suggestions.map((s, si) => (
                  <div key={si} className="qa-ai-sug" onClick={() => onAddItem({ title: s.title || '', content_type: s.content_type || 'material', learning_type: s.learning_type || 'formal', item_type: 'fixed', estimated_minutes: s.estimated_minutes || 30 })}>
                    <div className="qa-ai-sug-title">{s.title}</div>
                    <div className="qa-ai-sug-meta">{s.content_type} · {s.estimated_minutes || '?'}min</div>
                    <div className="qa-ai-sug-add">+ Add to Quest</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="qa-ai-input-row">
        <input className="qa-input qa-ai-input" placeholder="Ask AI..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send(input)} disabled={streaming} />
        <button className="qa-btn-send" onClick={() => send(input)} disabled={streaming}>{streaming ? '⏳' : '➤'}</button>
      </div>
    </div>
  );
}
