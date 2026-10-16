import React, { useCallback, useEffect, useRef, useState } from 'react';
import { findingText } from './findingText';
import {
  Alert, Button, Card, Collapse, Empty, Layout, List, Progress, Space,
  Select, Statistic, Steps, Tag, Typography, Upload,
} from 'antd';
import {
  AppstoreOutlined, CheckCircleOutlined, CloudUploadOutlined,
  DownloadOutlined, FileSearchOutlined, FileTextOutlined, FolderOpenOutlined,
  InfoCircleOutlined, LoadingOutlined, SafetyCertificateOutlined,
} from '@ant-design/icons';

const { Sider, Content } = Layout;
const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;
const jobStorageKey = 'apk-audit-active-job';
const stageOrder = ['upload', 'documents', 'unpack', 'facts', 'rules', 'report'];
const stageLabels = {
  upload: 'Tiếp nhận ứng dụng',
  documents: 'Đọc tài liệu đối chiếu',
  unpack: 'Giải mã APK',
  facts: 'Trích xuất dữ liệu',
  rules: 'Đối chiếu quy tắc',
  report: 'Tạo báo cáo',
};
const steps = [
  { title: 'Tiếp nhận', description: 'APK / XAPK / APKM' },
  { title: 'Tài liệu', description: 'ADS SCRIPTS & working file' },
  { title: 'Giải mã', description: 'jadx workspace' },
  { title: 'Trích xuất', description: 'Manifest & facts' },
  { title: 'Đối chiếu', description: 'Các rule ads' },
  { title: 'Báo cáo', description: 'JSON & Markdown' },
];
const statusLabels = { PASS: 'Đạt', FAIL: 'Cần xử lý', UNKNOWN: 'Chưa rõ', SKIPPED: 'Bỏ qua' };
const statusColors = { PASS: 'success', FAIL: 'error', UNKNOWN: 'warning', SKIPPED: 'default' };

async function readJson(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Không đọc được dữ liệu từ server.');
  return data;
}

async function uploadDocument(kind, file) {
  const response = await fetch('/api/documents', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/octet-stream',
      'X-Document-Kind': kind,
      'X-Filename': encodeURIComponent(file.name),
    },
    body: file,
  });
  return (await readJson(response)).id;
}

function uploadArchive(file, documentIds, engine, onProgress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('POST', '/api/jobs');
    request.setRequestHeader('Content-Type', 'application/octet-stream');
    request.setRequestHeader('X-Filename', encodeURIComponent(file.name));
    request.setRequestHeader('X-Audit-Engine', engine);
    if (documentIds) {
      request.setRequestHeader('X-Ads-Scripts-Id', documentIds.ads_scripts);
      request.setRequestHeader('X-Checklist-Id', documentIds.checklist);
    }
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round(100 * event.loaded / event.total));
    };
    request.onload = () => {
      let data;
      try { data = JSON.parse(request.responseText); } catch { data = {}; }
      if (request.status === 202) resolve(data.id);
      else reject(new Error(data.error || 'Tải ứng dụng thất bại.'));
    };
    request.onerror = () => reject(new Error('Không kết nối được localhost.'));
    request.send(file);
  });
}

function Metric({ title, value, color, help }) {
  return <Card className={`metric-card metric-${color}`}><Statistic title={title} value={value ?? '—'} /><Text type="secondary">{help}</Text></Card>;
}

function inlineAnalysis(text) {
  return text.split(/(`[^`]+`)/g).map((part, index) => part.startsWith('`') && part.endsWith('`')
    ? <Text code key={index}>{part.slice(1, -1)}</Text> : part);
}

function Finding({ item }) {
  const evidence = (item.evidence || []).filter((entry) => entry.verified);
  const analysis = findingText(item.reasoning || item.reason || 'Chưa có mô tả.');
  const renderLine = (line, index) => {
    const clean = line.replace(/^#{1,3}\s*/, '').replace(/\*\*/g, '').replace(/^[-•]\s*/, '');
    const heading = clean.match(/^(Kết luận|Cần sửa|Đã đúng|Chưa xác minh)\s*:\s*(.*)$/i);
    return heading ? <div className="finding-section" key={index}><Text strong>{heading[1]}</Text>{heading[2] && <Paragraph>{inlineAnalysis(heading[2])}</Paragraph>}</div>
      : <li key={index}>{inlineAnalysis(clean)}</li>;
  };
  return (
    <List.Item className="finding-item">
      <div className="finding-main">
        <div className="finding-heading">
          <Text strong>{item.title}</Text>
          <Tag color={statusColors[item.status]}>{statusLabels[item.status] || item.status}</Tag>
        </div>
        <Text type="secondary" className="finding-meta">{item.area} · {item.rule_id}</Text>
        {analysis.structured ? <div className="finding-reason">{analysis.lines.map((line, index) => {
          const rendered = renderLine(line, index);
          return rendered.type === 'li' ? <ul className="finding-points" key={index}>{rendered}</ul> : rendered;
        })}</div> : <div className="finding-reason">
          <Paragraph className="finding-summary">{inlineAnalysis(analysis.summary)}</Paragraph>
          <Collapse ghost items={[{ key: 'analysis', label: 'Đọc toàn bộ phân tích', children: <ul className="finding-points">{analysis.lines.map(renderLine)}</ul> }]} />
        </div>}
        {evidence.length > 0 && <Collapse ghost size="small" items={[{
          key: 'evidence',
          label: `${evidence.length} bằng chứng đã xác minh`,
          children: evidence.map((entry, index) => <div className="evidence" key={`${entry.file}-${entry.line}-${index}`}>
            <Text code>{entry.file}:{entry.line}</Text><Text>{entry.excerpt}</Text>
          </div>),
        }]} />}
      </div>
    </List.Item>
  );
}

export default function App() {
  const [apk, setApk] = useState(null);
  const [ads, setAds] = useState(null);
  const [working, setWorking] = useState(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(null);
  const [uploadPercent, setUploadPercent] = useState(null);
  const [notice, setNotice] = useState('Chưa chọn ứng dụng.');
  const [error, setError] = useState(false);
  const [job, setJob] = useState(null);
  const [report, setReport] = useState(null);
  const [engines, setEngines] = useState([]);
  const [selectedEngine, setSelectedEngine] = useState(null);
  const [enginesLoading, setEnginesLoading] = useState(true);
  const [engineError, setEngineError] = useState('');
  const busyRef = useRef(false);
  const timerRef = useRef(null);

  const refreshEngines = useCallback(async () => {
    setEnginesLoading(true);
    setEngineError('');
    try {
      const data = await readJson(await fetch('/api/engines'));
      setEngines(data.engines);
      setSelectedEngine((previous) => data.engines.some((item) => item.id === previous && item.installed) ? previous : data.default);
    } catch (cause) {
      setEngineError(cause.message);
      setEngines([]);
      setSelectedEngine(null);
    } finally {
      setEnginesLoading(false);
    }
  }, []);

  useEffect(() => { refreshEngines(); }, [refreshEngines]);

  const changeBusy = useCallback((value) => {
    busyRef.current = value;
    setBusy(value);
  }, []);

  const poll = useCallback(async (id) => {
    try {
      const response = await fetch(`/api/jobs/${id}`);
      if (response.status === 404) sessionStorage.removeItem(jobStorageKey);
      const next = await readJson(response);
      setJob(next);
      setStage(stageLabels[next.stage] ? next.stage : 'upload');
      if (next.state === 'running' || next.state === 'uploading') {
        const ruleText = next.stage === 'rules' && next.current_rule
          ? ` · ${next.rule_completed || 0}/${next.rule_total || '?'}: ${next.current_rule_title || next.current_rule}`
          : '';
        setNotice(`${next.filename}: ${stageLabels[next.stage] || 'Đang xử lý'}${ruleText}…`);
        setError(false);
        timerRef.current = setTimeout(() => poll(id), 1200);
        return;
      }
      setUploadPercent(null);
      if (next.state === 'error') {
        sessionStorage.removeItem(jobStorageKey);
        changeBusy(false);
        setError(true);
        setNotice(next.error || 'Không phân tích được file.');
        return;
      }
      const reportResponse = await fetch(`/api/jobs/${id}/report`);
      const result = await readJson(reportResponse);
      setReport(result);
      setStage('done');
      setNotice(`Hoàn tất: ${next.filename}`);
      setError(false);
      sessionStorage.removeItem(jobStorageKey);
      changeBusy(false);
    } catch (cause) {
      if (sessionStorage.getItem(jobStorageKey) === id) {
        setError(true);
        setNotice(`${cause.message} Đang thử kết nối lại…`);
        timerRef.current = setTimeout(() => poll(id), 3000);
      } else {
        changeBusy(false);
        setError(true);
        setNotice(cause.message);
      }
    }
  }, [changeBusy]);

  useEffect(() => {
    const beforeUnload = (event) => {
      if (!busyRef.current) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    const activeId = sessionStorage.getItem(jobStorageKey);
    if (activeId) {
      changeBusy(true);
      setNotice('Đang khôi phục lượt kiểm tra…');
      poll(activeId);
    }
    return () => {
      window.removeEventListener('beforeunload', beforeUnload);
      clearTimeout(timerRef.current);
    };
  }, [changeBusy, poll]);

  function chooseApk(file) {
    if (busyRef.current) return Upload.LIST_IGNORE;
    if (!/\.(apk|xapk|apkm)$/i.test(file.name)) {
      setNotice('Chỉ nhận APK, XAPK hoặc APKM.');
      setError(true);
      return Upload.LIST_IGNORE;
    }
    setApk(file);
    setNotice(`Đã chọn ${file.name}. Bấm “Bắt đầu kiểm tra” để chạy audit.`);
    setError(false);
    return Upload.LIST_IGNORE;
  }

  function chooseDocument(file, kind) {
    if (!/\.(csv|json)$/i.test(file.name)) {
      setNotice('Tài liệu cần là CSV hoặc JSON.');
      setError(true);
      return Upload.LIST_IGNORE;
    }
    if (kind === 'ads') setAds(file);
    else setWorking(file);
    return Upload.LIST_IGNORE;
  }

  async function beginAudit() {
    if (busyRef.current || !apk || enginesLoading || !engines.some((item) => item.id === selectedEngine && item.installed)) return;
    changeBusy(true);
    setReport(null);
    setJob(null);
    setError(false);
    setStage('upload');
    try {
      let documentIds = null;
      if (ads && working) {
        setNotice('Đang tải ADS SCRIPTS và working file…');
        documentIds = {
          ads_scripts: await uploadDocument('ads_scripts', ads),
          checklist: await uploadDocument('checklist', working),
        };
      }
      setNotice(`Đang tải ${apk.name}…`);
      setUploadPercent(0);
      const id = await uploadArchive(apk, documentIds, selectedEngine, setUploadPercent);
      sessionStorage.setItem(jobStorageKey, id);
      poll(id);
    } catch (cause) {
      setUploadPercent(null);
      changeBusy(false);
      setError(true);
      setNotice(cause.message);
    }
  }

  const documentHint = ads && working
    ? 'Đã chọn đủ hai file. Cả hai sẽ được đưa vào lượt kiểm tra.'
    : ads || working
      ? 'Mới có một file. Lượt kiểm tra sẽ bỏ qua cả hai tài liệu.'
      : 'Không bắt buộc. Có thể kiểm tra APK mà không kèm tài liệu.';
  const currentStep = stage === 'done' ? steps.length : Math.max(0, stageOrder.indexOf(stage));
  const phase = job?.state === 'error' ? 'Có lỗi' : stage === 'done' ? 'Đã tạo báo cáo' : busy ? stageLabels[stage] || 'Đang xử lý' : 'Sẵn sàng';
  const ruleTotal = report?.summary?.total ?? job?.rule_total;
  const displayedEngine = report?.engine || job?.engine || selectedEngine;
  const engineLabel = displayedEngine?.startsWith('claude') ? 'Claude CLI' : displayedEngine?.startsWith('codex') ? 'Codex GPT-6 Luna' : 'AI CLI';

  return (
    <Layout className="app-layout">
      <Sider className="sidebar" width={248} breakpoint="lg" collapsedWidth={0} trigger={null}>
        <a href="#overview" className="brand"><span className="brand-icon"><SafetyCertificateOutlined /></span><span>APK Audit<small>LOCAL WORKSPACE</small></span></a>
        <Text className="sidebar-caption">WORKSPACE</Text>
        <nav className="side-nav" aria-label="Điều hướng">
          <a href="#overview"><AppstoreOutlined /> Tổng quan</a>
          <a href="#upload"><CloudUploadOutlined /> Tải ứng dụng</a>
          <a href="#results"><FileSearchOutlined /> Kết quả kiểm tra</a>
        </nav>
        <div className="sidebar-foot"><span className="live-dot" /> Chạy trên máy của bạn<Text>Dữ liệu lưu ở localhost</Text></div>
      </Sider>
      <Content className="main-content" id="overview">
        <header className="page-header">
          <div><Text className="eyebrow">DASHBOARD / TỔNG QUAN</Text><Title level={2}>Kiểm tra tích hợp Ads</Title><Text type="secondary">Kiểm tra logic quảng cáo trong ứng dụng Android bằng Codex hoặc Claude CLI.</Text></div>
          <Tag className="local-tag" color="processing"><span className="live-dot" /> Local mode</Tag>
        </header>

        <Card className="upload-card" id="upload">
          <div className="upload-heading"><div><Text className="eyebrow">BẮT ĐẦU</Text><Title level={3}>Chọn ứng dụng cần kiểm tra</Title><Paragraph type="secondary">Kéo thả APK, XAPK hoặc APKM. Việc chọn file chưa bắt đầu audit.</Paragraph></div><SafetyCertificateOutlined className="upload-art" /></div>
          <Dragger id="apk-drop-zone" accept=".apk,.xapk,.apkm" multiple={false} maxCount={1} disabled={busy} showUploadList={false} beforeUpload={chooseApk}>
            <p className="ant-upload-drag-icon"><CloudUploadOutlined /></p>
            <p className="ant-upload-text">Kéo file vào đây hoặc bấm để chọn</p>
            <p className="ant-upload-hint">Hỗ trợ .apk, .xapk, .apkm</p>
          </Dragger>
          {apk && <div className="selected-file"><FileTextOutlined /><Text strong>{apk.name}</Text><Tag color="blue">Đã chọn</Tag></div>}
          {uploadPercent !== null && <Progress percent={uploadPercent} size="small" />}
          <Alert className="state-alert" type={error ? 'error' : busy ? 'info' : apk ? 'success' : 'info'} showIcon message={notice} role="status" />
        </Card>

        <Card className="documents-card" title="Thông tin đối chiếu" extra={<Tag>Không bắt buộc</Tag>}>
          <Paragraph type="secondary">Chọn đủ ADS SCRIPTS và working file để so sánh ID ads, package và cấu hình. Hỗ trợ CSV dạng bảng của Infinity, CSV key,value hoặc JSON object.</Paragraph>
          <div className="document-grid">
            <div className="document-field"><Text strong>ADS SCRIPTS</Text><Upload id="ads-upload" accept=".csv,.json" showUploadList={false} beforeUpload={(file) => chooseDocument(file, 'ads')}><Button icon={<FolderOpenOutlined />} disabled={busy}>Chọn file</Button></Upload><Text type="secondary" ellipsis>{ads?.name || 'Chưa chọn file'}</Text></div>
            <div className="document-field"><Text strong>Working file</Text><Upload id="working-upload" accept=".csv,.json" showUploadList={false} beforeUpload={(file) => chooseDocument(file, 'working')}><Button icon={<FolderOpenOutlined />} disabled={busy}>Chọn file</Button></Upload><Text type="secondary" ellipsis>{working?.name || 'Chưa chọn file'}</Text></div>
          </div>
          <div className="engine-field">
            <Text strong>AI dùng để audit</Text>
            <Space wrap>
              <Select id="engine-select" aria-label="AI dùng để audit" style={{ width: 290 }} placeholder="Chưa tìm thấy CLI" value={selectedEngine || undefined} loading={enginesLoading} disabled={busy || enginesLoading}
                onChange={setSelectedEngine} options={engines.map((item) => ({ value: item.id, label: `${item.label}${item.installed ? '' : ' — chưa cài'}`, disabled: !item.installed }))} />
              <Button onClick={refreshEngines} loading={enginesLoading} disabled={busy}>Phát hiện lại</Button>
            </Space>
            <Text type="secondary">Phát hiện trên máy chạy server. CLI cần được đăng nhập sẵn; Claude dùng model mặc định của CLI.</Text>
            {engineError && <Alert type="error" showIcon message={engineError} />}
            {!enginesLoading && !engineError && !selectedEngine && <Alert type="warning" showIcon message="Cài và đăng nhập Codex CLI hoặc Claude CLI, sau đó khởi động lại server nếu PATH thay đổi và bấm Phát hiện lại." />}
          </div>
          <div className="start-row"><Text type="secondary">{documentHint}</Text><Button id="start-button" type="primary" size="large" icon={busy ? <LoadingOutlined /> : <FileSearchOutlined />} disabled={!apk || busy || enginesLoading || !selectedEngine} onClick={beginAudit}>{busy ? 'Đang kiểm tra' : 'Bắt đầu kiểm tra'}</Button></div>
        </Card>

        <Card className="steps-card" title="Tiến độ audit" extra={<Tag color={error ? 'error' : busy ? 'processing' : stage === 'done' ? 'success' : 'default'}>{phase}</Tag>}>
          <Steps size="small" responsive current={currentStep} status={error ? 'error' : 'process'} items={steps} />
          {stage === 'rules' && job?.rule_total > 0 && <div className="rule-progress">
            <Text strong>{job.rule_completed || 0}/{job.rule_total} quy tắc đã xong</Text>
            <Progress percent={Math.round(100 * (job.rule_completed || 0) / job.rule_total)} size="small" />
            {job.current_rule && <Text type="secondary">Đang đọc mã: {job.current_rule_title || job.current_rule}</Text>}
            {job.last_rule && <Text type="secondary"> · Vừa xong: {job.last_rule.rule_id} ({statusLabels[job.last_rule.status] || job.last_rule.status}{job.last_rule.from_cache ? ', cache' : ''})</Text>}
          </div>}
        </Card>

        <section className="results-section" id="results">
          <div className="results-header"><div><Text className="eyebrow">KẾT QUẢ</Text><Title level={3}>Tổng quan kiểm tra</Title></div>{report && <Button href={`/api/jobs/${job.id}/report`} icon={<DownloadOutlined />}>Tải report.json</Button>}</div>
          <Alert className="ai-notice" type="info" showIcon icon={<InfoCircleOutlined />} message={ruleTotal ? `${engineLabel} đánh giá ${ruleTotal} rule ads` : `${engineLabel} đọc mã và đánh giá các rule ads`} description="PASS và FAIL cần bằng chứng file/dòng hợp lệ. Khi thiếu dữ liệu hoặc không thể kết nối AI, kết quả là Chưa rõ. Nội dung mã và tài liệu được gửi tới nhà cung cấp AI đã chọn, sử dụng quota của tài khoản CLI." />
          {report?.inventory?.documents_available && <Alert className="inventory-notice" type={report.inventory.missing_local.length || report.inventory.mismatched_ids.length || report.inventory.package_match === false || report.inventory.app_id_match === false ? 'warning' : 'success'} showIcon
            message={`Kiểm kê ID: ${report.inventory.matching_ids.length}/${report.inventory.expected_count} placement khớp config local`}
            description={<Space direction="vertical" size={2}>
              {report.inventory.missing_local.length > 0 && <Text>Thiếu trong config: {report.inventory.missing_local.join(', ')}</Text>}
              {report.inventory.mismatched_ids.length > 0 && <Text>ID lệch: {report.inventory.mismatched_ids.join(', ')}</Text>}
              {report.inventory.extra_local.length > 0 && <Text>Thừa trong config: {report.inventory.extra_local.join(', ')}</Text>}
              {report.inventory.package_match !== null && report.inventory.package_match !== undefined && <Text>Package: {report.inventory.package_match ? 'khớp working file' : 'không khớp working file'}</Text>}
              {report.inventory.app_id_match !== null && report.inventory.app_id_match !== undefined && <Text>AdMob App ID: {report.inventory.app_id_match ? 'khớp ADS SCRIPTS' : 'không khớp ADS SCRIPTS'}</Text>}
              <Text type="secondary">Kiểm kê từ tài liệu và assets; chưa chứng minh ID được dùng khi chạy.</Text>
            </Space>} />}
          <div className="metric-grid"><Metric title="ĐẠT" value={report?.summary?.pass} color="pass" help="Có bằng chứng phù hợp" /><Metric title="CẦN XỬ LÝ" value={report?.summary?.fail} color="fail" help="Có bằng chứng sai lệch" /><Metric title="CHƯA RÕ" value={report?.summary?.unknown} color="unknown" help="Cần thêm dữ liệu" /><Metric title="BỎ QUA" value={report?.summary?.skipped} color="skipped" help="Chưa đủ điều kiện" /></div>
          <Card className="findings-card" title="Chi tiết phân tích" extra={<Tag color={error ? 'error' : stage === 'done' ? 'success' : 'default'}>{phase}</Tag>}>
            {job && <Paragraph type="secondary" className="report-subtitle">{job.filename}{job.package ? ` · ${job.package}` : ''}{job.state === 'done' ? ` · ${job.docs_used ? 'Đã nhận 2 tài liệu' : 'Không kèm tài liệu'}` : ''}</Paragraph>}
            {report ? <List dataSource={report.findings || []} locale={{ emptyText: 'Không có luật nào trong báo cáo.' }} renderItem={(item) => <Finding item={item} />} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chọn APK và bấm Bắt đầu kiểm tra để xem báo cáo." />}
          </Card>
        </section>
        <footer><Space><CheckCircleOutlined /> APK Audit · Local workspace</Space></footer>
      </Content>
    </Layout>
  );
}
