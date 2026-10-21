import React, { useCallback, useEffect, useRef, useState } from 'react';
import { findingText } from './findingText';
import { unknownExplanation } from './findingExplanation';
import {
  Alert, Button, Card, Collapse, Empty, Layout, List, Progress, Space,
  Checkbox, Select, Statistic, Steps, Table, Tabs, Tag, Typography, Upload, message,
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
const statusLabels = { PASS: 'Đạt', FAIL: 'Cần sửa', UNKNOWN: 'Cần dev xem lại', SKIPPED: 'Không áp dụng' };
const statusColors = { PASS: 'success', FAIL: 'error', UNKNOWN: 'warning', SKIPPED: 'default' };

async function readJson(response) {
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || 'Không đọc được dữ liệu từ server.');
    error.status = response.status;
    throw error;
  }
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
  const data = await readJson(response);
  return { id: data.id, sheets: data.sheets || [] };
}

function uploadArchive(file, documentIds, engine, crossFlow, recheckAll, onProgress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('POST', '/api/jobs');
    request.setRequestHeader('Content-Type', 'application/octet-stream');
    request.setRequestHeader('X-Filename', encodeURIComponent(file.name));
    request.setRequestHeader('X-Audit-Engine', engine);
    if (crossFlow) request.setRequestHeader('X-Cross-Flow', '1');
    if (recheckAll) request.setRequestHeader('X-Recheck-All', '1');
    if (documentIds) {
      request.setRequestHeader('X-Ads-Scripts-Id', documentIds.ads_scripts.id);
      request.setRequestHeader('X-Checklist-Id', documentIds.checklist.id);
      if (documentIds.ads_scripts.sheet) request.setRequestHeader('X-Ads-Scripts-Sheet', encodeURIComponent(documentIds.ads_scripts.sheet));
      if (documentIds.checklist.sheet) request.setRequestHeader('X-Checklist-Sheet', encodeURIComponent(documentIds.checklist.sheet));
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

function Finding({ item, index }) {
  const evidence = (item.evidence || []).filter((entry) => entry.verified);
  const claims = (Array.isArray(item.claims) ? item.claims : []).filter((claim) => claim && typeof claim.statement === 'string');
  const analysis = findingText(item.reasoning || item.reason || 'Chưa có mô tả.');
  const unknown = unknownExplanation(item);
  const renderLine = (line, index) => {
    const clean = line.replace(/^#{1,3}\s*/, '').replace(/\*\*/g, '').replace(/^[-•]\s*/, '');
    const heading = clean.match(/^(Kết luận|Cần sửa|Đã đúng|Chưa xác minh)\s*:\s*(.*)$/i);
    return heading ? <div className="finding-section" key={index}><Text strong>{heading[1]}</Text>{heading[2] && <Paragraph>{inlineAnalysis(heading[2])}</Paragraph>}</div>
      : <li key={index}>{inlineAnalysis(clean)}</li>;
  };
  return (
    <List.Item className="finding-item">
      <Card className={`finding-rule-card rule-${(item.status || 'UNKNOWN').toLowerCase()}`}
        title={<div className="finding-heading">
          <span className="finding-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
          <div className="finding-title">
            <Title level={4}>{item.title}</Title>
            <Text type="secondary" className="finding-meta">{item.area} · {item.rule_id}</Text>
          </div>
        </div>}
        extra={<Tag color={statusColors[item.status]}>{statusLabels[item.status] || item.status}</Tag>}>
      <div className="finding-main">
        {unknown && <Alert type="warning" showIcon message={unknown.title} description={unknown.description} />}
        {item.verification?.level && <Paragraph type="secondary" className="finding-verification">
          {item.verification.level === 'structure_and_evidence'
            ? (item.verification.valid ? 'Cấu trúc nhận định và liên kết dẫn chứng hợp lệ.' : 'Chưa đủ nhận định và liên kết dẫn chứng hợp lệ.')
            : 'Báo cáo cũ: chỉ kiểm tra đoạn trích với mã nguồn.'}
          {item.verification.review === 'accepted' && ' AI đã rà lại kết luận.'}
          {' Chưa phải xác nhận hành vi khi chạy app.'}
        </Paragraph>}
        {analysis.structured ? <div className="finding-reason">{analysis.lines.map((line, index) => {
          const rendered = renderLine(line, index);
          return rendered.type === 'li' ? <ul className="finding-points" key={index}>{rendered}</ul> : rendered;
        })}</div> : <div className="finding-reason">
          <Paragraph className="finding-summary">{inlineAnalysis(analysis.summary)}</Paragraph>
          <Collapse ghost items={[{ key: 'analysis', label: 'Đọc toàn bộ phân tích', children: <ul className="finding-points">{analysis.lines.map(renderLine)}</ul> }]} />
        </div>}
        {evidence.length > 0 && <Collapse ghost size="small" items={[{
          key: 'evidence',
          label: `${evidence.length} đoạn trích khớp file/dòng`,
          children: evidence.map((entry, index) => <div className="evidence" key={`${entry.file}-${entry.line}-${index}`}>
            <Text code>{entry.file}:{entry.line}</Text><Text>{entry.excerpt}</Text>
          </div>),
        }]} />}
        {claims.length > 0 && <Collapse ghost items={[{ key: 'claims', label: `${claims.length} nhận định và điều kiện kiểm tra`,
          children: claims.map((claim, index) => <div className="finding-section" key={claim.id || index}>
            <Text strong>{claim.statement}</Text>
            {Array.isArray(claim.conditions) && claim.conditions.length > 0 && <Paragraph>Điều kiện: {claim.conditions.join('; ')}</Paragraph>}
            {Array.isArray(claim.unresolved) && claim.unresolved.length > 0 && <Paragraph>Chưa đủ căn cứ: {claim.unresolved.join('; ')}</Paragraph>}
            {Array.isArray(claim.limitations) && claim.limitations.length > 0 && <Paragraph type="secondary">Giới hạn: {claim.limitations.join('; ')}</Paragraph>}
          </div>) }]} />}
      </div>
      </Card>
    </List.Item>
  );
}

const phaseLabels = {
  initial: ['Đọc mã', 'processing'],
  repair: ['Sửa bằng chứng', 'warning'],
  investigation: ['Điều tra bổ sung', 'purple'],
  review: ['Review FAIL', 'magenta'],
};

function elapsed(since, now) {
  const seconds = since ? Math.max(0, Math.floor((now - Date.parse(since)) / 1000)) : 0;
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

const fmtTokens = (value) => (value >= 1000 ? `${(value / 1000).toFixed(value >= 100000 ? 0 : 1)}K` : String(value || 0));
const requirementIcons = { ok: '✅', issue: '❌', unknown: '❔', na: '➖' };
const levelTags = { ok: 'success', issue: 'error', check: 'warning', skip: 'default' };

function idProblemText(data) {
  const rows = (data.screens || []).flatMap((screen) => screen.placements.filter((item) => item.problem)
    .map((item) => `${screen.title} — ${item.name} — ${item.status}${item.document_id || item.app_id ? ` (ADS SCRIPTS: ${item.document_id || '—'} | app: ${item.app_id || '—'})` : ''}`));
  return rows.length ? `${rows.length} ID ads đang có vấn đề:\n${rows.join('\n')}` : 'Không thấy ID ads nào sai hoặc thiếu ở các màn đầu.';
}

function MarketingSummary({ data, jobId }) {
  const problems = data.id_problems || [];
  const copyProblems = () => navigator.clipboard.writeText(idProblemText(data))
    .then(() => message.success('Đã copy danh sách ID lỗi'), () => message.error('Không copy được, hãy tải CSV'));
  return (
    <Card className="marketing-card" title="Tóm tắt cho Marketing · 4 màn đầu" style={{ marginBottom: 16 }}
      extra={<Space wrap>
        <Button size="small" onClick={copyProblems}>Copy danh sách ID lỗi</Button>
        <Button size="small" href={`/api/jobs/${jobId}/ids.csv`} icon={<DownloadOutlined />}>Tải CSV</Button>
        <Button size="small" href={`/api/jobs/${jobId}/report.html`} target="_blank" icon={<DownloadOutlined />}>Báo cáo HTML</Button>
      </Space>}>
      <Space direction="vertical" size={10} style={{ width: '100%' }}>
        {!data.documents_available && <Alert type="info" showIcon message="Chưa có ADS SCRIPTS nên chưa đối chiếu được ID ads." />}
        {data.publisher_note && <Alert type="error" showIcon message="ID ads thuộc tài khoản AdMob khác" description={data.publisher_note} />}
        {data.app_id_match === false && <Alert type="error" showIcon message="AdMob App ID trong app không khớp ADS SCRIPTS." />}
        {data.package_match === false && <Alert type="warning" showIcon message="Package của app không khớp working file." />}
        {data.documents_available && (problems.length
          ? <Alert type="error" showIcon message={`${problems.length} ID ads đang có vấn đề`}
              description={<ul className="marketing-problems">{problems.map((item) => <li key={item.name}><Text strong>{item.name}</Text> <Text type="secondary">({item.screen})</Text> — {item.status}</li>)}</ul>} />
          : <Alert type="success" showIcon message="Không thấy ID ads nào sai hoặc thiếu ở các màn đầu." />)}
        {(data.config_checks || []).map((check) => (
          <Alert key={check.rule_id} type={check.level === 'ok' ? 'success' : check.level === 'issue' ? 'error' : 'warning'} showIcon
            message={`${check.title}: ${check.label}`}
            description={<Space direction="vertical" size={6} style={{ width: '100%' }}>
              {check.explanation && <Text>{check.explanation}</Text>}
              {check.issues.length > 0 && <Table size="small" pagination={false} scroll={{ x: 'max-content' }}
                rowKey={(row) => `${row.file}-${row.placement}-${row.field}`} dataSource={check.issues}
                columns={[
                  { title: 'File', dataIndex: 'file' },
                  { title: 'Vị trí', dataIndex: 'placement', render: (value) => <Text code>{value}</Text> },
                  { title: 'Trường', dataIndex: 'field' },
                  { title: 'Cần là', dataIndex: 'expected', render: (value) => String(value) },
                  { title: 'Đang là', dataIndex: 'actual', render: (value) => <Text type="danger">{String(value)}</Text> },
                ]} />}
            </Space>} />
        ))}
        <div className="marketing-grid">
          {data.screens.map((screen) => (
            <div className={`marketing-screen level-${screen.level}`} key={screen.key}>
              <div className="marketing-screen-head"><Text strong>{screen.title}</Text></div>
              <Space size={4} wrap>
                <Tag color={screen.id_issues ? 'error' : 'success'}>{screen.id_issues ? `${screen.id_issues} ID có vấn đề` : 'ID đúng'}</Tag>
                <Tag color={levelTags[screen.flow_level]}>Luồng quảng cáo: {screen.flow_label}</Tag>
              </Space>
              {screen.explanation && <Paragraph className="marketing-explanation">{screen.explanation}</Paragraph>}
              {screen.logic && (screen.logic.load || screen.logic.show) && <div className="screen-logic">
                <Text strong>Logic hiện tại{screen.logic.verified ? '' : ' (chưa xác minh đủ)'}</Text>
                <div><Text type="secondary">Tải quảng cáo: </Text>{screen.logic.load || '—'}</div>
                <div><Text type="secondary">Hiển thị: </Text>{screen.logic.show || '—'}</div>
              </div>}
              {screen.requirements?.length > 0 && <div className="screen-requirements">
                <Text strong>Đã đúng yêu cầu chưa?</Text>
                <ul>{screen.requirements.map((item, index) => <li key={index} className={`req-${item.status}`}>
                  <span className="req-icon">{requirementIcons[item.status] || '❔'}</span> {item.text}{item.note && <Text type="secondary"> — {item.note}</Text>}
                </li>)}</ul>
              </div>}
              {screen.placements.length > 0 && <Table size="small" pagination={false} rowKey="name" scroll={{ x: 'max-content' }} dataSource={screen.placements}
                rowClassName={(row) => (row.problem ? 'marketing-row-problem' : '')}
                columns={[
                  { title: 'Vị trí', dataIndex: 'name', render: (value) => <Text code>{value}</Text> },
                  { title: 'Loại', dataIndex: 'ad_type' },
                  { title: 'Tình trạng', dataIndex: 'status', render: (value, row) => <Text type={row.problem ? 'danger' : undefined}>{row.problem ? '❌ ' : ''}{value}</Text> },
                  { title: 'ID trong ADS SCRIPTS', dataIndex: 'document_id', render: (value) => <Text className="ad-id" copyable={Boolean(value)}>{value || '—'}</Text> },
                  { title: 'ID trong app', dataIndex: 'app_id', render: (value) => <Text className="ad-id" copyable={Boolean(value)}>{value || '—'}</Text> },
                ]} />}
            </div>
          ))}
        </div>
        <Text type="secondary">ID trong app lấy từ {data.id_source}. Chi tiết kỹ thuật cho dev ở các mục bên dưới.</Text>
      </Space>
    </Card>
  );
}

function DevView({ view }) {
  return (
    <div className="dev-view">
      {view.groups.map((group) => (
        <Card key={group.key} size="small" className={`dev-group level-${group.level}`} title={group.title}
          extra={<Space size={4}>
            {group.summary.FAIL > 0 && <Tag color="error">{group.summary.FAIL} cần sửa</Tag>}
            {group.summary.UNKNOWN > 0 && <Tag color="warning">{group.summary.UNKNOWN} cần xem lại</Tag>}
            {group.summary.PASS > 0 && <Tag color="success">{group.summary.PASS} đạt</Tag>}
            {group.summary.SKIPPED > 0 && <Tag>{group.summary.SKIPPED} không áp dụng</Tag>}
          </Space>}>
          {group.rules.map((rule) => (
            <div className={`dev-rule level-${rule.level}`} key={rule.rule_id}>
              <Space size={8} wrap><Tag color={levelTags[rule.level]}>{rule.status_label}</Tag><Text strong>{rule.title || rule.rule_id}</Text>{rule.confidence && <Tag color={rule.confidence === 'cao' ? 'green' : rule.confidence === 'trung bình' ? 'gold' : 'default'}>Độ tin cậy: {rule.confidence}</Tag>}</Space>
              {rule.conclusion && <div>{rule.conclusion}</div>}
              {rule.unknown_reason && rule.status !== 'PASS' && <Text type="secondary">Lý do: {rule.unknown_reason}</Text>}
              {rule.basis && <Text type="secondary" className="rule-basis">Căn cứ: {rule.basis}{rule.limits ? ` (${rule.limits})` : ''}</Text>}
              {rule.fixes && <div><Text strong>Cần sửa: </Text>{rule.fixes}</div>}
              {rule.locations.length > 0 && <div><Text strong>Vị trí code: </Text>{rule.locations.map((loc) => <Text code key={loc} copyable>{loc}</Text>)}</div>}
              {(rule.verified || rule.unverified) && <Collapse ghost size="small" items={[{ key: 'more', label: 'Đã đúng / chưa xác minh',
                children: <Space direction="vertical" size={2}>{rule.verified && <Text>Đã đúng: {rule.verified}</Text>}{rule.unverified && <Text type="secondary">Chưa xác minh: {rule.unverified}</Text>}</Space> }]} />}
            </div>
          ))}
        </Card>
      ))}
    </div>
  );
}

function AgentPanel({ agents, engine }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className="agent-grid">
      {agents.map((agent) => {
        const [label, color] = phaseLabels[agent.phase] || ['Đang khởi động', 'default'];
        const recent = (agent.recent_commands || []).slice(0, -1).reverse();
        return (
          <div className="agent-card" key={agent.rule_id}>
            <div className="agent-head">
              <span className="agent-pulse" />
              <Text strong ellipsis title={agent.title}>{agent.title || agent.rule_id}</Text>
              <Text type="secondary" className="agent-time">{elapsed(agent.started_at, now)}</Text>
            </div>
            <Space size={4} wrap>
              <Tag color={color}>{label}{agent.attempt > 1 ? ` · lượt ${agent.attempt}` : ''}</Tag>
              <Tag>{engine}</Tag>
              {agent.allowance > 0 && <Tag>{agent.tool_calls || 0}/{agent.allowance} lệnh</Tag>}
            </Space>
            {agent.allowance > 0 && <Progress percent={Math.min(100, Math.round(100 * (agent.tool_calls || 0) / agent.allowance))} size="small" showInfo={false} />}
            <code className="agent-command">{agent.command ? `$ ${agent.command}` : 'AI đang suy luận…'}</code>
            {recent.length > 0 && <ul className="agent-history">{recent.map((command, index) => <li key={index}>{command}</li>)}</ul>}
          </div>
        );
      })}
    </div>
  );
}

export default function App() {
  const [apk, setApk] = useState(null);
  const [ads, setAds] = useState(null);
  const [working, setWorking] = useState(null);
  const [crossFlow, setCrossFlow] = useState(false);
  const [recheckAll, setRecheckAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(null);
  const [uploadPercent, setUploadPercent] = useState(null);
  const [notice, setNotice] = useState('Chưa chọn ứng dụng.');
  const [error, setError] = useState(false);
  const [job, setJob] = useState(null);
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState('');
  const [engines, setEngines] = useState([]);
  const [selectedEngine, setSelectedEngine] = useState(null);
  const [enginesLoading, setEnginesLoading] = useState(true);
  const [engineError, setEngineError] = useState('');
  const busyRef = useRef(false);
  const viewedJobRef = useRef(null);
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

  const refreshHistory = useCallback(async () => {
    try {
      const data = await readJson(await fetch('/api/jobs'));
      setHistory(data.jobs || []);
      setHistoryError('');
      return data.jobs || [];
    } catch (cause) {
      setHistoryError(cause.message);
      return [];
    }
  }, []);

  const poll = useCallback(async (id) => {
    try {
      const response = await fetch(`/api/jobs/${id}`);
      if (viewedJobRef.current !== id) return;
      if (response.status === 404) sessionStorage.removeItem(jobStorageKey);
      const next = await readJson(response);
      if (viewedJobRef.current !== id) return;
      setJob(next);
      setStage(stageLabels[next.stage] ? next.stage : 'upload');
      if (next.state === 'running' || next.state === 'uploading') {
        changeBusy(true);
        const activeTitles = (next.current_rules || []).map((item) => item.title || item.rule_id);
        const ruleText = next.stage === 'rules' && (activeTitles.length || next.current_rule)
          ? ` · ${next.rule_completed || 0}/${next.rule_total || '?'}: ${activeTitles.join(', ') || next.current_rule_title || next.current_rule}`
          : '';
        setNotice(`${next.filename}: ${stageLabels[next.stage] || 'Đang xử lý'}${ruleText}…`);
        setError(false);
        timerRef.current = setTimeout(() => poll(id), 1200);
        return;
      }
      setUploadPercent(null);
      changeBusy(false);
      refreshHistory();
      if (next.state === 'error') {
        changeBusy(false);
        setError(true);
        setNotice(next.error || 'Không phân tích được file.');
        return;
      }
      const reportResponse = await fetch(`/api/jobs/${id}/report`);
      const result = await readJson(reportResponse);
      if (viewedJobRef.current !== id) return;
      setReport(result);
      setStage('done');
      setNotice(`Hoàn tất: ${next.filename}`);
      setError(false);
      sessionStorage.setItem(jobStorageKey, id);
      changeBusy(false);
    } catch (cause) {
      if (viewedJobRef.current !== id) return;
      if (cause.status === 404) sessionStorage.removeItem(jobStorageKey);
      if (busyRef.current && cause.status !== 404 && sessionStorage.getItem(jobStorageKey) === id) {
        setError(true);
        setNotice(`${cause.message} Đang thử kết nối lại…`);
        timerRef.current = setTimeout(() => poll(id), 3000);
      } else {
        changeBusy(false);
        setError(true);
        setNotice(cause.message);
      }
    }
  }, [changeBusy, refreshHistory]);

  useEffect(() => {
    const beforeUnload = (event) => {
      if (!busyRef.current) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    const activeId = sessionStorage.getItem(jobStorageKey);
    if (activeId) {
      viewedJobRef.current = activeId;
      changeBusy(true);
      setNotice('Đang khôi phục lượt kiểm tra…');
      poll(activeId);
    }
    refreshHistory().then((items) => {
      const active = items.find((item) => ['running', 'uploading'].includes(item.state));
      if (!activeId && active && !busyRef.current && !viewedJobRef.current) {
        viewedJobRef.current = active.id;
        sessionStorage.setItem(jobStorageKey, active.id);
        changeBusy(true);
        poll(active.id);
      }
    });
    return () => {
      window.removeEventListener('beforeunload', beforeUnload);
      clearTimeout(timerRef.current);
      viewedJobRef.current = null;
    };
  }, [changeBusy, poll, refreshHistory]);

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
    if (!/\.(xlsx|csv|json)$/i.test(file.name)) {
      setNotice('Tài liệu cần là XLSX, CSV hoặc JSON.');
      setError(true);
      return Upload.LIST_IGNORE;
    }
    const setDocument = kind === 'ads' ? setAds : setWorking;
    setDocument({ file, name: file.name, sheets: [], sheet: null, loading: true });
    // Upload right away so a multi-app workbook can offer its sheets before the audit starts.
    uploadDocument(kind === 'ads' ? 'ads_scripts' : 'checklist', file)
      .then(({ id, sheets }) => setDocument((current) => current?.file === file
        ? { ...current, id, sheets, sheet: sheets.length === 1 ? sheets[0] : null, loading: false }
        : current))
      .catch((cause) => {
        setDocument((current) => (current?.file === file ? null : current));
        setNotice(`${file.name}: ${cause.message}`);
        setError(true);
      });
    return Upload.LIST_IGNORE;
  }

  async function documentToken(kind, document, setDocument) {
    // The server consumes a document token per job, so re-upload after a previous attempt used it.
    if (document.id && !document.used) {
      setDocument((current) => (current === document ? { ...current, used: true } : current));
      return { id: document.id, sheet: document.sheets.length > 1 ? document.sheet : null };
    }
    const { id, sheets } = await uploadDocument(kind, document.file);
    setDocument((current) => (current?.file === document.file ? { ...current, id, sheets, used: true } : current));
    return { id, sheet: sheets.length > 1 ? document.sheet : null };
  }

  async function beginAudit() {
    if (busyRef.current || !apk || enginesLoading || ads?.loading || working?.loading || (ads && working && [ads, working].some((item) => item.sheets.length > 1 && !item.sheet)) || !engines.some((item) => item.id === selectedEngine && item.installed)) return;
    changeBusy(true);
    viewedJobRef.current = null;
    clearTimeout(timerRef.current);
    setReport(null);
    setJob(null);
    setError(false);
    setStage('upload');
    try {
      let documentIds = null;
      if (ads && working) {
        setNotice('Đang tải ADS SCRIPTS và working file…');
        documentIds = {
          ads_scripts: await documentToken('ads_scripts', ads, setAds),
          checklist: await documentToken('checklist', working, setWorking),
        };
      }
      setNotice(`Đang tải ${apk.name}…`);
      setUploadPercent(0);
      const id = await uploadArchive(apk, documentIds, selectedEngine, crossFlow, recheckAll, setUploadPercent);
      viewedJobRef.current = id;
      sessionStorage.setItem(jobStorageKey, id);
      poll(id);
    } catch (cause) {
      setUploadPercent(null);
      changeBusy(false);
      setError(true);
      setNotice(cause.message);
    }
  }

  function openJob(item) {
    if (busyRef.current) return;
    clearTimeout(timerRef.current);
    setReport(null);
    setJob(null);
    viewedJobRef.current = item.id;
    sessionStorage.setItem(jobStorageKey, item.id);
    poll(item.id);
  }

  async function resumeJob(item) {
    if (busyRef.current) return;
    clearTimeout(timerRef.current);
    changeBusy(true);
    setReport(null);
    setJob(item);
    viewedJobRef.current = item.id;
    setError(false);
    setNotice('Đang tiếp tục kiểm tra; sử dụng lại kết quả hoàn tất còn cache hợp lệ…');
    try {
      const next = await readJson(await fetch(`/api/jobs/${item.id}/resume`, { method: 'POST' }));
      sessionStorage.setItem(jobStorageKey, next.id);
      poll(next.id);
      refreshHistory();
    } catch (cause) {
      changeBusy(false);
      setError(true);
      setNotice(cause.message);
      refreshHistory();
    }
  }

  const needsSheet = (document) => document && document.sheets.length > 1 && !document.sheet;
  const documentsLoading = Boolean(ads?.loading || working?.loading);
  const sheetMissing = Boolean(ads && working && (needsSheet(ads) || needsSheet(working)));
  const documentHint = documentsLoading
    ? 'Đang đọc tài liệu…'
    : sheetMissing
      ? 'Workbook có nhiều sheet; hãy chọn sheet của app cần kiểm cho từng tài liệu.'
      : ads && working
    ? 'Đã chọn đủ hai file. Cả hai sẽ được đưa vào lượt kiểm tra.'
    : ads || working
      ? 'Mới có một file. Lượt kiểm tra sẽ bỏ qua cả hai tài liệu.'
      : 'Không bắt buộc. Có thể kiểm tra APK mà không kèm tài liệu.';
  const currentStep = stage === 'done' ? steps.length : Math.max(0, stageOrder.indexOf(stage));
  const phase = job?.state === 'error' ? 'Có lỗi' : stage === 'done' ? 'Đã tạo báo cáo' : busy ? stageLabels[stage] || 'Đang xử lý' : 'Sẵn sàng';
  const ruleTotal = report?.summary?.total ?? job?.rule_total;
  const displayedEngine = report?.engine || job?.engine || selectedEngine;
  const reportEngineLabels = {
    'codex:gpt-6-sol:low': 'Codex GPT-6 Sol · low',
    'codex:gpt-6.1-sol:low': 'Codex GPT-6.1 Sol · low (báo cáo cũ)',
    'codex:gpt-6.1-sol:medium': 'Codex GPT-6.1 Sol · medium (báo cáo cũ)',
    'claude:claude-sonnet-5:low': 'Claude Sonnet 5 · low',
    'claude:claude-haiku-5-5:low': 'Claude Haiku 5.5 · low (báo cáo cũ)',
    'claude:claude-sonnet-5-5:low': 'Claude Sonnet 5.5 · low (báo cáo cũ)',
    'claude:claude-sonnet-5-5:medium': 'Claude Sonnet 5.5 · medium (báo cáo cũ)',
    'codex:gpt-6-luna': 'Codex GPT-6 Luna (báo cáo cũ)',
    'claude:default': 'Claude (model mặc định cũ)',
  };
  const engineLabel = reportEngineLabels[displayedEngine] || engines.find((item) => item.id === displayedEngine)?.label || displayedEngine || 'AI CLI';

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
          <Paragraph type="secondary">Chọn đủ ADS SCRIPTS và working file để so sánh ID ads, package và cấu hình. Ưu tiên XLSX để giữ màu nền ô ID và gạch ngang tên/ID; các dấu này được hiểu là không dùng. Google Sheets: tải xuống Microsoft Excel (.xlsx). CSV cần cột Status/Enabled để xác định trạng thái open_resume.</Paragraph>
          <div className="document-grid">
            <div className="document-field"><Text strong>ADS SCRIPTS</Text><Upload id="ads-upload" accept=".xlsx,.csv,.json" showUploadList={false} beforeUpload={(file) => chooseDocument(file, 'ads')}><Button icon={<FolderOpenOutlined />} disabled={busy}>Chọn file</Button></Upload><Text type="secondary" ellipsis>{ads?.name || 'Chưa chọn file'}</Text>{ads?.sheets?.length > 1 && <Select id="ads-sheet" aria-label="Sheet ADS SCRIPTS" style={{ width: '100%' }} placeholder="Chọn sheet của app cần kiểm" value={ads.sheet || undefined} disabled={busy} options={ads.sheets.map((name) => ({ value: name, label: name }))} onChange={(sheet) => setAds((current) => ({ ...current, sheet }))} />}</div>
            <div className="document-field"><Text strong>Working file</Text><Upload id="working-upload" accept=".xlsx,.csv,.json" showUploadList={false} beforeUpload={(file) => chooseDocument(file, 'working')}><Button icon={<FolderOpenOutlined />} disabled={busy}>Chọn file</Button></Upload><Text type="secondary" ellipsis>{working?.name || 'Chưa chọn file'}</Text>{working?.sheets?.length > 1 && <Select id="working-sheet" aria-label="Sheet working file" style={{ width: '100%' }} placeholder="Chọn sheet của app cần kiểm" value={working.sheet || undefined} disabled={busy} options={working.sheets.map((name) => ({ value: name, label: name }))} onChange={(sheet) => setWorking((current) => ({ ...current, sheet }))} />}</div>
          </div>
          <div className="engine-field">
            <Text strong>AI dùng để audit</Text>
            <Space wrap>
              <Select id="engine-select" aria-label="AI dùng để audit" style={{ width: 290 }} placeholder="Chưa tìm thấy CLI" value={selectedEngine || undefined} loading={enginesLoading} disabled={busy || enginesLoading}
                onChange={setSelectedEngine} options={engines.map((item) => ({ value: item.id, label: `${item.label}${item.installed ? '' : ' — chưa cài'}`, disabled: !item.installed }))} />
              <Button onClick={refreshEngines} loading={enginesLoading} disabled={busy}>Phát hiện lại</Button>
            </Space>
            <Text type="secondary">CLI cần được đăng nhập sẵn. Claude cố định Haiku 5.5 / low; Codex dùng GPT-6 Sol / low.</Text>
            {engineError && <Alert type="error" showIcon message={engineError} />}
            {!enginesLoading && !engineError && !selectedEngine && <Alert type="warning" showIcon message="Cài và đăng nhập Codex CLI hoặc Claude CLI, sau đó khởi động lại server nếu PATH thay đổi và bấm Phát hiện lại." />}
          </div>
          <Checkbox className="cross-flow-option" checked={recheckAll} disabled={busy} onChange={(event) => setRecheckAll(event.target.checked)}>Kiểm lại cả rule đã đạt ở bản trước (hiện áp dụng cho Firebase tracking)</Checkbox>
          <Checkbox className="cross-flow-option" checked={crossFlow} disabled={busy} onChange={(event) => setCrossFlow(event.target.checked)}>Rà thêm lỗi chéo giữa các luồng (chậm hơn ~5 phút, tốn thêm token)</Checkbox>
          <div className="start-row"><Text type="secondary">{documentHint}</Text><Button id="start-button" type="primary" size="large" icon={busy ? <LoadingOutlined /> : <FileSearchOutlined />} disabled={!apk || busy || enginesLoading || !selectedEngine || documentsLoading || sheetMissing} onClick={beginAudit}>{busy ? 'Đang kiểm tra' : 'Bắt đầu kiểm tra'}</Button></div>
          <Paragraph type="secondary">Tự nhận dạng cột và dòng tiêu đề. Khi chưa hiểu mẫu, AI đã chọn sẽ hỗ trợ ánh xạ cột (tối đa 90 giây/tài liệu); giá trị vẫn lấy từ file gốc. Hai tài liệu cần thuộc cùng app.</Paragraph>
        </Card>

        <Card className="steps-card" title="Tiến độ audit" extra={<Tag color={error ? 'error' : busy ? 'processing' : stage === 'done' ? 'success' : 'default'}>{phase}</Tag>}>
          <Steps size="small" responsive current={currentStep} status={error ? 'error' : 'process'} items={steps} />
          {stage === 'rules' && job?.rule_total > 0 && <div className="rule-progress">
            <Text strong>{job.rule_completed || 0}/{job.rule_total} quy tắc đã xong</Text>
            <Progress percent={Math.round(100 * (job.rule_completed || 0) / job.rule_total)} size="small" />
            {(job.current_rules?.length > 0 || job.current_rule) && <Text type="secondary">Đang đọc mã: {job.current_rules?.length ? job.current_rules.map((item) => item.title || item.rule_id).join(', ') : job.current_rule_title || job.current_rule}</Text>}
            {job.last_rule && <Text type="secondary"> · Vừa xong: {job.last_rule.rule_id} ({statusLabels[job.last_rule.status] || job.last_rule.status}{job.last_rule.from_cache ? ', cache' : ''})</Text>}
            {job.current_rules?.length > 0 && <>
              <Text strong className="agent-title">Agent đang chạy ({job.current_rules.length})</Text>
              <AgentPanel agents={job.current_rules} engine={job.engine === 'claude' ? 'Claude' : 'Codex'} />
            </>}
          </div>}
        </Card>

        <Card title="Lịch sử kiểm tra" extra={<Button onClick={refreshHistory}>Làm mới</Button>}>
          {historyError && <Alert type="warning" showIcon message={historyError} />}
          <List dataSource={history.slice(0, 10)} locale={{ emptyText: 'Chưa có lượt kiểm tra nào được lưu.' }} renderItem={(item) => <List.Item actions={[
            <Button key="open" disabled={busy} onClick={() => openJob(item)}>{item.state === 'done' ? 'Mở báo cáo' : 'Xem trạng thái'}</Button>,
            ...(item.resumable ? [<Button key="resume" disabled={busy} onClick={() => resumeJob(item)}>Tiếp tục</Button>] : []),
          ]}>
            <List.Item.Meta title={item.filename} description={<Space wrap><Tag color={item.state === 'done' ? 'success' : item.state === 'error' ? 'error' : 'processing'}>{item.interrupted ? 'Bị gián đoạn' : item.state === 'done' ? 'Hoàn tất' : item.state === 'error' ? 'Có lỗi' : 'Đang chạy'}</Tag><Text type="secondary">{item.created_at ? new Date(item.created_at).toLocaleString('vi-VN') : ''}</Text></Space>} />
          </List.Item>} />
          {job?.resumable && <Alert type="info" showIcon message="Lượt kiểm tra bị gián đoạn" description="Bấm Tiếp tục để chạy lại các bước cần thiết và dùng kết quả đã hoàn tất còn cache hợp lệ." action={<Button disabled={busy} onClick={() => resumeJob(job)}>Tiếp tục</Button>} />}
        </Card>

        <section className="results-section" id="results">
          <div className="results-header"><div><Text className="eyebrow">KẾT QUẢ</Text><Title level={3}>Tổng quan kiểm tra</Title></div>{report && <Button href={`/api/jobs/${job.id}/report`} icon={<DownloadOutlined />}>Tải report.json</Button>}</div>
          <Alert className="ai-notice" type="info" showIcon icon={<InfoCircleOutlined />} message={ruleTotal ? `${engineLabel} đánh giá ${ruleTotal} rule ads` : `${engineLabel} đọc mã và đánh giá các rule ads`} description="PASS và FAIL cần bằng chứng file/dòng hợp lệ. Khi thiếu dữ liệu hoặc không thể kết nối AI, kết quả là Chưa đủ căn cứ (UNKNOWN), chưa phải lỗi APK được xác nhận. Nội dung mã và tài liệu được gửi tới nhà cung cấp AI đã chọn, sử dụng quota của tài khoản CLI." />
          {report ? <Tabs className="report-tabs" defaultActiveKey="marketing" items={[
            { key: 'marketing', label: 'Marketing', children: report.marketing ? <MarketingSummary data={report.marketing} jobId={job.id} /> : <Empty description="Báo cáo này chưa có tóm tắt Marketing" /> },
            { key: 'dev', label: 'Dev', children: <>
              {report.code_profile && (report.code_profile.obfuscation !== 'thấp' || report.code_profile.decompile_gap_files > 0) && <Alert type="warning" showIcon style={{ marginBottom: 12 }}
                message={`Mã đã giải mã bị làm rối mức ${report.code_profile.obfuscation} (${Math.round(100 * report.code_profile.short_name_ratio)}% tên lớp ≤2 ký tự)${report.code_profile.decompile_gap_files ? `, ${report.code_profile.decompile_gap_files} file của app giải mã lỗi` : ''}`}
                description="Tên hàm/lớp có thể bị đổi nên 'không tìm thấy' không đồng nghĩa app thiếu. Tool chỉ báo Cần sửa khi có bằng chứng rõ (chuỗi ký tự, manifest, file cấu hình, hành vi đọc được); phần còn lại ghi Cần dev xem lại." />}
              {report.dev_view && <DevView view={report.dev_view} />}
          {report?.metrics?.documents?.parsed?.length > 0 && <Card size="small" title="Tài liệu đã đọc" style={{ marginBottom: 16 }}>
            <List size="small" dataSource={report.metrics.documents.parsed} renderItem={(document) => <List.Item>
              <Space wrap><Text strong>{document.kind === 'ads_scripts' ? 'ADS SCRIPTS' : 'Working file'}</Text>
                <Tag color={document.method === 'ai_mapping' ? 'blue' : 'default'}>{document.method === 'ai_mapping' ? 'AI hỗ trợ nhận dạng' : 'Đọc trực tiếp'}</Tag>
                <Text type="secondary">{document.sheet ? `${document.sheet} · ` : ''}{document.rows} dòng dữ liệu{document.header_line ? ` · tiêu đề dòng ${document.header_line}` : ''}</Text>
              </Space>
            </List.Item>} />
          </Card>}
          {report?.metrics && <Collapse style={{ marginBottom: 16 }} items={[{ key: 'metrics', label: `Thời gian ${Math.round(report.summary.duration_seconds)} giây · ${report.summary.from_cache}/${report.summary.total} rule dùng lại kết quả`,
            children: <Space direction="vertical" style={{ width: '100%' }}>
              {!report.metrics.verdict_cache_enabled && report.engine !== 'none' && <Alert type="warning" showIcon message="Chưa xác định đầy đủ model/phiên bản CLI: lượt này không dùng lại kết luận cũ." />}
              {report.metrics.tool_budget?.overrun > 0 && <Alert type="warning" showIcon message="CLI báo công cụ sau khi đã bắt đầu; đã phát hiện vượt ngân sách và dừng phần phân tích liên quan." />}
              <Text type="secondary">{report.metrics.workers} rule có thể chạy đồng thời. Thời gian từng rule có thể chồng lấp.</Text>
              {report.metrics.usage_totals && <Text type="secondary">Token tổng: đọc cache {fmtTokens(report.metrics.usage_totals.cache_read)} · ghi cache {fmtTokens(report.metrics.usage_totals.cache_write)} · đầu vào mới {fmtTokens(report.metrics.usage_totals.input)} · đầu ra {fmtTokens(report.metrics.usage_totals.output)}</Text>}
              {report.metrics.base_reference_source?.commit && <Text type="secondary">Đối chiếu code base tại commit {report.metrics.base_reference_source.commit.slice(0, 8)}. Bằng chứng kết luận vẫn lấy từ APK.</Text>}
              <List size="small" dataSource={report.metrics.rules || []} renderItem={(metric) => <List.Item>
                <Text>{report.findings.find((finding) => finding.rule_id === metric.rule_id)?.title || metric.rule_id}</Text>
                <Text type="secondary">{metric.duration_seconds.toFixed(1)}s · {metric.from_checkpoint ? 'checkpoint' : metric.from_scoped_cache ? 'dùng lại vì code liên quan không đổi' : metric.from_cache ? 'cache' : `${metric.tool_calls} lượt công cụ`}{metric.repair_attempts ? ` · ${metric.repair_attempts} lượt sửa bằng chứng` : ''}{metric.investigation_attempts ? ` · ${metric.investigation_attempts} lượt điều tra bổ sung` : ''}{metric.review_attempts ? ' · đã review' : ''}{metric.resumed_attempts ? ` · ${metric.resumed_attempts} lượt nối phiên` : ''}{metric.usage && (metric.usage.cache_read || metric.usage.output) ? ` · token: đọc ${fmtTokens(metric.usage.cache_read)} / ghi ${fmtTokens(metric.usage.cache_write)} / ra ${fmtTokens(metric.usage.output)}` : ''}</Text>
              </List.Item>} />
            </Space> }]} />}
          {report?.inventory?.documents_available && <Alert className="inventory-notice" type={report.inventory.missing_local.length || report.inventory.mismatched_ids.length || report.inventory.package_match === false || report.inventory.app_id_match === false ? 'warning' : 'success'} showIcon
            message={`Kiểm kê ID: ${report.inventory.matching_ids.length}/${report.inventory.expected_count} placement khớp config local`}
            description={<Space direction="vertical" size={2}>
              {report.inventory.missing_local.length > 0 && <Text>Thiếu trong config: {report.inventory.missing_local.join(', ')}</Text>}
              {report.inventory.mismatched_ids.length > 0 && <Text>ID lệch: {report.inventory.mismatched_ids.join(', ')}</Text>}
              {report.inventory.extra_local.length > 0 && <Text>Thừa trong config: {report.inventory.extra_local.join(', ')}</Text>}
              {report.inventory.optional_placements?.length > 0 && <Text>Tùy chọn: {report.inventory.optional_placements.join(', ')}</Text>}
              {report.inventory.disabled_placements?.length > 0 && <Text>Không dùng theo tài liệu: {report.inventory.disabled_placements.join(', ')}</Text>}
              {report.inventory.uncertain_placements?.length > 0 && <Text>Chưa rõ trạng thái trong tài liệu: {report.inventory.uncertain_placements.join(', ')}</Text>}
              {report.inventory.document_warnings?.map((warning, index) => <Text key={`doc-warning-${index}`}>{warning}</Text>)}
              {report.inventory.package_match !== null && report.inventory.package_match !== undefined && <Text>Package: {report.inventory.package_match ? 'khớp working file' : 'không khớp working file'}</Text>}
              {report.inventory.app_id_match !== null && report.inventory.app_id_match !== undefined && <Text>AdMob App ID: {report.inventory.app_id_match ? 'khớp ADS SCRIPTS' : 'không khớp ADS SCRIPTS'}</Text>}
              <Text type="secondary">Kiểm kê từ tài liệu và assets; chưa chứng minh ID được dùng khi chạy.</Text>
            </Space>} />}
          <div className="metric-grid"><Metric title="ĐẠT" value={report?.summary?.pass} color="pass" help="Có bằng chứng phù hợp" /><Metric title="CẦN XỬ LÝ" value={report?.summary?.fail} color="fail" help="Có bằng chứng sai lệch" /><Metric title="CHƯA RÕ" value={report?.summary?.unknown} color="unknown" help="Cần thêm dữ liệu" /><Metric title="BỎ QUA" value={report?.summary?.skipped} color="skipped" help="Chưa đủ điều kiện" /></div>
          <Card className="findings-card" title="Chi tiết đầy đủ từng rule (kèm bằng chứng)" extra={<Tag color={error ? 'error' : stage === 'done' ? 'success' : 'default'}>{phase}</Tag>}>
            {job && <Paragraph type="secondary" className="report-subtitle">{job.filename}{job.package ? ` · ${job.package}` : ''}{job.state === 'done' ? ` · ${job.docs_used ? 'Đã nhận 2 tài liệu' : 'Không kèm tài liệu'}` : ''}</Paragraph>}
            {report ? <List className="findings-list" split={false} dataSource={report.findings || []} locale={{ emptyText: 'Không có luật nào trong báo cáo.' }} renderItem={(item, index) => <Finding item={item} index={index} />} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chọn APK và bấm Bắt đầu kiểm tra để xem báo cáo." />}
          </Card>
            </> },
          ]} /> : <>
          {report?.metrics?.documents?.parsed?.length > 0 && <Card size="small" title="Tài liệu đã đọc" style={{ marginBottom: 16 }}>
            <List size="small" dataSource={report.metrics.documents.parsed} renderItem={(document) => <List.Item>
              <Space wrap><Text strong>{document.kind === 'ads_scripts' ? 'ADS SCRIPTS' : 'Working file'}</Text>
                <Tag color={document.method === 'ai_mapping' ? 'blue' : 'default'}>{document.method === 'ai_mapping' ? 'AI hỗ trợ nhận dạng' : 'Đọc trực tiếp'}</Tag>
                <Text type="secondary">{document.sheet ? `${document.sheet} · ` : ''}{document.rows} dòng dữ liệu{document.header_line ? ` · tiêu đề dòng ${document.header_line}` : ''}</Text>
              </Space>
            </List.Item>} />
          </Card>}
          {report?.metrics && <Collapse style={{ marginBottom: 16 }} items={[{ key: 'metrics', label: `Thời gian ${Math.round(report.summary.duration_seconds)} giây · ${report.summary.from_cache}/${report.summary.total} rule dùng lại kết quả`,
            children: <Space direction="vertical" style={{ width: '100%' }}>
              {!report.metrics.verdict_cache_enabled && report.engine !== 'none' && <Alert type="warning" showIcon message="Chưa xác định đầy đủ model/phiên bản CLI: lượt này không dùng lại kết luận cũ." />}
              {report.metrics.tool_budget?.overrun > 0 && <Alert type="warning" showIcon message="CLI báo công cụ sau khi đã bắt đầu; đã phát hiện vượt ngân sách và dừng phần phân tích liên quan." />}
              <Text type="secondary">{report.metrics.workers} rule có thể chạy đồng thời. Thời gian từng rule có thể chồng lấp.</Text>
              {report.metrics.usage_totals && <Text type="secondary">Token tổng: đọc cache {fmtTokens(report.metrics.usage_totals.cache_read)} · ghi cache {fmtTokens(report.metrics.usage_totals.cache_write)} · đầu vào mới {fmtTokens(report.metrics.usage_totals.input)} · đầu ra {fmtTokens(report.metrics.usage_totals.output)}</Text>}
              {report.metrics.base_reference_source?.commit && <Text type="secondary">Đối chiếu code base tại commit {report.metrics.base_reference_source.commit.slice(0, 8)}. Bằng chứng kết luận vẫn lấy từ APK.</Text>}
              <List size="small" dataSource={report.metrics.rules || []} renderItem={(metric) => <List.Item>
                <Text>{report.findings.find((finding) => finding.rule_id === metric.rule_id)?.title || metric.rule_id}</Text>
                <Text type="secondary">{metric.duration_seconds.toFixed(1)}s · {metric.from_checkpoint ? 'checkpoint' : metric.from_scoped_cache ? 'dùng lại vì code liên quan không đổi' : metric.from_cache ? 'cache' : `${metric.tool_calls} lượt công cụ`}{metric.repair_attempts ? ` · ${metric.repair_attempts} lượt sửa bằng chứng` : ''}{metric.investigation_attempts ? ` · ${metric.investigation_attempts} lượt điều tra bổ sung` : ''}{metric.review_attempts ? ' · đã review' : ''}{metric.resumed_attempts ? ` · ${metric.resumed_attempts} lượt nối phiên` : ''}{metric.usage && (metric.usage.cache_read || metric.usage.output) ? ` · token: đọc ${fmtTokens(metric.usage.cache_read)} / ghi ${fmtTokens(metric.usage.cache_write)} / ra ${fmtTokens(metric.usage.output)}` : ''}</Text>
              </List.Item>} />
            </Space> }]} />}
          {report?.inventory?.documents_available && <Alert className="inventory-notice" type={report.inventory.missing_local.length || report.inventory.mismatched_ids.length || report.inventory.package_match === false || report.inventory.app_id_match === false ? 'warning' : 'success'} showIcon
            message={`Kiểm kê ID: ${report.inventory.matching_ids.length}/${report.inventory.expected_count} placement khớp config local`}
            description={<Space direction="vertical" size={2}>
              {report.inventory.missing_local.length > 0 && <Text>Thiếu trong config: {report.inventory.missing_local.join(', ')}</Text>}
              {report.inventory.mismatched_ids.length > 0 && <Text>ID lệch: {report.inventory.mismatched_ids.join(', ')}</Text>}
              {report.inventory.extra_local.length > 0 && <Text>Thừa trong config: {report.inventory.extra_local.join(', ')}</Text>}
              {report.inventory.optional_placements?.length > 0 && <Text>Tùy chọn: {report.inventory.optional_placements.join(', ')}</Text>}
              {report.inventory.disabled_placements?.length > 0 && <Text>Không dùng theo tài liệu: {report.inventory.disabled_placements.join(', ')}</Text>}
              {report.inventory.uncertain_placements?.length > 0 && <Text>Chưa rõ trạng thái trong tài liệu: {report.inventory.uncertain_placements.join(', ')}</Text>}
              {report.inventory.document_warnings?.map((warning, index) => <Text key={`doc-warning-${index}`}>{warning}</Text>)}
              {report.inventory.package_match !== null && report.inventory.package_match !== undefined && <Text>Package: {report.inventory.package_match ? 'khớp working file' : 'không khớp working file'}</Text>}
              {report.inventory.app_id_match !== null && report.inventory.app_id_match !== undefined && <Text>AdMob App ID: {report.inventory.app_id_match ? 'khớp ADS SCRIPTS' : 'không khớp ADS SCRIPTS'}</Text>}
              <Text type="secondary">Kiểm kê từ tài liệu và assets; chưa chứng minh ID được dùng khi chạy.</Text>
            </Space>} />}
          <div className="metric-grid"><Metric title="ĐẠT" value={report?.summary?.pass} color="pass" help="Có bằng chứng phù hợp" /><Metric title="CẦN XỬ LÝ" value={report?.summary?.fail} color="fail" help="Có bằng chứng sai lệch" /><Metric title="CHƯA RÕ" value={report?.summary?.unknown} color="unknown" help="Cần thêm dữ liệu" /><Metric title="BỎ QUA" value={report?.summary?.skipped} color="skipped" help="Chưa đủ điều kiện" /></div>
          <Card className="findings-card" title="Chi tiết đầy đủ từng rule (kèm bằng chứng)" extra={<Tag color={error ? 'error' : stage === 'done' ? 'success' : 'default'}>{phase}</Tag>}>
            {job && <Paragraph type="secondary" className="report-subtitle">{job.filename}{job.package ? ` · ${job.package}` : ''}{job.state === 'done' ? ` · ${job.docs_used ? 'Đã nhận 2 tài liệu' : 'Không kèm tài liệu'}` : ''}</Paragraph>}
            {report ? <List className="findings-list" split={false} dataSource={report.findings || []} locale={{ emptyText: 'Không có luật nào trong báo cáo.' }} renderItem={(item, index) => <Finding item={item} index={index} />} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chọn APK và bấm Bắt đầu kiểm tra để xem báo cáo." />}
          </Card>
          </>}
        </section>
        <footer><Space><CheckCircleOutlined /> APK Audit · Local workspace</Space></footer>
      </Content>
    </Layout>
  );
}
