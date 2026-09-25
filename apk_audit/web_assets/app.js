const zone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const state = document.getElementById('upload-state');
const progressTrack = document.getElementById('progress-track');
const progressBar = document.getElementById('progress-bar');
const phase = document.getElementById('phase-chip');
const subtitle = document.getElementById('result-subtitle');
const findings = document.getElementById('finding-list');
const reportLink = document.getElementById('report-link');
let busy = false;

function message(value, error = false) {
  state.textContent = value;
  state.classList.toggle('error', error);
}
function metric(name, value) {
  document.getElementById(`count-${name}`).textContent = value;
}
function showFindings(report) {
  findings.replaceChildren();
  const items = report.findings || [];
  for (const item of items) {
    const row = document.createElement('div');
    row.className = 'finding';
    const copy = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = item.title;
    const info = document.createElement('small');
    info.textContent = `${item.area} · ${item.rule_id} · ${item.reasoning || item.reason || ''}`;
    copy.append(title, info);
    const badge = document.createElement('span');
    badge.className = `finding-status ${item.status}`;
    badge.textContent = {PASS: 'Đạt', FAIL: 'Cần xử lý', UNKNOWN: 'Chưa rõ', SKIPPED: 'Bỏ qua'}[item.status] || item.status;
    row.append(copy, badge);
    findings.append(row);
  }
  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'Không có luật nào trong báo cáo.';
    findings.append(empty);
  }
}
async function poll(id) {
  try {
    const response = await fetch(`/api/jobs/${id}`);
    const job = await response.json();
    if (!response.ok) throw new Error(job.error || 'Không đọc được trạng thái');
    if (job.state === 'running' || job.state === 'uploading') {
      phase.textContent = 'Đang phân tích';
      message(`Đã tải ${job.filename}. Đang giải mã và tạo báo cáo…`);
      setTimeout(() => poll(id), 1200);
      return;
    }
    busy = false;
    progressTrack.hidden = true;
    if (job.state === 'error') {
      phase.textContent = 'Có lỗi';
      subtitle.textContent = job.filename;
      message(job.error || 'Không phân tích được file.', true);
      return;
    }
    phase.textContent = 'Đã tạo báo cáo';
    message(`Hoàn tất: ${job.filename}`);
    subtitle.textContent = `${job.filename}${job.package ? ` · ${job.package}` : ''}`;
    for (const key of ['pass', 'fail', 'unknown', 'skipped']) metric(key, job.summary[key]);
    const reportResponse = await fetch(`/api/jobs/${id}/report`);
    if (!reportResponse.ok) throw new Error('Không đọc được báo cáo');
    showFindings(await reportResponse.json());
    reportLink.href = `/api/jobs/${id}/report`;
    reportLink.hidden = false;
    document.getElementById('results').scrollIntoView({behavior: 'smooth'});
  } catch (error) {
    busy = false;
    phase.textContent = 'Có lỗi';
    message(error.message, true);
  }
}
function upload(file) {
  if (busy) return;
  if (!/\.(apk|xapk|apkm)$/i.test(file.name)) {
    message('Chỉ nhận APK, XAPK hoặc APKM.', true);
    return;
  }
  busy = true;
  phase.textContent = 'Đang tải file';
  subtitle.textContent = file.name;
  reportLink.hidden = true;
  message(`Đang tải ${file.name}…`);
  progressTrack.hidden = false;
  progressBar.style.width = '0%';
  const request = new XMLHttpRequest();
  request.open('POST', '/api/jobs');
  request.setRequestHeader('Content-Type', 'application/octet-stream');
  request.setRequestHeader('X-Filename', encodeURIComponent(file.name));
  request.upload.onprogress = (event) => {
    if (event.lengthComputable) progressBar.style.width = `${Math.round(100 * event.loaded / event.total)}%`;
  };
  request.onload = () => {
    let data;
    try { data = JSON.parse(request.responseText); } catch { data = {}; }
    if (request.status !== 202) {
      busy = false;
      progressTrack.hidden = true;
      phase.textContent = 'Có lỗi';
      message(data.error || 'Upload thất bại.', true);
      return;
    }
    progressBar.style.width = '100%';
    poll(data.id);
  };
  request.onerror = () => {
    busy = false;
    progressTrack.hidden = true;
    phase.textContent = 'Có lỗi';
    message('Không kết nối được localhost.', true);
  };
  request.send(file);
}
zone.addEventListener('click', () => fileInput.click());
zone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); fileInput.click(); } });
fileInput.addEventListener('change', () => { if (fileInput.files[0]) upload(fileInput.files[0]); fileInput.value = ''; });
for (const name of ['dragenter', 'dragover']) zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add('dragging'); });
for (const name of ['dragleave', 'drop']) zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.remove('dragging'); });
zone.addEventListener('drop', (event) => { if (event.dataTransfer.files[0]) upload(event.dataTransfer.files[0]); });
