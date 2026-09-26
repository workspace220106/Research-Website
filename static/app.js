const views = ['new', 'history', 'settings', 'detail'];
const labels = { full: 'Complete research', social: 'Public discussion only', research: 'Source research only' };
const stages = ['Collect public discussion', 'Research sources', 'Check and write', 'Prepare paper'];
let runs = [];
let selectedRun = null;
let previousView = 'history';
let pollTimer = null;

const el = id => document.getElementById(id);
const fmtDate = value => new Date(value).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' });
const bytes = value => value < 1024 ? `${value} B` : `${(value / 1024).toFixed(1)} KB`;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const type = response.headers.get('content-type') || '';
  const data = type.includes('json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(data.error || 'The request could not be completed.');
  return data;
}

function show(view) {
  views.forEach(name => el(`${name}-view`).hidden = name !== view);
  document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('active', button.dataset.view === view && view !== 'detail'));
  window.scrollTo({ top: 0, behavior: 'instant' });
  if (view === 'history') loadRuns();
  if (view === 'settings') loadState();
}

function message(id, text, success = false) {
  const box = el(id);
  box.hidden = !text;
  box.textContent = text;
  box.style.color = success ? '#111' : '#8b2929';
}

async function loadState() {
  try {
    const state = await api('/api/state');
    const connectedCount = Object.values(state.keys).filter(Boolean).length;
    const coreReady = state.keys['GOOGLE_API_KEY'] && state.keys['OPENROUTER_API_KEY'] && state.keys['TAVILY_API_KEY'];
    el('setup-dot').classList.toggle('ready', coreReady);
    el('setup-status').textContent = coreReady ? 'Ready to research' : 'Setup needed';
    el('setup-summary').textContent = coreReady ? 'Core services connected (Gemini + OpenRouter + Tavily). Add NVIDIA NIM or Groq for YouTube scripts.' : `${connectedCount} services connected. Add Gemini, OpenRouter, and Tavily keys to start research.`;
    Object.entries(state.keys).forEach(([key, ok]) => {
      const target = el(`key-${key}`);
      target.textContent = ok ? 'Connected' : 'Not connected';
      target.classList.toggle('ok', ok);
    });
    el('run-button').disabled = Boolean(state.active_run);
    el('run-button').innerHTML = state.active_run ? 'Research in progress' : 'Start research <span aria-hidden="true">↗</span>';
    if (state.active_run && !selectedRun) openRun(state.active_run);
  } catch (error) {
    el('setup-status').textContent = 'Cannot reach the local app';
    el('setup-summary').textContent = error.message;
  }
}

function runItem(run, compact = false) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = compact ? 'recent-item' : 'history-row';
  const info = document.createElement('span');
  const title = document.createElement('strong');
  title.textContent = run.topic;
  const detail = document.createElement('small');
  detail.textContent = `${fmtDate(run.created_at)} · ${labels[run.mode] || run.mode}`;
  info.append(title, detail);
  const status = document.createElement('span');
  status.textContent = compact ? '↗' : statusLabel(run.status);
  button.append(info, status);
  button.addEventListener('click', () => openRun(run.id));
  return button;
}

function statusLabel(status) {
  return ({ queued: 'Starting', running: 'In progress', complete: 'Complete', partial: 'Check results', failed: 'Needs attention' })[status] || status;
}

async function loadRuns() {
  try {
    runs = await api('/api/runs');
    const recent = el('recent-list');
    const history = el('history-list');
    recent.replaceChildren();
    history.replaceChildren();
    if (!runs.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'Your research will appear here after your first run.';
      recent.append(empty);
      const panel = document.createElement('div');
      panel.className = 'empty-state';
      panel.innerHTML = '<h2>No research yet</h2><p>Enter a topic to begin your first run.</p>';
      history.append(panel);
      return;
    }
    runs.slice(0, 3).forEach(run => recent.append(runItem(run, true)));
    runs.forEach(run => history.append(runItem(run)));
  } catch (error) {
    el('recent-list').textContent = error.message;
    el('history-list').textContent = error.message;
  }
}

function stageCount(run) {
  const names = new Set(run.files.map(file => file.name));
  if (run.mode === 'social') return names.has('twitter_intel.json') ? 1 : 0;
  if (run.mode === 'research') return names.has('deep_research.json') ? 2 : 0;
  if (names.has('paper.tex') || names.has('refs.bib')) return 4;
  if (names.has('script.md') || names.has('audit.md')) return 3;
  if (names.has('deep_research.json')) return 2;
  if (names.has('twitter_intel.json')) return 1;
  return 0;
}

async function openRun(id) {
  previousView = el('new-view').hidden ? 'history' : 'new';
  selectedRun = id;
  show('detail');
  await refreshRun();
}

async function refreshRun() {
  if (!selectedRun) return;
  try {
    const run = await api(`/api/runs/${selectedRun}`);
    el('detail-title').textContent = run.topic;
    el('detail-date').textContent = fmtDate(run.created_at);
    el('detail-mode').textContent = labels[run.mode] || run.mode;
    const badge = el('detail-status');
    badge.textContent = statusLabel(run.status);
    badge.className = `badge ${run.status}`;
    const progress = el('progress-steps');
    progress.replaceChildren();
    const count = stageCount(run);
    const shownStages = run.mode === 'social' ? [stages[0]] : run.mode === 'research' ? [stages[1]] : stages;
    shownStages.forEach((stage, index) => {
      const row = document.createElement('div');
      row.className = `progress-step ${(run.mode === 'research' ? count >= 2 : count > index) ? 'done' : ''}`;
      const circle = document.createElement('span');
      circle.textContent = (run.mode === 'research' ? count >= 2 : count > index) ? '✓' : String(index + 1);
      const text = document.createElement('strong');
      text.textContent = stage;
      row.append(circle, text);
      progress.append(row);
    });
    el('progress-note').textContent = run.status === 'running' ? 'The files below appear as each stage finishes. This can take several minutes.' : run.status === 'failed' ? 'The run stopped. Open Technical details below to see what happened.' : run.status === 'partial' ? 'Some steps had problems. Review the files and technical details.' : run.status === 'complete' ? 'The research run has finished.' : 'Starting the research run…';
    el('run-log').textContent = run.log || 'No technical details yet.';
    const dlAll = el('download-all-link');
    dlAll.href = `/api/runs/${selectedRun}/download`;
    dlAll.hidden = !run.files.length;
    const fileList = el('file-list');
    fileList.replaceChildren();
    if (!run.files.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'No files yet. They will appear as research progresses.';
      fileList.append(empty);
    }
    run.files.forEach(file => {
      const row = document.createElement('div');
      row.className = 'file-row';
      const button = document.createElement('button');
      button.type = 'button';
      const name = document.createElement('strong');
      name.textContent = file.label;
      const detail = document.createElement('small');
      detail.textContent = `${file.name} · ${bytes(file.bytes)}`;
      button.append(name, detail);
      button.addEventListener('click', () => preview(run.id, file));
      const link = document.createElement('a');
      link.href = `/api/runs/${run.id}/files/${file.name}?download=1`;
      link.textContent = 'Download';
      link.setAttribute('aria-label', `Download ${file.label}`);
      row.append(button, link);
      fileList.append(row);
    });
    clearTimeout(pollTimer);
    if (run.status === 'running' || run.status === 'queued') pollTimer = setTimeout(refreshRun, 2500);
    else { loadState(); loadRuns(); }
  } catch (error) {
    el('progress-note').textContent = error.message;
  }
}

async function preview(id, file) {
  const link = `/api/runs/${id}/files/${file.name}`;
  el('preview-title').textContent = file.label;
  el('preview-subtitle').textContent = file.name;
  el('download-link').href = `${link}?download=1`;
  el('download-link').hidden = false;
  if (file.name.endsWith('.pdf')) {
    el('preview-content').textContent = 'This PDF is ready to download and open in your PDF reader.';
    return;
  }
  el('preview-content').textContent = 'Loading preview…';
  try {
    const text = await api(link);
    el('preview-content').textContent = typeof text === 'string' ? text : JSON.stringify(text, null, 2);
  } catch (error) {
    el('preview-content').textContent = error.message;
  }
}

document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => show(button.dataset.view)));
el('back-button').addEventListener('click', () => { selectedRun = null; clearTimeout(pollTimer); show(previousView); });
el('run-form').addEventListener('submit', async event => {
  event.preventDefault();
  message('form-message', '');
  const topic = el('topic').value.trim();
  const mode = document.querySelector('input[name="mode"]:checked').value;
  el('run-button').disabled = true;
  try {
    const run = await api('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic, mode }) });
    el('topic').value = '';
    await openRun(run.id);
  } catch (error) {
    message('form-message', error.message);
    if (error.message.includes('API keys')) { show('settings'); message('settings-message', error.message); }
  } finally { loadState(); }
});
el('settings-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  try {
    await api('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    event.currentTarget.reset();
    message('settings-message', 'Keys saved on this computer.', true);
    loadState();
  } catch (error) { message('settings-message', error.message); }
});
loadState();
loadRuns();
