const main = document.getElementById('main');
const icon = (type) => type === 'section' ? '📁' : type === 'custom_app' ? '🧮' : '📄';

async function api(path) {
  const res = await fetch(path, { credentials: 'same-origin' });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

function esc(s) { return (s || '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

async function showClassrooms() {
  location.hash = '';
  main.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const { classrooms } = await api('/api/classrooms');
    if (!classrooms.length) {
      main.innerHTML = '<div class="empty">No classrooms found under Courses/ yet.</div>';
      return;
    }
    main.innerHTML = `<div class="grid">${classrooms.map(c =>
      `<div class="card" data-classroom="${esc(c.name)}"><div class="name">${esc(c.name)}</div></div>`
    ).join('')}</div>`;
    main.querySelectorAll('[data-classroom]').forEach(el => {
      el.addEventListener('click', () => showClassroom(el.dataset.classroom));
    });
  } catch (e) {
    main.innerHTML = `<div class="empty">Failed to load classrooms: ${esc(e.message)}</div>`;
  }
}

function renderMaterials(items, classroomName) {
  return `<div class="material-list">${items.map(item => {
    if (item.type === 'section') {
      return `<div class="section-title">${esc(item.name)}</div>${renderMaterials(item.items, classroomName)}`;
    }
    return `<div class="material" data-path="${esc(item.path)}" data-type="${item.type}" data-app="${esc(item.app_url || '')}">
      <span class="icon">${icon(item.type)}</span><span>${esc(item.name)}</span>
    </div>`;
  }).join('')}</div>`;
}

async function showClassroom(name) {
  location.hash = `#/${encodeURIComponent(name)}`;
  main.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const data = await api(`/api/classrooms/${encodeURIComponent(name)}`);
    main.innerHTML = `<div class="crumb"><a data-back>Classrooms</a> / ${esc(name)}</div>` +
      (data.materials.length ? renderMaterials(data.materials, name) : '<div class="empty">Empty classroom.</div>');
    main.querySelector('[data-back]').addEventListener('click', showClassrooms);
    main.querySelectorAll('.material').forEach(el => {
      el.addEventListener('click', () => {
        if (el.dataset.type === 'custom_app') openApp(el.dataset.app);
        else openNote(name, el.dataset.path, el.querySelector('span:last-child').textContent);
      });
    });
  } catch (e) {
    main.innerHTML = `<div class="empty">Failed to load classroom: ${esc(e.message)}</div>`;
  }
}

function openApp(url) {
  // Full-page navigation, not an iframe: Odysseus sets X-Frame-Options: DENY
  // globally (core/middleware.py), which blocks framing even same-origin.
  window.location.href = url;
}

async function openNote(classroomName, path, title) {
  main.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const data = await api(`/api/classrooms/${encodeURIComponent(classroomName)}/note?path=${encodeURIComponent(path)}`);
    main.innerHTML = `<div class="crumb"><a data-back>Classrooms</a> / <a data-classroom-back>${esc(classroomName)}</a> / ${esc(title)}</div>
      <div class="note-content">${esc(data.content)}</div>`;
    main.querySelector('[data-back]').addEventListener('click', showClassrooms);
    main.querySelector('[data-classroom-back]').addEventListener('click', () => showClassroom(classroomName));
  } catch (e) {
    main.innerHTML = `<div class="empty">Failed to load note: ${esc(e.message)}</div>`;
  }
}

const initial = decodeURIComponent(location.hash.replace('#/', ''));
if (initial) showClassroom(initial); else showClassrooms();
