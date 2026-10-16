"""Claude Code CLI adapter with read tools, structured output and bounded execution."""

import json
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time

from .contracts import AgentResult
from .engine_common import audit_instruction, verdict_schema
from .errors import AuditError


class ClaudeEngine:
    name = 'claude:default'

    def available(self):
        return shutil.which('claude') is not None

    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        if max_tool_calls <= 0:
            return AgentResult('', exhausted_budget=True)
        command = [
            'claude', '--print', '--output-format', 'stream-json', '--verbose',
            '--json-schema', json.dumps(verdict_schema()),
            '--no-session-persistence', '--safe-mode', '--restricted',
            '--tools', 'Read,Glob,Grep', '--allowedTools', 'Read,Glob,Grep',
            '--permission-mode', 'dontAsk', '--disable-slash-commands',
            '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
        ]
        with tempfile.TemporaryDirectory(prefix='apk-audit-claude-') as temp:
            stderr_path = Path(temp) / 'claude.stderr'
            with stderr_path.open('wb') as stderr:
                try:
                    process = subprocess.Popen(command, cwd=tools.root, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=stderr)
                except OSError as exc:
                    raise AuditError(f'Không chạy được Claude CLI: {exc}', 6) from exc
                try:
                    process.stdin.write(audit_instruction(prompt, max_tool_calls).encode('utf-8'))
                    process.stdin.close()
                    result, calls, exhausted = self._collect(process, max_tool_calls, timeout)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    process.stdin.close()
                    process.stdout.close()
            if exhausted:
                return AgentResult('', tool_calls=calls, exhausted_budget=True)
            if process.returncode:
                detail = stderr_path.read_text(encoding='utf-8', errors='replace')[-1000:].strip()
                if not detail and result:
                    detail = str(result.get('result') or result.get('errors') or '')[-1000:]
                raise AuditError('Claude CLI lỗi: ' + (detail or f'exit {process.returncode}'), 6)
            if not result:
                raise AuditError('Claude CLI không trả kết quả; kiểm tra phiên đăng nhập và phiên bản CLI.', 6)
            if result.get('is_error') or result.get('subtype') != 'success':
                detail = result.get('errors') or result.get('result') or result.get('subtype', 'error')
                raise AuditError('Claude CLI không hoàn thành: ' + str(detail)[-1000:], 6)
            payload = result.get('structured_output')
            if not isinstance(payload, dict):
                try:
                    payload = json.loads(result.get('result', ''))
                except (ValueError, TypeError):
                    payload = None
            if not isinstance(payload, dict):
                raise AuditError('Claude CLI không trả kết quả JSON theo schema.', 6)
            return AgentResult(json.dumps(payload, ensure_ascii=False), tool_calls=calls)

    @staticmethod
    def _collect(process, max_tool_calls, timeout):
        messages = queue.Queue()

        def read_stdout():
            try:
                for line in process.stdout:
                    messages.put(line)
            finally:
                messages.put(None)

        reader = threading.Thread(target=read_stdout, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        seen = set()
        result = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AuditError('Claude CLI quá thời gian chờ.', 6)
            try:
                line = messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise AuditError('Claude CLI quá thời gian chờ.', 6) from exc
            if line is None:
                break
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(event, dict):
                continue
            if event.get('type') == 'assistant':
                message = event.get('message', {})
                content = message.get('content', []) if isinstance(message, dict) else []
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get('type') == 'tool_use':
                        seen.add(block.get('id') or f'unnamed-{len(seen)}')
                        if len(seen) > max_tool_calls:
                            return None, len(seen), True
            elif event.get('type') == 'result':
                result = event
        return result, len(seen), False
