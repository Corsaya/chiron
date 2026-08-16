import { mdToHtml, sanitizeAllowedHtml } from '/static/js/markdown.js';

const sideEl = document.getElementById('side');
const mainEl = document.getElementById('main');
const tutorEl = document.getElementById('tutor');
const tutorMsgsEl = document.getElementById('tutor-msgs');
const tutorInputEl = document.getElementById('tutor-input');
const tutorSendEl = document.getElementById('tutor-send');

const icon = (type) => type === 'section' ? '📁' : type === 'custom_app' ? '🧮' : '📄';

async function api(path, opts) {
  const res = await fetch(path, { credentials: 'same-origin', ...opts });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

function esc(s) { return (s || '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }

// ---------------------------------------------------------------- progress --
const PROGRESS_KEY = 'chiron_classroom_progress_v1';
function loadProgress() {
  try { return JSON.parse(localStorage.getItem(PROGRESS_KEY) || '{}'); } catch (e) { return {}; }
}
function saveProgress(p) { localStorage.setItem(PROGRESS_KEY, JSON.stringify(p)); }
function isDone(classroomName, path) { return !!(loadProgress()[classroomName] || {})[path]; }
function setDone(classroomName, path, done) {
  const p = loadProgress();
  p[classroomName] = p[classroomName] || {};
  if (done) p[classroomName][path] = true; else delete p[classroomName][path];
  saveProgress(p);
}
function countLeaves(items) {
  let total = 0, done = 0;
  const walk = (list, classroomName) => list.forEach(item => {
    if (item.type === 'section') { walk(item.items, classroomName); return; }
    total++;
    if (isDone(classroomName, item.path)) done++;
  });
  return { total, done, walk };
}
function classroomProgress(classroomName, items) {
  let total = 0, done = 0;
  (function walk(list) {
    list.forEach(item => {
      if (item.type === 'section') { walk(item.items); return; }
      total++;
      if (isDone(classroomName, item.path)) done++;
    });
  })(items);
  return { total, done, pct: total ? Math.round(100 * done / total) : 0 };
}

// ---------------------------------------------------------------- state --
let state = { classrooms: [], current: null, materials: [], activePath: null, activeTitle: null, tutorHistory: [] };

// ---------------------------------------------------------------- sidebar --
async function renderSidebar() {
  if (!state.classrooms.length) { sideEl.innerHTML = ''; return; }
  const parts = [`<div class="crumb"><a id="side-home">All classrooms</a></div>`];
  for (const c of state.classrooms) {
    const open = state.current === c.name;
    let materialsHtml = '';
    let prog = null;
    if (open && state.materials.length) {
      prog = classroomProgress(c.name, state.materials);
      materialsHtml = renderSideMaterials(state.materials, c.name);
    }
    parts.push(`
      <div class="side-classroom">
        <div class="side-classroom-head" data-classroom="${esc(c.name)}">
          <span>${esc(c.name)}</span>
          ${prog ? `<span class="progress-pill ${prog.pct === 100 ? 'done' : ''}">${prog.done}/${prog.total}</span>` : ''}
        </div>
        <div class="side-materials ${open ? 'open' : ''}">${materialsHtml}</div>
      </div>`);
  }
  sideEl.innerHTML = parts.join('');
  document.getElementById('side-home')?.addEventListener('click', showClassrooms);
  sideEl.querySelectorAll('[data-classroom]').forEach(el => {
    el.addEventListener('click', () => showClassroom(el.dataset.classroom));
  });
  sideEl.querySelectorAll('.side-item[data-path]').forEach(el => {
    el.addEventListener('click', () => {
      if (el.dataset.type === 'custom_app') openApp(el.dataset.app);
      else openNote(state.current, el.dataset.path, el.dataset.title);
    });
  });
}

function renderSideMaterials(items, classroomName, depth = 0) {
  return items.map(item => {
    if (item.type === 'section') {
      return `<div class="side-section-title">${esc(item.name)}</div>${renderSideMaterials(item.items, classroomName, depth + 1)}`;
    }
    const done = isDone(classroomName, item.path);
    const active = state.activePath === item.path;
    return `<div class="side-item ${active ? 'active' : ''}" data-path="${esc(item.path)}" data-type="${item.type}" data-app="${esc(item.app_url || '')}" data-title="${esc(item.name)}">
      <span class="check">${done ? '✓' : ''}</span><span class="icon">${icon(item.type)}</span><span class="lbl">${esc(item.name)}</span>
    </div>`;
  }).join('');
}

// ---------------------------------------------------------------- classrooms list --
async function showClassrooms() {
  location.hash = '';
  state.current = null; state.activePath = null;
  hideTutor();
  mainEl.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const { classrooms } = await api('/api/classrooms');
    state.classrooms = classrooms;
    if (!classrooms.length) {
      mainEl.innerHTML = '<div class="empty">No classrooms found under Courses/ yet.</div>';
      sideEl.innerHTML = '';
      return;
    }
    // Need each classroom's materials to compute progress bars on the grid.
    const withMaterials = await Promise.all(classrooms.map(async c => {
      try { const d = await api(`/api/classrooms/${encodeURIComponent(c.name)}`); return { ...c, materials: d.materials }; }
      catch (e) { return { ...c, materials: [] }; }
    }));
    mainEl.innerHTML = `<div class="grid">${withMaterials.map(c => {
      const prog = classroomProgress(c.name, c.materials);
      return `<div class="card" data-classroom="${esc(c.name)}">
        <div class="name">${esc(c.name)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${prog.pct}%"></div></div>
        <div class="pct">${prog.total ? `${prog.done}/${prog.total} complete` : 'No materials yet'}</div>
      </div>`;
    }).join('')}</div>`;
    mainEl.querySelectorAll('[data-classroom]').forEach(el => {
      el.addEventListener('click', () => showClassroom(el.dataset.classroom));
    });
    renderSidebar();
  } catch (e) {
    mainEl.innerHTML = `<div class="empty">Failed to load classrooms: ${esc(e.message)}</div>`;
  }
}

// ---------------------------------------------------------------- one classroom --
async function showClassroom(name) {
  location.hash = `#/${encodeURIComponent(name)}`;
  state.current = name; state.activePath = null;
  hideTutor();
  mainEl.innerHTML = '<div class="empty">Loading…</div>';
  try {
    if (!state.classrooms.length) {
      // Landed here directly (e.g. a bookmarked #/Name hash) without going
      // through the classrooms list first — the sidebar needs the full list
      // to render, not just this one classroom's materials.
      const { classrooms } = await api('/api/classrooms');
      state.classrooms = classrooms;
    }
    const data = await api(`/api/classrooms/${encodeURIComponent(name)}`);
    state.materials = data.materials;
    const prog = classroomProgress(name, data.materials);
    mainEl.innerHTML = `
      <div class="lesson-head"><h2 class="lesson-title" style="font-size:19px">${esc(name)}</h2>
        <span class="progress-pill ${prog.pct === 100 ? 'done' : ''}">${prog.done}/${prog.total} complete</span></div>
      ${data.materials.length ? '' : '<div class="empty">Empty classroom.</div>'}
    `;
    renderSidebar();
  } catch (e) {
    mainEl.innerHTML = `<div class="empty">Failed to load classroom: ${esc(e.message)}</div>`;
  }
}

function openApp(url) {
  // Full-page navigation, not an iframe: Odysseus sets X-Frame-Options: DENY
  // globally (core/middleware.py), which blocks framing even same-origin.
  window.location.href = url;
}

// ---------------------------------------------------------------- lesson note --
async function openNote(classroomName, path, title) {
  state.activePath = path; state.activeTitle = title; state.tutorHistory = [];
  mainEl.innerHTML = '<div class="empty">Loading…</div>';
  renderSidebar();
  try {
    const data = await api(`/api/classrooms/${encodeURIComponent(classroomName)}/note?path=${encodeURIComponent(path)}`);
    state.activeContent = data.content;
    const done = isDone(classroomName, path);
    // Strip Obsidian YAML frontmatter (--- ... ---) — it's metadata for the
    // vault, not lesson content, and reads as noise dumped above the title.
    const bodyOnly = data.content.replace(/^---\n[\s\S]*?\n---\n/, '');
    const html = sanitizeAllowedHtml(mdToHtml(bodyOnly));
    mainEl.innerHTML = `
      <div class="lesson-head">
        <h1 class="lesson-title">${esc(title)}</h1>
        <button class="mark-done-btn ${done ? 'done' : ''}" id="mark-done">${done ? '✓ Completed' : 'Mark complete'}</button>
      </div>
      <div class="lesson-body">${html}</div>
    `;
    document.getElementById('mark-done').addEventListener('click', (e) => {
      const nowDone = !isDone(classroomName, path);
      setDone(classroomName, path, nowDone);
      e.target.textContent = nowDone ? '✓ Completed' : 'Mark complete';
      e.target.classList.toggle('done', nowDone);
      renderSidebar();
    });
    showTutor();
  } catch (e) {
    mainEl.innerHTML = `<div class="empty">Failed to load note: ${esc(e.message)}</div>`;
  }
}

// ---------------------------------------------------------------- tutor panel --
function showTutor() {
  tutorEl.style.display = 'flex';
  tutorMsgsEl.innerHTML = '<div class="tutor-empty">Ask about the material on this page — the tutor reads it as context.</div>';
}
function hideTutor() { tutorEl.style.display = 'none'; }

function appendTutorMsg(role, html) {
  if (tutorMsgsEl.querySelector('.tutor-empty')) tutorMsgsEl.innerHTML = '';
  const div = document.createElement('div');
  div.className = `tutor-msg ${role}`;
  div.innerHTML = html;
  tutorMsgsEl.appendChild(div);
  tutorMsgsEl.scrollTop = tutorMsgsEl.scrollHeight;
  return div;
}

async function sendTutorQuestion() {
  const question = tutorInputEl.value.trim();
  if (!question || !state.activePath) return;
  tutorInputEl.value = '';
  tutorSendEl.disabled = true;
  appendTutorMsg('user', esc(question));
  state.tutorHistory.push({ role: 'user', content: question });
  const answerEl = appendTutorMsg('assistant', '<span style="color:#75757e">Thinking…</span>');

  let full = '';
  try {
    const res = await fetch('/api/classrooms/tutor', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lesson_title: state.activeTitle || '',
        lesson_content: state.activeContent || '',
        question,
        history: state.tutorHistory.slice(0, -1),
      }),
    });
    if (!res.ok || !res.body) throw new Error(`${res.status} ${await res.text().catch(() => '')}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let first = true;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        if (line === 'data: [DONE]') continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.delta && !data.thinking) {
            if (first) { answerEl.innerHTML = ''; first = false; }
            full += data.delta;
            answerEl.innerHTML = sanitizeAllowedHtml(mdToHtml(full));
            tutorMsgsEl.scrollTop = tutorMsgsEl.scrollHeight;
          }
        } catch (e) { /* ignore partial/non-JSON chunks */ }
      }
    }
    state.tutorHistory.push({ role: 'assistant', content: full || '(no response)' });
  } catch (e) {
    answerEl.innerHTML = `<span style="color:#e05c5c">Tutor error: ${esc(e.message)}</span>`;
  } finally {
    tutorSendEl.disabled = false;
  }
}

tutorSendEl.addEventListener('click', sendTutorQuestion);
tutorInputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTutorQuestion(); }
});
tutorInputEl.addEventListener('input', () => {
  tutorInputEl.style.height = 'auto';
  tutorInputEl.style.height = Math.min(120, tutorInputEl.scrollHeight) + 'px';
});

// ---------------------------------------------------------------- boot --
const initial = decodeURIComponent(location.hash.replace('#/', ''));
if (initial) showClassroom(initial); else showClassrooms();
