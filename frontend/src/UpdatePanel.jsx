import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Space, Tag, Typography } from 'antd';
import { updateView } from './updateStatus';

const { Text, Paragraph } = Typography;

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Lỗi ${response.status}`);
  return data;
}

const wait = (ms) => new Promise((resolve) => { setTimeout(resolve, ms); });

// Shared state: banner (compact) and the card on the setup page use the same calls.
export function useUpdater() {
  const [status, setStatus] = useState(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');
  const [phase, setPhase] = useState('idle'); // idle | updating | restarting | failed
  const [log, setLog] = useState([]);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const check = useCallback(async (force = false) => {
    setChecking(true);
    setError('');
    try {
      setStatus(await readJson(await fetch(`/api/update/status${force ? '?force=1' : ''}`)));
    } catch (cause) {
      setError(cause.message);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => { check(false); }, [check]);

  const apply = useCallback(async () => {
    setError('');
    setLog([]);
    setPhase('updating');
    try {
      await readJson(await fetch('/api/update/apply', { method: 'POST' }));
    } catch (cause) {
      setError(cause.message);
      setPhase('failed');
      return;
    }
    const target = status?.latest;
    for (let i = 0; i < 600 && alive.current; i += 1) {
      await wait(1500);
      try {
        const data = await readJson(await fetch('/api/update/status'));
        if (data.job) setLog(data.job.log || []);
        if (data.job?.state === 'error') {
          setError(data.job.error);
          setPhase('failed');
          return;
        }
        if (data.job?.state === 'restarting') setPhase('restarting');
        if (data.current === target) { window.location.reload(); return; }
      } catch {
        setPhase('restarting'); // server is down while it restarts
      }
    }
  }, [status]);

  return { status, checking, error, phase, log, check, apply };
}

export function UpdateBanner({ updater, onOpen }) {
  const view = updateView(updater.status);
  if (!view.available || updater.phase !== 'idle') return null;
  return <Alert className="update-banner" type="info" showIcon
    message={`Có bản mới ${updater.status.latest} (đang dùng ${updater.status.current})`}
    action={<Space><Button size="small" onClick={onOpen}>Xem thay đổi</Button><Button size="small" type="primary" onClick={updater.apply}>Cập nhật</Button></Space>} />;
}

export default function UpdatePanel({ updater }) {
  const { status, checking, error, phase, log, check, apply } = updater;
  const view = updateView(status);
  return (
    <Card className="setup-card" id="update" title="Cập nhật tool" extra={<Space>
      {status && <Tag color={view.available ? 'processing' : 'success'}>{view.available ? `Có bản ${status.latest}` : 'Đang dùng bản mới nhất'}</Tag>}
      <Button onClick={() => check(true)} loading={checking} disabled={phase === 'updating' || phase === 'restarting'}>Kiểm tra cập nhật</Button>
    </Space>}>
      <Paragraph type="secondary">Phiên bản đang dùng: <Text strong>{status?.current || '...'}</Text>
        {status?.latest && <> · Bản mới nhất trên GitHub: <Text strong>{status.latest}</Text></>}
        {status?.checked_at && <> · Kiểm tra lúc {new Date(status.checked_at * 1000).toLocaleTimeString('vi-VN')}</>}</Paragraph>
      {status?.error && <Alert type="warning" showIcon message={status.error} style={{ marginBottom: 12 }} />}
      {status?.git_checkout && <Alert type="info" showIcon message="Đây là bản dev (thư mục git): cập nhật bằng git pull, nút cập nhật bị tắt." style={{ marginBottom: 12 }} />}
      {view.available && phase === 'idle' && <>
        {status.notes && <pre className="update-notes">{status.notes}</pre>}
        <Button type="primary" onClick={apply}>Cập nhật lên {status.latest}</Button>
        <Paragraph type="secondary" style={{ marginTop: 8 }}>Kết quả kiểm tra cũ, cache và công cụ đã cài được giữ nguyên. Tool tự khởi động lại và tải lại trang khi xong.</Paragraph>
      </>}
      {(phase === 'updating' || phase === 'restarting') && <Alert type="info" showIcon
        message={phase === 'restarting' ? 'Đang khởi động lại bản mới, trang sẽ tự tải lại...' : 'Đang cập nhật, đừng đóng cửa sổ tool...'}
        description="Nếu sau 1 phút trang chưa tự tải lại: đóng cửa sổ APK Audit rồi bấm lại biểu tượng trên màn hình chính." />}
      {log.length > 0 && <div className="setup-log"><pre>{log.slice(-20).join('\n')}</pre></div>}
      {error && <Alert type="error" showIcon message={error} style={{ marginTop: 12 }} />}
    </Card>
  );
}
