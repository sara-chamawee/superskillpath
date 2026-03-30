import { useState, useEffect, useRef } from 'react';
import { fetchSkills } from '../utils/api';

const SKILL_ICONS = ['🧠', '💡', '🎯', '🔥', '⚡', '🌟', '🚀', '💎', '🎨', '🔍'];

export default function SkillCatalog({ onSelectSkill, selectedSkills, onToggleSelect }) {
  const [skills, setSkills] = useState([]);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [publishedSkills, setPublishedSkills] = useState(null);
  const timer = useRef(null);
  const API = import.meta.env.VITE_API_URL || '';

  const load = async (q, p, append = false) => {
    const data = await fetchSkills(q, p);
    setTotal(data.total);
    setSkills(prev => append ? [...prev, ...data.skills] : data.skills);
  };

  useEffect(() => {
    load('', 1);
    fetch(`${API}/api/skill-paths`).then(r => r.json()).then(d => {
      setPublishedSkills(new Set((d.results || []).map(t => t.skill_name)));
    }).catch(() => setPublishedSkills(new Set()));
  }, []);

  const onSearch = (e) => {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => { setPage(1); load(q, 1); }, 300);
  };

  const loadMore = () => { const next = page + 1; setPage(next); load(query, next, true); };
  const isSelected = (id) => selectedSkills?.some(s => s.id === id);
  const visibleSkills = publishedSkills ? skills.filter(s => publishedSkills.has(s.name)) : [];

  return (
    <div className="catalog">
      {/* Hero */}
      <div className="cat-hero">
        <div className="cat-hero-emoji">🧠</div>
        <h1>เครื่องมือออกแบบ SuperPath ของคุณ</h1>
        <p>เส้นทางสู่การเติบโตของคุณเริ่มต้นที่นี่!</p>
      </div>

      {/* Selected skills */}
      {selectedSkills?.length > 0 && (
        <div style={{ padding: '16px 40px 0' }}>
          <div style={{ fontSize: '.82em', fontWeight: 600, color: 'var(--text2)', marginBottom: 8 }}>⭐ ทักษะที่เลือก ({selectedSkills.length})</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {selectedSkills.map(s => (
              <div key={s.id} style={{ background: 'var(--primary-light)', border: '1.5px solid var(--primary)', borderRadius: 10, padding: '6px 14px', display: 'flex', alignItems: 'center', gap: 10, fontSize: '.82em' }}>
                <span style={{ fontWeight: 600, color: 'var(--primary)' }}>{s.name}</span>
                <button className="btn btn-primary" style={{ fontSize: '.7em', padding: '3px 10px' }} onClick={() => onSelectSkill(s.id)}>เข้าเรียน →</button>
                <span style={{ cursor: 'pointer', color: 'var(--text3)', fontSize: '.8em' }} onClick={() => onToggleSelect(s)}>✕</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="cat-top">
        <h2>SuperPath ล่าสุด</h2>
        <input className="search" placeholder="🔍 ค้นหาทักษะ..." value={query} onChange={onSearch} />
      </div>

      {publishedSkills === null ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text3)' }}>⏳ กำลังโหลดทักษะ...</div>
      ) : (
        <>
          <div className="cat-info">{visibleSkills.length} ทักษะที่พร้อมเรียน</div>
          <div className="grid">
            {visibleSkills.map((s, i) => (
              <div key={s.id} className="skill-card" style={{ borderColor: isSelected(s.id) ? 'var(--primary)' : undefined }}>
                <div className="skill-icon">{SKILL_ICONS[i % SKILL_ICONS.length]}</div>
                <div className="skill-body">
                  <div>
                    <span className="tag">⚔️ Quest Ready</span>
                    {s.domain && <span className="tag" style={{ background: '#f0edff', color: '#6c5ce7' }}>{s.domain}</span>}
                  </div>
                  <h3>{s.name}</h3>
                  <div className="desc">{s.definition}</div>
                  <div className="skill-footer">
                    <div className="meta">
                      <span>📚 {s.num_areas} ด้าน</span>
                      <span>✅ {s.num_checklist_items} items</span>
                    </div>
                  </div>
                </div>
                <div className="skill-actions">
                  <button className={`btn ${isSelected(s.id) ? 'btn-green' : 'btn-outline'}`} style={{ fontSize: '.72em' }}
                    onClick={() => onToggleSelect(s)}>{isSelected(s.id) ? '✓ เลือกแล้ว' : '+ เลือก'}</button>
                  <button className="btn btn-primary" style={{ fontSize: '.72em' }}
                    onClick={() => onSelectSkill(s.id)}>เข้าเรียน →</button>
                </div>
              </div>
            ))}
          </div>
          {visibleSkills.length === 0 && <div style={{ textAlign: 'center', padding: 60, color: 'var(--text3)' }}>🔍 ไม่พบทักษะที่ตรงกับคำค้นหา</div>}
          {page * 20 < total && <button className="more-btn" onClick={loadMore}>โหลดเพิ่ม</button>}
        </>
      )}
    </div>
  );
}
