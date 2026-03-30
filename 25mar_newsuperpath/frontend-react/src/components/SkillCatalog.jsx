import { useState, useEffect, useRef } from 'react';
import { fetchSkills } from '../utils/api';

export default function SkillCatalog({ onSelectSkill, selectedSkills, onToggleSelect }) {
  const [skills, setSkills] = useState([]);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const timer = useRef(null);

  const load = async (q, p, append = false) => {
    const data = await fetchSkills(q, p);
    setTotal(data.total);
    setSkills(prev => append ? [...prev, ...data.skills] : data.skills);
  };

  useEffect(() => { load('', 1); }, []);

  const onSearch = (e) => {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => { setPage(1); load(q, 1); }, 300);
  };

  const loadMore = () => { const next = page + 1; setPage(next); load(query, next, true); };
  const isSelected = (id) => selectedSkills?.some(s => s.id === id);

  return (
    <div className="catalog">
      {/* Selected skills section */}
      {selectedSkills?.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: '1.1em', fontWeight: 700, color: 'var(--primary)', marginBottom: 12 }}>⭐ ทักษะที่เลือก ({selectedSkills.length})</h2>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {selectedSkills.map(s => (
              <div key={s.id} style={{ background: '#f0edff', border: '1.5px solid var(--purple)', borderRadius: 'var(--radius)', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}
                onClick={() => onSelectSkill(s.id)}>
                <div>
                  <div style={{ fontSize: '.85em', fontWeight: 600, color: 'var(--primary)' }}>{s.name}</div>
                  <div style={{ fontSize: '.72em', color: 'var(--text3)' }}>{s.domain}</div>
                </div>
                <button className="btn btn-primary" style={{ fontSize: '.72em', padding: '4px 12px' }}>เข้าเรียน →</button>
                <button style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '.8em', color: 'var(--text3)' }}
                  onClick={(e) => { e.stopPropagation(); onToggleSelect(s); }}>✕</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="cat-top">
        <div>
          <h1>เลือกทักษะที่ต้องการพัฒนา</h1>
          <p>เลือกทักษะแล้ว AI จะสร้างแผนการเรียนตาม 10-20-70 ให้อัตโนมัติ</p>
        </div>
        <input className="search" placeholder="🔍 ค้นหาทักษะ..." value={query} onChange={onSearch} />
      </div>
      <div className="cat-info">แสดง {Math.min(page * 20, total)} จาก {total} ทักษะ</div>
      <div className="grid">
        {skills.map(s => (
          <div key={s.id} className="skill-card" style={{ border: isSelected(s.id) ? '2px solid var(--purple)' : undefined }}>
            {s.domain && <span className="tag">{s.domain}</span>}
            <h3>{s.name}</h3>
            <div className="desc">{s.definition}</div>
            <div className="meta" style={{ marginBottom: 8 }}>
              <span>📚 {s.num_areas} ด้าน</span>
              <span>✅ {s.num_checklist_items} items</span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className={`btn ${isSelected(s.id) ? 'btn-green' : 'btn-blue'}`} style={{ fontSize: '.72em', flex: 1 }}
                onClick={() => onToggleSelect(s)}>{isSelected(s.id) ? '✓ เลือกแล้ว' : '+ เลือกทักษะ'}</button>
              <button className="btn btn-primary" style={{ fontSize: '.72em' }}
                onClick={() => onSelectSkill(s.id)}>เข้าเรียน →</button>
            </div>
          </div>
        ))}
      </div>
      {page * 20 < total && <button className="more-btn" onClick={loadMore}>โหลดเพิ่ม</button>}
    </div>
  );
}
