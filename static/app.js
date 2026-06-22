const form           = document.getElementById('loginForm');
const startBtn       = document.getElementById('startBtn');
const statusPanel    = document.getElementById('statusPanel');
const statusTitle    = document.getElementById('statusTitle');
const statusSpinner  = document.getElementById('statusSpinner');
const logEl          = document.getElementById('log');
const downloads      = document.getElementById('downloads');
const downloadMaster = document.getElementById('downloadMaster');
const downloadDaily  = document.getElementById('downloadDaily');

let pollTimer = null;
let lastLogCount = 0;

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  startBtn.disabled = true;
  startBtn.textContent = 'Starting…';
  statusPanel.classList.remove('hidden');
  downloads.classList.add('hidden');
  downloadMaster.classList.remove('hidden');
  downloadDaily.classList.remove('hidden');
  logEl.textContent = '';
  lastLogCount = 0;
  statusSpinner.classList.remove('hidden');
  statusTitle.textContent = 'Running…';

  try {
    const res = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Failed to start');
    }
    poll(data.job_id);
  } catch (err) {
    statusTitle.textContent = 'Error: ' + err.message;
    statusSpinner.classList.add('hidden');
    startBtn.disabled = false;
    startBtn.textContent = 'Start Extraction';
  }
});

function poll(jobId) {
  pollTimer = setInterval(async () => {
    const res = await fetch(`/api/status/${jobId}`);
    if (!res.ok) return;
    const data = await res.json();

    if (data.logs.length > lastLogCount) {
      const newLines = data.logs.slice(lastLogCount).join('\n');
      logEl.textContent += (lastLogCount > 0 ? '\n' : '') + newLines;
      logEl.scrollTop = logEl.scrollHeight;
      lastLogCount = data.logs.length;
    }

    if (data.status === 'done') {
      clearInterval(pollTimer);
      statusSpinner.classList.add('hidden');
      statusTitle.textContent = 'Done!';
      startBtn.disabled = false;
      startBtn.textContent = 'Run Again';
      downloads.classList.remove('hidden');
      if (!data.has_master) downloadMaster.classList.add('hidden');
      if (!data.has_daily) downloadDaily.classList.add('hidden');
    } else if (data.status === 'error') {
      clearInterval(pollTimer);
      statusSpinner.classList.add('hidden');
      statusTitle.textContent = 'Error — see log below';
      startBtn.disabled = false;
      startBtn.textContent = 'Try Again';
    }
  }, 1500);
}
