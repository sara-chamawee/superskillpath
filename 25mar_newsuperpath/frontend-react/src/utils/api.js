const API = '';

export async function fetchSkills(q = '', page = 1, limit = 20) {
  const res = await fetch(`${API}/api/skills?q=${encodeURIComponent(q)}&page=${page}&limit=${limit}`);
  return res.json();
}

export async function fetchSkillDetail(id) {
  const res = await fetch(`${API}/api/skills/${id}`);
  return res.json();
}

export async function startChat(userId, skillId) {
  const res = await fetch(`${API}/api/chat/start`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, skill_id: skillId }),
  });
  return res.json();
}

export async function streamMessage(sessionId, message) {
  return fetch(`${API}/api/chat/${sessionId}/stream`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
}

export async function fetchProgress(sessionId) {
  const res = await fetch(`${API}/api/chat/${sessionId}/progress`);
  return res.json();
}

export async function assessSkill(userId, skillId, completedCourses, completedTodos) {
  const res = await fetch(`${API}/api/assess-skill`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, skill_id: skillId, completed_courses: completedCourses, completed_todos: completedTodos }),
  });
  return res.json();
}
