const STORAGE_KEY = 'aura.mobile.workspaceUrl';
const HISTORY_KEY = 'aura.mobile.workspaceHistory';
const MAX_HISTORY = 5;

const form = document.getElementById('config-form');
const input = document.getElementById('server-url');
const hint = document.getElementById('config-hint');
const clearButton = document.getElementById('clear-url');
const clearHistoryButton = document.getElementById('clear-history');
const editButton = document.getElementById('edit-url');
const reloadButton = document.getElementById('reload-workspace');
const panel = document.getElementById('workspace-panel');
const frame = document.getElementById('workspace-frame');
const connectedUrl = document.getElementById('connected-url');
const workspaceStatus = document.getElementById('workspace-status');
const workspaceHistory = document.getElementById('workspace-history');
const loadingOverlay = document.getElementById('workspace-loading');

function normalizeWorkspaceUrl(rawValue) {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    throw new Error('Please enter the Aura workspace URL.');
  }

  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  const url = new URL(withProtocol);
  if (url.pathname === '/' || url.pathname === '') {
    url.pathname = '/workspace';
  }
  url.hash = '';
  return url.toString();
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((value) => typeof value === 'string') : [];
  } catch {
    return [];
  }
}

function saveHistory(entries) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, MAX_HISTORY)));
}

function persistUrl(url) {
  localStorage.setItem(STORAGE_KEY, url);
  const nextHistory = [url, ...loadHistory().filter((entry) => entry !== url)];
  saveHistory(nextHistory);
  renderHistory();
}

function clearUrl() {
  localStorage.removeItem(STORAGE_KEY);
}

function showMessage(message, isError = false) {
  hint.textContent = message;
  hint.style.color = isError ? '#c2410c' : '';
}

function setWorkspaceStatus(message) {
  workspaceStatus.textContent = message;
}

function toggleLoading(isVisible) {
  loadingOverlay.classList.toggle('hidden', !isVisible);
}

function renderWorkspace(url) {
  connectedUrl.textContent = url;
  setWorkspaceStatus('Loading workspace');
  toggleLoading(true);
  frame.src = url;
  panel.classList.remove('hidden');
}

function workspaceLabel(url) {
  try {
    const parsed = new URL(url);
    return `${parsed.hostname}${parsed.pathname === '/workspace' ? '' : parsed.pathname}`;
  } catch {
    return url;
  }
}

function removeHistoryEntry(url) {
  const nextHistory = loadHistory().filter((entry) => entry !== url);
  saveHistory(nextHistory);
  if (localStorage.getItem(STORAGE_KEY) === url) {
    clearUrl();
  }
  renderHistory();
}

function useHistoryEntry(url) {
  input.value = url;
  persistUrl(url);
  showMessage('Workspace connected from recent list.');
  renderWorkspace(url);
}

function renderHistory() {
  const entries = loadHistory();
  workspaceHistory.innerHTML = '';

  if (entries.length === 0) {
    workspaceHistory.className = 'history-list empty-state';
    workspaceHistory.textContent = 'No saved servers yet.';
    return;
  }

  workspaceHistory.className = 'history-list';
  entries.forEach((url) => {
    const chip = document.createElement('div');
    chip.className = 'history-chip';

    const chipButton = document.createElement('button');
    chipButton.type = 'button';
    chipButton.className = 'history-chip-label';
    chipButton.textContent = workspaceLabel(url);
    chipButton.addEventListener('click', () => useHistoryEntry(url));

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', () => removeHistoryEntry(url));

    chip.append(chipButton, removeButton);
    workspaceHistory.appendChild(chip);
  });
}

function resetWorkspaceView(message) {
  frame.src = 'about:blank';
  panel.classList.add('hidden');
  toggleLoading(false);
  setWorkspaceStatus('Idle');
  showMessage(message);
}

function bootFromStorage() {
  renderHistory();
  const savedUrl = localStorage.getItem(STORAGE_KEY);
  if (!savedUrl) {
    return;
  }

  input.value = savedUrl;
  renderWorkspace(savedUrl);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  try {
    const normalized = normalizeWorkspaceUrl(input.value);
    persistUrl(normalized);
    showMessage('Workspace connected.');
    renderWorkspace(normalized);
  } catch (error) {
    showMessage(error instanceof Error ? error.message : 'Unable to use this URL.', true);
  }
});

frame.addEventListener('load', () => {
  toggleLoading(false);
  setWorkspaceStatus('Connected');
});

clearButton.addEventListener('click', () => {
  clearUrl();
  input.value = '';
  resetWorkspaceView('Saved workspace URL cleared.');
});

clearHistoryButton.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
  showMessage('Recent server list cleared.');
});

editButton.addEventListener('click', () => {
  input.focus();
  input.select();
});

reloadButton.addEventListener('click', () => {
  if (connectedUrl.textContent) {
    renderWorkspace(connectedUrl.textContent);
  }
});

bootFromStorage();
