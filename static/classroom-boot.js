// A module load error otherwise leaves the initial Loading message forever.
window.addEventListener('load', () => {
  const timer = setTimeout(() => {
    const main = document.getElementById('main');
    if (main?.textContent.trim() === 'Loading…') {
      main.innerHTML = '<div class="empty" role="alert">Classroom could not start. Reload this page; if it persists, check Chiron logs and browser console. <a href="/static/classroom.html">Reload Classroom</a></div>';
    }
  }, 15000);
  window.addEventListener('classroom-ready', () => clearTimeout(timer), { once: true });
});
