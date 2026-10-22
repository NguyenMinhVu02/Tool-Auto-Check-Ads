import { useEffect } from 'react';

const BASE_TITLE = 'APK Audit · Local workspace';
const SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
const COLORS = { running: '#2767d8', done: '#26c593', error: '#e5484d', waiting: '#f5a524', idle: '#8299ba' };

export function tabTitle(state, label, frame) {
  const text = label ? ` ${label}` : '';
  if (state === 'running') return `${SPINNER[frame % SPINNER.length]} Đang kiểm tra${text} · APK Audit`;
  if (state === 'waiting') return '❔ Cần xác nhận tài liệu · APK Audit';
  if (state === 'done') return '✅ Đã xong · APK Audit';
  if (state === 'error') return '⚠️ Có lỗi · APK Audit';
  return BASE_TITLE;
}

// A 32px canvas icon: a ring with a bright arc that spins while the audit runs.
function drawIcon(state, angle) {
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 32;
  const ctx = canvas.getContext('2d');
  ctx.lineWidth = 5;
  ctx.lineCap = 'round';
  ctx.strokeStyle = `${COLORS[state]}33`;
  ctx.beginPath();
  ctx.arc(16, 16, 11, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = COLORS[state];
  ctx.beginPath();
  if (state === 'running') ctx.arc(16, 16, 11, angle, angle + Math.PI * 1.1);
  else ctx.arc(16, 16, 11, 0, Math.PI * 2);
  ctx.stroke();
  return canvas.toDataURL('image/png');
}

function iconLink() {
  let link = document.querySelector('link[rel="icon"]');
  if (!link) {
    link = document.createElement('link');
    link.rel = 'icon';
    document.head.appendChild(link);
  }
  return link;
}

/** Animates the browser tab (title spinner + spinning favicon) while an audit runs. */
export function useTabIndicator(state, label) {
  useEffect(() => {
    const link = iconLink();
    const original = link.getAttribute('href');
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let frame = 0;
    const paint = () => {
      document.title = tabTitle(state, label, frame);
      try { link.href = drawIcon(state, (frame * Math.PI) / 5); } catch { /* canvas can be blocked; the title still animates */ }
    };
    paint();
    if (state !== 'running' || reduced) return () => { if (original) link.setAttribute('href', original); };
    // Background tabs throttle timers to ~1s, which is still a visible spin in the tab strip.
    const timer = setInterval(() => { frame += 1; paint(); }, 120);
    return () => {
      clearInterval(timer);
      if (original) link.setAttribute('href', original);
    };
  }, [state, label]);
}
