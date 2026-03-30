import { useState, useRef, useEffect } from 'react';
import { streamMessage } from '../utils/api';
import { renderMarkdown } from '../utils/markdown';
import { speak } from '../utils/tts';

const COACHES = [
  { name: 'Sorc AI', emoji: '✨', personality: 'กระตือรือร้น ให้กำลังใจ' },
  { name: 'Dr. Wise', emoji: '🧠', personality: 'วิเคราะห์ลึก ให้เหตุผล' },
  { name: 'Coach Panda', emoji: '🐼', personality: 'ใจเย็น อธิบายง่าย' },
  { name: 'Sensei Fox', emoji: '🦊', personality: 'ท้าทาย กระตุ้นคิด' },
  { name: 'Buddy Bot', emoji: '🤖', personality: 'เป็นกันเอง สนุกสนาน' },
];

const BG_COLORS = ['#ffffff', '#f8f6ff', '#f0f7ff', '#f0faf4', '#fff8f0', '#fff0f5', '#f5f5f5', '#fffde7'];

export default function ChatPanel({ sessionId, expanded, onToggle, messages, setMessages, onAIResponse, onPickMode, path, courses, onToggleCourse, todos, onAddTodo, sendRef }) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [bgColor, setBgColor] = useState('#ffffff');
  const [bubbleStyle, setBubbleStyle] = useState('normal');
  const [fontSize, setFontSize] = useState('medium');
  const [coach, setCoach] = useState(COACHES[0]);
  const [showCoachPicker, setShowCoachPicker] = useState(false);
  const msgsRef = useRef(null);
  const sessionRef = useRef(sessionId);

  useEffect(() => { sessionRef.current = sessionId; }, [sessionId]);
  useEffect(() => { if (msgsRef.current) msgsRef.current.scrollTop = 99999; }, [messages]);

  const send = async (text) => {
    const msg = text || input.trim();
    const sid = sessionRef.current;
    if (!msg || !sid) return;
    setInput('');
    setSending(true);
    const aiId = 'ai-' + Date.now();
    const now = new Date().toLocaleString('th-TH', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    setMessages(prev => prev.filter(m => m.role !== 'mode-picker').concat([{ role: 'user', content: msg, time: now }, { role: 'assistant', content: '', id: aiId, time: now }]));
    try {
      const res = await streamMessage(sid, msg);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let full = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of dec.decode(value).split('\n').filter(l => l.startsWith('data: '))) {
          try { const d = JSON.parse(line.slice(6)); if (d.text) { full += d.text; setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: full } : m)); } } catch {}
        }
      }
      if (onAIResponse) onAIResponse(msg, full);
    } catch { setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: 'เกิดข้อผิดพลาด' } : m)); }
    setSending(false);
  };

  useEffect(() => { if (sendRef) sendRef.current = send; });

  const fontSizeClass = fontSize === 'small' ? 'fs-small' : fontSize === 'large' ? 'fs-large' : '';
  const bubbleClass = bubbleStyle === 'round' ? 'bbl-round' : bubbleStyle === 'square' ? 'bbl-square' : '';

  const renderMsg = (m, i) => {
    if (m.role === 'mode-picker') return <ModePicker key={i} onPick={onPickMode} />;
    if (m.role === 'course-suggestions') return <CourseSuggestions key={i} courses={m.courses} path={path} onToggle={onToggleCourse} />;
    if (m.role === 'todo-suggestions') return <TodoSuggestions key={i} items={m.items} todos={todos} onAdd={onAddTodo} />;
    if (m.role === 'sim-added') return (
      <div key={i} className="m assistant">
        <div className="m-avatar">{coach.emoji}</div>
        <div className="m-body">
          <div className="m-meta"><span className="m-name">{coach.name}</span>{m.time && <span className="m-time">{m.time}</span>}</div>
          <div className="suggest-card" style={{ borderColor: '#fcc' }}>
            <h5>🎯 Simulation สร้างเสร็จแล้ว!</h5>
            <p style={{ fontSize: '.82em', color: 'var(--text2)', margin: '6px 0' }}>{m.title}</p>
            <p style={{ fontSize: '.78em', color: 'var(--text3)', margin: '4px 0' }}>กดที่ sidebar เพื่อดูสถานการณ์ ยืนยัน แล้วพิมพ์คำตอบได้เลย</p>
          </div>
        </div>
      </div>
    );
    if (m.role === 'quiz-added') return (
      <div key={i} className="m assistant">
        <div className="m-avatar">{coach.emoji}</div>
        <div className="m-body">
          <div className="m-meta"><span className="m-name">{coach.name}</span>{m.time && <span className="m-time">{m.time}</span>}</div>
          <div className="suggest-card" style={{ borderColor: '#b2dfdb' }}>
            <h5>📝 Quiz ทบทวนพร้อมแล้ว!</h5>
            <p style={{ fontSize: '.82em', color: 'var(--text2)', margin: '6px 0' }}>สร้าง Quiz {m.count} ข้อเรียบร้อย</p>
            <p style={{ fontSize: '.78em', color: 'var(--text3)', margin: '4px 0' }}>กดที่ sidebar เพื่อเริ่มทำ Quiz ได้เลย</p>
          </div>
        </div>
      </div>
    );
    const isAI = m.role === 'assistant';
    return (
      <div key={i} className={`m ${m.role}`}>
        <div className="m-avatar">{isAI ? coach.emoji : '👤'}</div>
        <div className="m-body">
          <div className="m-meta">
            <span className="m-name">{isAI ? coach.name : 'คุณ'}</span>
            {m.time && <span className="m-time">{m.time}</span>}
          </div>
          <div className={`mb ${bubbleClass}`} dangerouslySetInnerHTML={{ __html: isAI ? renderMarkdown(m.content) : m.content }} />
          {isAI && m.content && (
            <button className="tts-btn" onClick={(e) => { const btn = e.target; const playing = speak(btn.closest('.m-body').querySelector('.mb').innerText, () => { btn.textContent = '🔊'; }); btn.textContent = playing ? '⏹' : '🔊'; }}>🔊</button>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`cp${expanded ? ' expanded' : ''}`}>
      <div className="cp-top">
        <span style={{ fontSize: '1.1em', cursor: 'pointer' }} onClick={() => setShowCoachPicker(!showCoachPicker)}>{coach.emoji}</span>
        <h3>AI Coach</h3>
        <span className="ai-badge" style={{ cursor: 'pointer' }} onClick={() => setShowCoachPicker(!showCoachPicker)}>{coach.name} ▾</span>
        <button className="cp-settings-btn" onClick={() => { setShowSettings(!showSettings); setShowCoachPicker(false); }} title="ตั้งค่าแชท">⚙️</button>
        <button className="cp-toggle" onClick={onToggle}>{expanded ? '➡ หด' : '⬅ ขยาย'}</button>
      </div>

      {showCoachPicker && (
        <div className="coach-picker">
          <div className="coach-picker-title">เลือก AI Coach</div>
          {COACHES.map(c => (
            <button key={c.name} className={`coach-opt${coach.name === c.name ? ' active' : ''}`} onClick={() => { setCoach(c); setShowCoachPicker(false); }}>
              <span className="coach-emoji">{c.emoji}</span>
              <div>
                <div className="coach-name">{c.name}</div>
                <div className="coach-desc">{c.personality}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {showSettings && (
        <div className="chat-settings">
          <div className="cs-section">
            <div className="cs-label">สีพื้นหลัง</div>
            <div className="cs-colors">
              {BG_COLORS.map(c => (
                <button key={c} className={`cs-color${bgColor === c ? ' active' : ''}`} style={{ background: c }} onClick={() => setBgColor(c)} />
              ))}
            </div>
          </div>
          <div className="cs-section">
            <div className="cs-label">รูปแบบกล่องข้อความ</div>
            <div className="cs-row">
              {[['normal', 'ปกติ'], ['round', 'กลม'], ['square', 'เหลี่ยม']].map(([k, label]) => (
                <button key={k} className={`cs-opt${bubbleStyle === k ? ' active' : ''}`} onClick={() => setBubbleStyle(k)}>{label}</button>
              ))}
            </div>
          </div>
          <div className="cs-section">
            <div className="cs-label">ขนาดตัวอักษร</div>
            <div className="cs-row">
              {[['small', 'เล็ก'], ['medium', 'กลาง'], ['large', 'ใหญ่']].map(([k, label]) => (
                <button key={k} className={`cs-opt${fontSize === k ? ' active' : ''}`} onClick={() => setFontSize(k)}>{label}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className={`msgs ${fontSizeClass}`} ref={msgsRef} style={{ background: bgColor }}>{messages.map(renderMsg)}</div>
      <div className="ci-row">
        <button className="ci-q" onClick={() => send('แนะนำเนื้อหาสำหรับทักษะนี้')}>✨ เนื้อหา</button>
        <button className="ci-q" onClick={() => send('สร้างสถานการณ์จำลอง 1 ข้อ')}>🎯 Simulation</button>
        <button className="ci-q" onClick={() => send('สร้าง To-Do List 3 ข้อ')}>📝 To-Do</button>
      </div>
      <div className="ci-row">
        <input className="ci-in" placeholder={`คุยกับ ${coach.name} ได้เลย...`} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} />
        <button className="ci-s" disabled={sending} onClick={() => send()}>➤</button>
      </div>
    </div>
  );
}

function ModePicker({ onPick }) {
  return (
    <div className="m assistant">
      <div className="mb"><p style={{ marginBottom: 12 }}><strong>คุณชอบเรียนรู้แบบไหนครับ?</strong></p></div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
        {[
          { key: 'courses', icon: '📚', title: 'เรียนคอร์สก่อน', desc: 'ดูเนื้อหาที่แนะนำ เรียนตามลำดับ' },
          { key: 'scenario', icon: '🎯', title: 'สรุป + จำลองสถานการณ์', desc: 'AI สรุปให้ แล้วถามจากสถานการณ์จริง' },
          { key: 'todo', icon: '🛠️', title: 'ลงมือทำจริง', desc: 'AI สร้าง To-Do List ให้ทำแล้วส่งงาน' },
          { key: 'auto', icon: '🤖', title: 'AI จัดให้ตาม 10-20-70', desc: 'AI จัดเส้นทางครบ: คอร์ส + Simulation + To-Do' },
        ].map(m => (
          <button key={m.key} className="mode-btn" onClick={() => onPick(m.key)}>
            <span className="mode-icon">{m.icon}</span>
            <div><strong>{m.title}</strong><div className="mode-desc">{m.desc}</div></div>
          </button>
        ))}
      </div>
    </div>
  );
}

function CourseSuggestions({ courses, path, onToggle }) {
  return (
    <div className="m assistant">
      <div className="suggest-card">
        <h5>📌 คอร์สที่มี — เลือกเพิ่มเข้า SuperPath</h5>
        {courses.map((c, i) => {
          const inP = path?.find(p => p.idx === i && p.in);
          return (
            <div key={i} className="suggest-item" style={{ padding: '10px 0' }}>
              <span className="s-name" style={{ flex: 1, lineHeight: 1.4 }}>{c.name}</span>
              <span style={{ fontSize: '.75em', color: 'var(--text3)', minWidth: 120, textAlign: 'right', marginRight: 10 }}>{c.instructor}</span>
              <button
                className={`btn-add ${inP ? 'added' : ''}`}
                style={{ minWidth: 70, padding: '6px 14px', borderRadius: 8, fontSize: '.8em', fontWeight: 600 }}
                onClick={() => onToggle(i)}
              >{inP ? '✓' : '+ เพิ่ม'}</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TodoSuggestions({ items, todos, onAdd }) {
  const addAll = () => items.forEach(item => onAdd(item.substring(0, 60), item));
  return (
    <div className="m assistant">
      <div className="suggest-card">
        <h5>📝 เลือกเพิ่ม To-Do เข้า SuperPath</h5>
        <button className="btn-add" style={{ marginBottom: 10, background: 'var(--text)', fontSize: '.78em', padding: '5px 12px' }} onClick={addAll}>+ เพิ่มทั้งหมด</button>
        {items.map((item, i) => {
          const short = item.substring(0, 60);
          const exists = todos?.find(t => t.title === short);
          return (
            <div key={i} className="suggest-item" style={{ padding: '10px 0' }}>
              <span className="s-name" style={{ flex: 1, lineHeight: 1.4 }}>{item.substring(0, 120)}</span>
              <button
                className={`btn-add ${exists ? 'added' : ''}`}
                style={{ minWidth: 70, padding: '6px 14px', borderRadius: 8, fontSize: '.8em', fontWeight: 600 }}
                onClick={() => onAdd(short, item)}
              >{exists ? '✓' : '+ เพิ่ม'}</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
