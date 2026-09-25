// Keep Classroom usable when the larger shared Markdown module cannot load.
let markdownRenderer = null;
import('/static/js/markdown.js').then(module => { markdownRenderer = module; }).catch(error => {
  console.warn('Classroom Markdown renderer unavailable; showing escaped source text.', error);
});

const sideEl = document.getElementById('side');
const mainEl = document.getElementById('main');
const tutorEl = document.getElementById('tutor');
const tutorMsgsEl = document.getElementById('tutor-msgs');
const tutorInputEl = document.getElementById('tutor-input');
const tutorSendEl = document.getElementById('tutor-send');

const icon = (type) => type === 'section' ? '📁' : type === 'custom_app' ? '🧮' : '📄';

async function api(path, opts) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const res = await fetch(path, { credentials: 'same-origin', ...opts, signal: controller.signal });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    return await res.json();
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Request timed out. Check that Chiron is running, then retry.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function renderMarkdown(source) {
  if (markdownRenderer) return markdownRenderer.sanitizeAllowedHtml(markdownRenderer.mdToHtml(source));
  return `<pre>${esc(source)}</pre>`;
}

// ---------------------------------------------------------------- progress --
const PROGRESS_KEY = 'chiron_classroom_progress_v1';
function loadProgress() {
  try { return JSON.parse(localStorage.getItem(PROGRESS_KEY) || '{}'); } catch (e) { return {}; }
}
function saveProgress(p) { localStorage.setItem(PROGRESS_KEY, JSON.stringify(p)); }
function isDone(classroomName, path) { if (classroomName === 'SAT') return false; return !!(loadProgress()[classroomName] || {})[path]; }
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
      if (c.name !== 'SAT') prog = classroomProgress(c.name, state.materials);
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
        ${c.name === 'SAT' ? '<div class="pct">Course plan and source evidence</div>' : `<div class="bar-track"><div class="bar-fill" style="width:${prog.pct}%"></div></div>
        <div class="pct">${prog.total ? `${prog.done}/${prog.total} complete` : 'No materials yet'}</div>`}
      </div>`;
    }).join('')}</div>`;
    mainEl.querySelectorAll('[data-classroom]').forEach(el => {
      el.addEventListener('click', () => showClassroom(el.dataset.classroom));
    });
    renderSidebar();
  } catch (e) {
    mainEl.innerHTML = `<div class="empty">Failed to load classrooms: ${esc(e.message)}</div>`;
    const retry = document.createElement('button');
    retry.className = 'mark-done-btn';
    retry.textContent = 'Retry';
    retry.addEventListener('click', showClassrooms);
    mainEl.appendChild(retry);
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
        ${name === 'SAT' ? '<span class="progress-pill">Source-linked plan</span>' : `<span class="progress-pill ${prog.pct === 100 ? 'done' : ''}">${prog.done}/${prog.total} complete</span>`}</div>
      ${data.materials.length ? '' : '<div class="empty">Empty classroom.</div>'}
    `;
    renderSidebar();
    if (name === 'SAT') await renderSatPlan();
  } catch (e) {
    mainEl.innerHTML = `<div class="empty">Failed to load classroom: ${esc(e.message)}</div>`;
    const retry = document.createElement('button');
    retry.className = 'mark-done-btn';
    retry.textContent = 'Retry';
    retry.addEventListener('click', () => showClassroom(name));
    mainEl.appendChild(retry);
  }
}

// Read-only interpretation of the existing course Home, within its current route.
async function renderSatPlan() {
  const panel = document.createElement('section');
  panel.className = 'lesson-body';
  panel.setAttribute('aria-label', 'SAT course plan');
  mainEl.appendChild(panel);
  panel.innerHTML = '<p role="status">Reading the course plan…</p>';
  try {
    const plan = await api('/api/classrooms/SAT/plan');
    if (!panel.isConnected || state.current !== 'SAT' || state.activePath) return;
    // Wiki targets are explicit source buttons below, not guessed browser URLs.
    const render = text => renderMarkdown((text || '').replace(
      /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
      (_, target, label) => label || target.split('/').pop()
    ));
    panel.innerHTML = `
      <h2>Next action</h2>
      <p class="pct">From your recorded course plan</p>
      ${plan.action ? render(plan.action) : '<p>No next action is recorded in the course Home.</p>'}
      <details><summary>Why this?</summary>
        ${plan.evidence ? render(plan.evidence) : '<p>No supporting evidence section is recorded. This is an authored plan, not a personalized inference.</p>'}
        <p>${esc(plan.limitations)}</p>
        <p>Source: ${esc(plan.source.path)}<br>Modified: ${esc(plan.source.modified_at)}<br>
        <span title="${esc(plan.source.revision)}">Revision: ${esc(plan.source.revision.slice(0, 12))}</span></p>
      </details>
      <h3>Continue in the existing course</h3>
      <div id="sat-source-links"></div>`;
    const links = panel.querySelector('#sat-source-links');
    for (const source of [{ path: plan.source.path, title: 'Open course Home' }, ...plan.references]) {
      const button = document.createElement('button');
      button.className = 'mark-done-btn';
      button.textContent = source.title;
      button.addEventListener('click', () => openNote('SAT', source.path, source.title));
      links.appendChild(button);
      links.appendChild(document.createTextNode(' '));
    }
    renderSatDesmos(panel);
  } catch (error) {
    if (!panel.isConnected) return;
    panel.innerHTML = `<p role="alert">The course plan could not be read: ${esc(error.message)}</p>
      <p>Your existing course notes remain in the navigation.</p>`;
    const retry = document.createElement('button');
    retry.className = 'mark-done-btn';
    retry.textContent = 'Retry';
    retry.addEventListener('click', () => { panel.remove(); renderSatPlan(); });
    panel.appendChild(retry);
  }
}

// Original examples teach calculator mechanics; no answer is inferred from a PDF.
const SAT_DESMOS = [
  ['Equation and intersection', 'Algebra', '3x+7=22', ['Identify the requested variable and any restrictions.', 'Enter y=3x+7 on one line and y=22 on another.', 'Select the intersection; its x-coordinate is 5.', 'Substitute 5 into the original equation. Report x, not the y-coordinate.']],
  ['Linear system', 'Algebra', '2x+y=11 and x-y=1', ['Enter both equations on separate lines.', 'Select the intersection (4,3).', 'If the prompt asks for x+y, calculate 7; verify in both equations.']],
  ['Number of solutions', 'Algebra', '2x+2y=6 and x+y=3', ['Graph both equations; the lines overlap.', 'Compare coefficients algebraically to prove they are the same line.', 'Report infinitely many solutions; an overlap may hide one line.']],
  ['Quadratic roots', 'Advanced Math', 'x²-5x+6=0', ['Enter y=x^2-5x+6.', 'Select both x-intercepts: 2 and 3.', 'Check whether the question restricts the domain; substitute candidates.']],
  ['Vertex and extrema', 'Advanced Math', 'y=-2(x-3)²+18', ['Enter y=-2(x-3)^2+18.', 'Select the peak (3,18).', 'For the maximum value report 18; for the input where it occurs report 3. Check domain endpoints.']],
  ['Function input', 'Advanced Math', 'f(x)=x²-4x+7; f(3)', ['Enter f(x)=x^2-4x+7.', 'On a second line enter f(3); read 4.', 'For f(2x), type parentheses around the full input.']],
  ['Regression from a table', 'Problem Solving and Data Analysis', '(0,1), (1,4), (2,9)', ['Add a table with x_1 and y_1 columns and enter the three pairs.', 'Type y_1~a*x_1^2+b*x_1+c on a new line.', 'Read a=1, b=2, c=1; check each original pair.', 'This exact fit does not establish a quadratic model for other data.']],
  ['Statistics from a list', 'Problem Solving and Data Analysis', '2, 4, 4, 6', ['Enter L=[2,4,4,6].', 'Enter mean(L) and median(L); both return 4.', 'Use stdev(L) for sample or stdevp(L) for population only if asked.']],
  ['Circle equation', 'Geometry and Trigonometry', '(x-2)²+(y+1)²=25', ['Enter (x-2)^2+(y+1)^2=25.', 'Identify center (2,-1) and radius 5; square root the right side.', 'Use the graph to check shape, then rely on the equation for exact values.']],
  ['Right triangle trig', 'Geometry and Trigonometry', 'opposite=3, adjacent=4', ['Sketch and label the right triangle first.', 'Use tan(theta)=3/4 or the Pythagorean theorem for hypotenuse 5.', 'Enter arctan(3/4) only if the angle is requested; check degree mode.', 'A graph does not supply missing geometry assumptions.']]
];

function renderSatDesmos(panel) {
  const section = document.createElement('section');
  section.setAttribute('aria-label', 'Desmos math coach');
  section.innerHTML = '<h2>Desmos math coach</h2><p>Choose a domain and a skill. Each lesson shows exactly what to type, what to click, and what to check. For a specific question, choose the closest skill and ask the tutor with the full prompt and choices.</p><label>Domain <select id="sat-domain"></select></label> <label>Skill <select id="sat-skill"></select></label><div id="sat-desmos-lesson" aria-live="polite"></div><p><a href="https://www.desmos.com/calculator" target="_blank" rel="noopener noreferrer">Open Desmos calculator</a> · In Bluebook, practice using its built-in calculator as well.</p>';
  panel.appendChild(section);
  const domain = section.querySelector('#sat-domain');
  const skill = section.querySelector('#sat-skill');
  const lesson = section.querySelector('#sat-desmos-lesson');
  for (const name of [...new Set(SAT_DESMOS.map(item => item[1]))]) domain.add(new Option(name, name));
  function selectSkill() {
    skill.replaceChildren();
    SAT_DESMOS.forEach((item, index) => { if (item[1] === domain.value) skill.add(new Option(item[0], index)); });
    showLesson();
  }
  function showLesson() {
    const item = SAT_DESMOS[Number(skill.value)];
    if (!item) return;
    lesson.innerHTML = `<h3>${esc(item[0])}</h3><p>Example: ${esc(item[2])}</p><ol>${item[3].map(step => `<li>${esc(step)}</li>`).join('')}</ol><p>First identify the relationship yourself; then compare hand solving with the graph. Desmos approximations require an exact check when the answer calls for one.</p>`;
  }
  domain.addEventListener('change', selectSkill);
  skill.addEventListener('change', showLesson);
  selectSkill();
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
    const html = renderMarkdown(bodyOnly);
    mainEl.innerHTML = `
      <div class="lesson-head">
        <h1 class="lesson-title">${esc(title)}</h1>
        ${classroomName === 'SAT' ? '<button class="mark-done-btn" id="sat-back">Back to SAT plan</button>' : `<button class="mark-done-btn ${done ? 'done' : ''}" id="mark-done">${done ? '✓ Completed' : 'Mark complete'}</button>`}
      </div>
      <div class="lesson-body">${html}</div>
    `;
    document.getElementById('sat-back')?.addEventListener('click', () => showClassroom('SAT'));
    document.getElementById('mark-done')?.addEventListener('click', (e) => {
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
            answerEl.innerHTML = renderMarkdown(full);
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
window.dispatchEvent(new Event('classroom-ready'));
if (initial) showClassroom(initial); else showClassrooms();
