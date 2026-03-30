export default function Nav({ onHome, currentView, onAdmin }) {
  return (
    <nav className="nav">
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div className="logo" style={{ cursor: 'pointer' }} onClick={onHome}><span>✦</span> SuperPath</div>
        {currentView === 'admin' ? (
          <>
            <button className="nav-btn" onClick={onHome}>← กลับหน้าหลัก</button>
            <button className="nav-btn active">Admin</button>
          </>
        ) : (
          <>
            <button className="nav-btn" onClick={onHome}>← ย้อนกลับ</button>
            <button className="nav-btn active">Skills</button>
          </>
        )}
      </div>
      <div className="nav-right">
        {currentView !== 'admin' && (
          <button className="nav-btn nav-btn-admin" onClick={onAdmin} title="จัดการ Skill Path">
            ⚙️ Admin
          </button>
        )}
        <button className="nav-btn">บันทึก</button>
        <div className="avatar">C</div>
      </div>
    </nav>
  );
}
