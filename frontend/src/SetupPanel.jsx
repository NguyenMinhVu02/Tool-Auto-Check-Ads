import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, List, Space, Tag, Typography } from 'antd';
import { setupSummary, toolStatus } from './setupStatus';

const { Text, Paragraph } = Typography;
const statusTags = {
  ok: ['success', 'Đã có'],
  login: ['warning', 'Cần đăng nhập'],
  missing: ['error', 'Chưa có'],
  optional: ['default', 'Chưa cài (tùy chọn)'],
};

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Lỗi ${response.status}`);
  return data;
}

export default function SetupPanel({ onReadyChange }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [job, setJob] = useState(null);
  const [queue, setQueue] = useState([]);
  const timerRef = useRef(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await readJson(await fetch('/api/setup/status'));
      setStatus(data);
      onReadyChange?.(data);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setLoading(false);
    }
  }, [onReadyChange]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => () => clearTimeout(timerRef.current), []);

  const poll = useCallback((id) => {
    timerRef.current = setTimeout(async () => {
      try {
        const data = await readJson(await fetch(`/api/setup/jobs/${id}`));
        setJob(data);
        if (data.state === 'running') poll(id);
        else refresh();
      } catch (cause) {
        setError(cause.message);
      }
    }, 1000);
  }, [refresh]);

  const install = useCallback(async (tool) => {
    setError('');
    try {
      const { id } = await readJson(await fetch(`/api/setup/install/${tool}`, { method: 'POST' }));
      setJob({ id, tool, state: 'running', log: [] });
      poll(id);
    } catch (cause) {
      setError(cause.message);
    }
  }, [poll]);

  // "Cài tất cả": install the queued tools one after another.
  useEffect(() => {
    if (!queue.length || job?.state === 'running') return;
    if (job?.state === 'error') { setQueue([]); return; }
    const [next, ...rest] = queue;
    setQueue(rest);
    install(next);
  }, [queue, job, install]);

  const login = async (tool) => {
    setError('');
    try {
      await readJson(await fetch(`/api/setup/login/${tool}`, { method: 'POST' }));
    } catch (cause) {
      setError(cause.message);
    }
  };

  const summary = setupSummary(status);
  const running = job?.state === 'running' || queue.length > 0;

  return (
    <Card className="setup-card" id="setup" title="Thiết lập máy" extra={<Space>
      <Tag color={summary.ready ? 'success' : 'warning'}>{summary.ready ? 'Sẵn sàng' : 'Còn thiếu công cụ'}</Tag>
      <Button onClick={refresh} loading={loading} disabled={running}>Kiểm tra lại</Button>
    </Space>}>
      <Paragraph type="secondary">Tool cần Java, JADX và ít nhất một AI CLI (Claude hoặc Codex). Bấm Cài để tự tải về máy, không cần quyền quản trị. Công cụ được lưu tại <Text code>{status?.tools_dir || '...'}</Text>.</Paragraph>
      {summary.missingRequired.length > 0 && <Button type="primary" disabled={running} onClick={() => setQueue(summary.installAll)} style={{ marginBottom: 12 }}>Cài tất cả phần bắt buộc</Button>}
      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}
      <List dataSource={status?.items || []} loading={loading && !status} renderItem={(item) => {
        const state = toolStatus(item);
        const [color, label] = statusTags[state];
        const busyHere = job?.state === 'running' && job.tool === item.id;
        return <List.Item actions={[
          ...(!item.installed ? [<Button key="install" type={item.required ? 'primary' : 'default'} loading={busyHere} disabled={running && !busyHere} onClick={() => install(item.id)}>Cài</Button>] : []),
          ...(item.ai && item.installed ? [<Button key="login" disabled={running} onClick={() => login(item.id)}>{item.logged_in ? 'Đăng nhập lại' : 'Đăng nhập'}</Button>] : []),
        ]}>
          <List.Item.Meta title={<Space wrap><Text strong>{item.label}</Text><Tag color={color}>{label}</Tag>{item.required && <Tag>Bắt buộc</Tag>}</Space>}
            description={<Space direction="vertical" size={0}>
              <Text type="secondary">{item.purpose}</Text>
              {item.version && <Text type="secondary">Phiên bản: {item.version}</Text>}
              {item.note && <Text type="warning">{item.note}</Text>}
              {item.ai && item.installed && item.logged_in === null && <Text type="secondary">Chưa xác định được trạng thái đăng nhập. Nếu chưa đăng nhập, bấm Đăng nhập.</Text>}
            </Space>} />
        </List.Item>;
      }} />
      {job && <div className="setup-log">
        <Text strong>{job.state === 'running' ? `Đang cài ${job.tool}...` : job.state === 'done' ? `Đã cài xong ${job.tool}` : `Cài ${job.tool} thất bại`}</Text>
        <pre>{(job.log || []).slice(-30).join('\n')}</pre>
        {job.state === 'error' && <Alert type="error" showIcon message={job.error} description="Kiểm tra kết nối mạng rồi bấm Cài lại. Nếu vẫn lỗi, gửi đoạn log trên cho dev." />}
      </div>}
      {summary.needsLoginHint && <Alert type="info" showIcon message="Sau khi bấm Đăng nhập, làm theo hướng dẫn trong cửa sổ vừa mở (trình duyệt sẽ hỏi xác nhận tài khoản). Xong thì quay lại đây bấm Kiểm tra lại." />}
    </Card>
  );
}
