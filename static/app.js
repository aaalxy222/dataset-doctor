const fileInput = document.getElementById('fileInput');
const dropzone = document.getElementById('dropzone');
const dzTitle = document.getElementById('dzTitle');
const result = document.getElementById('result');
let currentFile = null;

const RING_COLORS = {
  '良好': '#2f9e63',
  '中等': '#2f6feb',
  '较差': '#d98b1f',
  '严重': '#d64b4b',
};

function setFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.csv')) {
    alert('只支持 .csv 文件');
    return;
  }
  currentFile = file;
  dzTitle.textContent = file.name;
  analyze(file);
}

async function analyze(file) {
  const form = new FormData();
  form.append('file', file);
  dropzone.classList.add('loading');

  try {
    const res = await fetch('/api/inspect', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '分析失败');
    render(data);
    result.hidden = false;
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    alert(err.message);
    dzTitle.textContent = '点击选择 CSV 文件';
    currentFile = null;
  } finally {
    dropzone.classList.remove('loading');
  }
}

function render(data) {
  const ring = document.getElementById('scoreRing');
  const scoreValue = document.getElementById('scoreValue');
  scoreValue.textContent = data.score;
  ring.style.setProperty('--p', data.score);
  ring.style.setProperty('--ring-color', RING_COLORS[data.level] || '#2f6feb');

  document.getElementById('scoreLevel').textContent = data.level;
  document.getElementById('statTotal').textContent = data.total;
  document.getElementById('statProblem').textContent = data.problem_rows;
  document.getElementById('statClean').textContent = data.clean_rows;
  document.getElementById('statClasses').textContent = Object.keys(data.label_distribution).length;

  renderIssues(data.issues);
  renderBars(data.label_distribution);
  document.getElementById('imbalanceNote').hidden = !data.imbalanced;
}

function renderIssues(issues) {
  const list = document.getElementById('issueList');
  list.innerHTML = '';
  issues.forEach((issue) => {
    const li = document.createElement('li');
    if (issue.count === 0) li.classList.add('clear');

    const left = document.createElement('span');
    left.className = 'issue-name';
    const dot = document.createElement('span');
    dot.className = 'dot';
    const name = document.createElement('span');
    name.textContent = issue.name;
    left.append(dot, name);

    const right = document.createElement('span');
    right.className = 'issue-count';
    right.textContent = issue.count === 0 ? '无' : `${issue.count} 条`;

    li.append(left, right);

    if (issue.count > 0 && issue.rows.length) {
      const sample = document.createElement('span');
      sample.className = 'issue-rows';
      sample.textContent = `行 ${issue.rows.slice(0, 5).join(', ')}${issue.count > 5 ? ' …' : ''}`;
      li.append(sample);
    }
    list.append(li);
  });
}

function renderBars(dist) {
  const box = document.getElementById('labelBars');
  box.innerHTML = '';
  const entries = Object.entries(dist).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    box.textContent = '没有可统计的标签';
    return;
  }
  const max = entries[0][1];
  const total = entries.reduce((sum, [, n]) => sum + n, 0);

  entries.forEach(([label, count]) => {
    const row = document.createElement('div');
    row.className = 'bar-row';

    const name = document.createElement('span');
    name.className = 'bar-label';
    name.textContent = label;
    name.title = label;

    const track = document.createElement('div');
    track.className = 'bar-track';
    const fill = document.createElement('div');
    fill.className = 'bar-fill' + (count / total < 0.1 ? ' minority' : '');
    fill.style.width = `${Math.max(4, (count / max) * 100)}%`;
    track.append(fill);

    const value = document.createElement('span');
    value.className = 'bar-value';
    value.textContent = `${count} · ${(count / total * 100).toFixed(1)}%`;

    row.append(name, track, value);
    box.append(row);
  });
}

dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  setFile(file);
});

fileInput.addEventListener('change', () => setFile(fileInput.files[0]));

document.getElementById('downloadBtn').addEventListener('click', async () => {
  if (!currentFile) return;
  const form = new FormData();
  form.append('file', currentFile);
  try {
    const res = await fetch('/api/clean', { method: 'POST', body: form });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || '导出失败');
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cleaned.csv';
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById('resetBtn').addEventListener('click', () => {
  currentFile = null;
  fileInput.value = '';
  dzTitle.textContent = '点击选择 CSV 文件';
  result.hidden = true;
});
