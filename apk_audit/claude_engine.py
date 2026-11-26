"""Claude Code CLI adapter with read tools, structured output and bounded execution."""

import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import uuid

from .contracts import AgentResult
from .engine_common import agent_error, audit_instruction, report_activity, retain_source_read, verdict_schema
from .errors import AuditError


class ClaudeEngine:
    model = 'claude-sonnet-5'
    reasoning_effort = 'low'
    name = f'claude:{model}:{reasoning_effort}'
    label = 'Claude CLI (Sonnet 5 · low)'
    requires_claims = True
    # Follow-up repair/investigation turns continue the rule's own session, so the
    # long audit prompt and the code already read stay in the prompt cache.
    supports_resume = True

    def available(self):
        return shutil.which('claude') is not None

    def run_agent(self, prompt, tools, max_tool_calls, timeout=600, resume=None):
        if max_tool_calls <= 0:
            return AgentResult('', exhausted_budget=True)
        session = resume or str(uuid.uuid4())
        result = self._run_structured(audit_instruction(prompt, max_tool_calls), tools,
                                      verdict_schema(), max_tool_calls, timeout, 'Read,Glob,Grep',
                                      session=session, resume=bool(resume))
        result.session_id = session
        return result

    @staticmethod
    def close_session(session_id):
        # Sessions are only kept for follow-ups inside one rule; drop the transcript afterwards.
        root = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'projects'
        for path in root.glob(f'*/{session_id}.jsonl'):
            path.unlink(missing_ok=True)

    def map_document(self, instruction, tools, schema, timeout=90):
        return self._run_structured(instruction, tools, schema, 0, timeout, '')

    def _run_structured(self, instruction, tools, schema, max_tool_calls, timeout, allowed_tools,
                        session=None, resume=False):
        persistence = (['--resume', session] if resume else ['--session-id', session]) if session else ['--no-session-persistence']
        command = [
            shutil.which('claude') or 'claude', '--print', '--output-format', 'stream-json', '--verbose',
            '--model', self.model, '--effort', self.reasoning_effort,
            '--settings', json.dumps({'availableModels': [self.model], 'fallbackModel': [],
                                      'switchModelsOnFlag': False}),
            '--json-schema', json.dumps(schema),
            *persistence, '--safe-mode', '--restricted',
            '--tools', allowed_tools, '--allowedTools', allowed_tools,
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
                    process.stdin.write(instruction.encode('utf-8'))
                    process.stdin.close()
                    result, calls, exhausted = self._collect(process, max_tool_calls, timeout)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    process.stdin.close()
                    process.stdout.close()
            if exhausted:
                return AgentResult('', tool_calls=calls, exhausted_budget=True, session_id=session,
                                   events=(result or {}).get('_audit_events', []))
            usage = result.get('usage', {}) if isinstance(result, dict) else {}
            if process.returncode:
                detail = stderr_path.read_text(encoding='utf-8', errors='replace')[-1000:].strip()
                if not detail and result:
                    detail = str(result.get('result') or result.get('errors') or '')[-1000:]
                raise agent_error('Claude CLI lỗi: ' + (detail or f'exit {process.returncode}'), calls, usage)
            if not result:
                raise agent_error('Claude CLI không trả kết quả; kiểm tra phiên đăng nhập và phiên bản CLI.', calls, usage)
            if result.get('is_error') or result.get('subtype') != 'success':
                detail = result.get('errors') or result.get('result') or result.get('subtype', 'error')
                raise agent_error('Claude CLI không hoàn thành: ' + str(detail)[-1000:], calls, usage)
            payload = result.get('structured_output')
            if not isinstance(payload, dict):
                try:
                    payload = json.loads(result.get('result', ''))
                except (ValueError, TypeError):
                    payload = None
            if not isinstance(payload, dict):
                raise agent_error('Claude CLI không trả kết quả JSON theo schema.', calls, usage)
            return AgentResult(json.dumps(payload, ensure_ascii=False), tool_calls=calls, usage=usage,
                               events=result.get('_audit_events', []))

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
        events = []
        commands = {}
        result = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise agent_error('Claude CLI quá thời gian chờ.', len(seen))
            try:
                line = messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise agent_error('Claude CLI quá thời gian chờ.', len(seen)) from exc
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
                        commands[block.get('id')] = str(block.get('name', '')) + ' ' + json.dumps(block.get('input', {}), ensure_ascii=False)[:1000]
                        report_activity(tool_calls=len(seen), command=commands[block.get('id')][:300])
                        if len(seen) > max_tool_calls:
                            return {'_audit_events': events}, len(seen), True
            elif event.get('type') == 'user':
                message = event.get('message', {})
                content = message.get('content', []) if isinstance(message, dict) else []
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        output = block.get('content', '')
                        retain_source_read(events, commands.get(block.get('tool_use_id'), 'tool result'),
                                           output if isinstance(output, str) else json.dumps(output, ensure_ascii=False))
            elif event.get('type') == 'result':
                result = event
        if result is not None:
            result['_audit_events'] = events
        return result, len(seen), False
