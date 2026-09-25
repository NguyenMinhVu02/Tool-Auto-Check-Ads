const zone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const adsInput = document.getElementById('ads-input');
const workingInput = document.getElementById('working-input');
const adsName = document.getElementById('ads-name');
const workingName = document.getElementById('working-name');
const documentsStatus = document.getElementById('documents-status');
const startButton = document.getElementById('start-button');
const state = document.getElementById('upload-state');
const progressTrack = document.getElementById('progress-track');
const progressBar = document.getElementById('progress-bar');
const phase = document.getElementById('phase-chip');
const subtitle = document.getElementById('result-subtitle');
const findings = document.getElementById('finding-list');
const reportLink = document.getElementById('report-link');
let selectedApk = null;
let busy = false;
const jobStorageKey = 'apk-audit-active-job';
const stageOrder = ['upload', 'unpack', 'facts', 'rules', 'report'];
const stageLabels = {
  upload: 'Đang tiếp nhận file',
  unpack: 'Đang giải mã APK',
  facts: 'Đang trích xuất dữ liệu',
  rules: 'Đang đối chiếu quy tắc',
  report: 'Đang ghi báo cáo',
};

function setStage(stage) {
  const current = stageOrder.indexOf(stage);
  for (const step of document.querySelectorAll('.step[data-stage]')) {
    const index = stageOrder.indexOf(step.dataset.stage);
    step.classList.toggle('is-active', index === current);
    step.classList.toggle('is-complete', stage === 'done' || (current >= 0 && index < current));
    if (index === current) step.setAttribute('aria-current', 'step');
    else step.removeAttribute('aria-current');
  }
}

function message(value, error = false) {
  state.textContent = value;
  state.classList.toggle('error', error);
}
function setBusy(value) {
  busy = value;
  startButton.disabled = value || !selectedApk;
}
function updateDocuments() {
  const ads = adsInput.files[0];
  const working = workingInput.files[0];
  adsName.textContent = ads ? ads.name : 'Chưa chọn file';
  workingName.textContent = working ? working.name : 'Chưa chọn file';
  if (ads && working) {
    documentsStatus.textContent = 'Đã chọn đủ hai file. Cả hai sẽ được đưa vào pipeline khi bấm kiểm tra.';
  } else if (ads || working) {
    documentsStatus.textContent = 'Mới có một file. Lượt kiểm tra sẽ bỏ qua cả hai tài liệu.';
  } else {
    documentsStatus.textContent = 'Chưa chọn tài liệu. Có thể kiểm tra APK mà không kèm tài liệu.';
  }
}
function selectApk(file) {
  if (busy) return;
  if (!/\.(apk|xapk|apkm)$/i.test(file.name)) {
    message('Chỉ nhận APK, XAPK hoặc APKM.', true);
    return;
  }
  selectedApk = file;
  message(`Đã chọn ${file.name}. Bấm “Bắt đầu kiểm tra” khi bạn sẵn sàng.`);
  startButton.disabled = false;
  phase.textContent = 'Sẵn sàng';
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
    if (response.status === 404) sessionStorage.removeItem(jobStorageKey);
    if (!response.ok) throw new Error(job.error || 'Không đọc được trạng thái');
    if (job.state === 'running' || job.state === 'uploading') {
      const stage = stageLabels[job.stage] ? job.stage : 'unpack';
      setStage(stage);
      phase.textContent = stageLabels[stage];
      subtitle.textContent = job.filename;
      message(`${job.filename}: ${stageLabels[stage].toLowerCase()}…`);
      setTimeout(() => poll(id), 1200);
      return;
    }
    progressTrack.hidden = true;
    if (job.state === 'error') {
      sessionStorage.removeItem(jobStorageKey);
      setBusy(false);
      phase.textContent = 'Có lỗi';
      subtitle.textContent = job.filename;
      message(job.error || 'Không phân tích được file.', true);
      return;
    }
    setStage('done');
    phase.textContent = 'Đã tạo báo cáo';
    message(`Hoàn tất: ${job.filename}`);
    subtitle.textContent = `${job.filename}${job.package ? ` · ${job.package}` : ''} · ${job.docs_used ? 'Đã nhận 2 tài liệu' : 'Không kèm tài liệu'}`;
    for (const key of ['pass', 'fail', 'unknown', 'skipped']) metric(key, job.summary[key]);
    const reportResponse = await fetch(`/api/jobs/${id}/report`);
    if (!reportResponse.ok) throw new Error('Không đọc được báo cáo');
    showFindings(await reportResponse.json());
    reportLink.href = `/api/jobs/${id}/report`;
    reportLink.hidden = false;
    sessionStorage.removeItem(jobStorageKey);
    setBusy(false);
    document.getElementById('results').scrollIntoView({behavior: 'smooth'});
  } catch (error) {
    if (sessionStorage.getItem(jobStorageKey) === id) {
      phase.textContent = 'Mất kết nối với server';
      message(`${error.message}. Đang thử kết nối lại…`, true);
      setTimeout(() => poll(id), 3000);
    } else {
      setBusy(false);
      phase.textContent = 'Có lỗi';
      message(error.message, true);
    }
  }
}
async function uploadDocument(kind, file) {
  if (!/\.(csv|json)$/i.test(file.name)) throw new Error('Tài liệu cần là CSV hoặc JSON.');
  const response = await fetch('/api/documents', {
    method: 'POST',
    headers: {'Content-Type': 'application/octet-stream', 'X-Document-Kind': kind, 'X-Filename': encodeURIComponent(file.name)},
    body: file,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Không tải được tài liệu.');
  return data.id;
}
function uploadArchive(file, documentIds) {
  setStage('upload');
  phase.textContent = 'Đang tải file';
  message(`Đang tải ${file.name}…`);
  progressTrack.hidden = false;
  progressBar.style.width = '0%';
  const request = new XMLHttpRequest();
  request.open('POST', '/api/jobs');
  request.setRequestHeader('Content-Type', 'application/octet-stream');
  request.setRequestHeader('X-Filename', encodeURIComponent(file.name));
  if (documentIds) {
    request.setRequestHeader('X-Ads-Scripts-Id', documentIds.ads_scripts);
    request.setRequestHeader('X-Checklist-Id', documentIds.checklist);
  }
  request.upload.onprogress = (event) => {
    if (event.lengthComputable) progressBar.style.width = `${Math.round(100 * event.loaded / event.total)}%`;
  };
  request.onload = () => {
    let data;
    try { data = JSON.parse(request.responseText); } catch { data = {}; }
    if (request.status !== 202) {
      setBusy(false);
      progressTrack.hidden = true;
      phase.textContent = 'Có lỗi';
      message(data.error || 'Upload thất bại.', true);
      return;
    }
    progressBar.style.width = '100%';
    sessionStorage.setItem(jobStorageKey, data.id);
    poll(data.id);
  };
  request.onerror = () => {
    setBusy(false);
    progressTrack.hidden = true;
    phase.textContent = 'Có lỗi';
    message('Không kết nối được localhost.', true);
  };
  request.send(file);
}
async function beginAudit() {
  if (busy || !selectedApk) return;
  setBusy(true);
  reportLink.hidden = true;
  subtitle.textContent = selectedApk.name;
  try {
    let documentIds = null;
    const ads = adsInput.files[0];
    const working = workingInput.files[0];
    if (ads && working) {
      setStage('upload');
      phase.textContent = 'Đang tải tài liệu';
      message('Đang tải ADS SCRIPTS và working file…');
      documentIds = {
        ads_scripts: await uploadDocument('ads_scripts', ads),
        checklist: await uploadDocument('checklist', working),
      };
    }
    uploadArchive(selectedApk, documentIds);
  } catch (error) {
    setBusy(false);
    phase.textContent = 'Có lỗi';
    message(error.message, true);
  }
}
zone.addEventListener('click', () => fileInput.click());
zone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); fileInput.click(); } });
fileInput.addEventListener('change', () => { if (fileInput.files[0]) selectApk(fileInput.files[0]); fileInput.value = ''; });
adsInput.addEventListener('change', updateDocuments);
workingInput.addEventListener('change', updateDocuments);
startButton.addEventListener('click', beginAudit);
window.addEventListener('beforeunload', (event) => {
  if (!busy) return;
  event.preventDefault();
  event.returnValue = '';
});
const activeJob = sessionStorage.getItem(jobStorageKey);
if (activeJob) {
  setBusy(true);
  phase.textContent = 'Đang khôi phục tiến độ';
  message('Đang kết nối lại với lượt kiểm tra…');
  poll(activeJob);
}
for (const name of ['dragenter', 'dragover']) zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add('dragging'); });
for (const name of ['dragleave', 'drop']) zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.remove('dragging'); });
zone.addEventListener('drop', (event) => { if (event.dataTransfer.files[0]) selectApk(event.dataTransfer.files[0]); });
