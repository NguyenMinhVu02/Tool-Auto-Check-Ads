# Audit Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Chuẩn bị evidence tốt hơn, kiểm chứng claim và giảm công việc audit lặp, có metrics/checkpoint và concurrency giới hạn.
**Architecture:** SourceIndex và claim verifier độc lập; pipeline kết hợp bundle, cache fingerprint, metrics và scheduler. Web lưu job nguyên tử và cho resume chủ động. Benchmark offline phân biệt kiểm thử fixture với accuracy thật.
**Tech Stack:** Python >=3.11, unittest, concurrent.futures, JSON atomic persistence, React/Ant Design.
**Spec:** docs/superpowers/specs/2026-10-19-audit-optimization.md

## Global Constraints
- Không tự commit/push; giữ thay đổi hiện có. Feature branch trong workspace hiện tại, không tạo worktree cần xác nhận mới.
- Codex Luna mặc định; không tự đổi model/provider; workers 1 mặc định, tối đa 2.
- Không dependency mới; compatibility legacy fixtures, bằng chứng không coi là chứng minh runtime.

## Review Focus
- Mã obfuscated, multiline và bundle bị cắt: vẫn giữ UNKNOWN khi không đủ căn cứ.
- Cache sai phiên bản/model hoặc bị sửa trên disk: không nhận PASS/FAIL chưa hợp lệ.
- Review FAIL timeout/budget: không âm thầm nhận verdict chưa qua review.
- Hai worker gần hết budget và rule cuối: không vượt tổng, không mất finding, thứ tự ổn định.
- Server restart/upload dang dở/path bị sửa: không tự chạy AI, không đọc file ngoài output_root.

### Task 1: Source index và gói evidence
**Files:** apk_audit/source_index.py, tests/test_source_index.py.
**Interfaces:** SourceIndex.build(workspace, content_hash, cache_dir); bundle(rule, facts, inventory, max_chars=20000) -> dict. Có metadata cache_hit/coverage/truncated, snippets chứa file/start/lines. Chỉ index trusted workspace, không đọc symlink ngoài root.
- [x] Viết test ranking theo key bất kể tên hàm, manifest/Application, bounded bundle, cache theo hash/policy, escaping/symlink.
- [x] Chạy RED test_source_index.py; implement tối thiểu; chạy GREEN.

### Task 2: Claim verification và targeted review
**Files:** apk_audit/{agent,claim_verifier,engine_common,contracts,engines,claude_engine}.py; tests/test_claims.py; tests/fixtures/audit-quality/.
**Interfaces:** evaluate giữ signature; live adapters requires_claims=True; Finding thêm claims/verification; schema live chứa claims. Replay legacy không cần claim. Trace attempts ghi prompt size/duration/review và tổng tool calls.
- [x] Viết test một verdict kèm excerpt đúng nhưng thiếu applicability/path, runtime claim, unresolved code, reviewer bác bỏ và review budget/error; legacy vẫn đọc được.
- [x] Chạy RED; implement checker cấu trúc/liên kết evidence và review trong cùng budget; chạy GREEN cả suite liên quan.

### Task 3: Metrics, cache và scheduler
**Files:** apk_audit/{pipeline,execution,verdict_cache,cli}.py, tests/test_execution.py.
**Interfaces:** run(...workers=1), report.metrics={phases,rules,workers}; cache.key(...policy=...), get_engine identity giữ provider/model/CLI. Rule runner trả Finding/trace/cache flag/duration. Giao thoa luôn cuối, phụ thuộc claims/evidence đã kiểm. CLI audit/serve --workers choices 1,2.
- [x] Viết test phase/rule metrics, bundle được gửi AI, cache prompt/verifier/model đổi, tamper evidence, unknown identity disables cache, 2-worker overlap + total budget + stable order/crossflow.
- [x] Chạy RED; implement scheduler và pipeline; chạy GREEN.

### Task 4: Job bền vững và web
**Files:** apk_audit/web.py, frontend/src/App.jsx, tests/test_web.py.
**Interfaces:** AuditJobs(output_root,rules=None,workers=1), list_jobs(), resume(job_id); GET /api/jobs history, POST /api/jobs/{id}/resume. Persist metadata atomic, recover interrupted as error+resumable, validate paths; run(...workers=self.workers). UI lịch sử, resume và active_rules khi có nhiều worker.
- [x] Test restart done/report, interrupted resume không auto-run, cache reuse, path tamper, exclusive job, malformed state.
- [x] Chạy RED; implement; chạy GREEN, build frontend.

### Task 5: Benchmark và quality cases
**Files:** apk_audit/benchmark.py, tests/test_benchmark.py, docs/audit-optimization.md, README.md.
**Interfaces:** offline quality suite có expected verdict/claim failure reason; command benchmark chạy workspace với engine none/replay hoặc opt-in AI cùng fingerprint, output JSON thời gian/cache/quality không bịa token. CLI benchmark support --workers --engine --repeats; không so hai report khác fingerprint như cặp tương đương.
- [x] Test quality confusion/unknown counts, comparison compatibility/fingerprint, cold/warm sequence; RED rồi GREEN.
- [x] Chạy offline benchmark, full tests, frontend build và smoke workspace; review độc lập, sửa lỗi quan trọng bằng test RED/GREEN.

### Task 6: Handoff
- [x] Cập nhật tiến độ/decisions/test và giới hạn tại SESSION_LOG.md + ledger; giữ code chưa commit/push theo yêu cầu.

## Evidence và điều chỉnh sau triển khai

- Baseline 51 test đạt. Sau review và pilot lớn: 127 test đạt, frontend build đạt, quality synthetic 15 ca đạt (chạy lại trước bàn giao).
- Native Codex smoke trên static slot fixture: 1 FAIL đúng lỗi, 1 targeted review accepted, 4 tools, 38.05s; warm cùng fingerprint 0 tools, 1/1 cache hit. Không dùng làm tuyên bố tăng tốc fresh APK AI.
- Independent review: sửa shape/integrity cache+checkpoint, đối chiếu reviewed payload và rebuild index cache thiếu truncated. Mỗi lỗi có test RED/GREEN.
- Phân biệt unresolved blocker trong scope với limitations ngoài scope sau smoke thật; không loại blocker bằng diễn giải prose.
- Ledger task completion không có commit vì AGENTS yêu cầu người dùng cho phép riêng; code để review trên feature branch.
- Native tools budget là reservation + observed stop, không hard pre-execution gate. Không giả định hard cap vật lý; metrics giữ observed overrun và warning.
- Chưa tự sinh smali/callgraph chính xác hoặc runtime; không tuyên bố precision APK từ fixture replay.

### Điều chỉnh từ pilot APK lớn

Index v1 toàn vocabulary tạo cache398MB và mất62.49s với59,457file/284MBtext. Đã chuyển audit vocabulary v2, JSON compact, caps nhỏ và chia sẻ file manifest cho facts/assets/strings/inventory/tools/xrefs. Index v2 trên cùng corpus:16,086,507B, cold53.63s, warm1.85s, bundle0.19s; local preprocessing engine none20.24s (facts18.31s), không tính AI.

Pilot Splash thật trước chỉnh guard cuối: UNKNOWN vì evidence/claim chưa hợp lệ,267.49s/19tools; không coi draft FAIL là lỗi xác nhận. Đã thêm targeted review khi còn supported violation nhưng claim phụ lỗi, strict final guard không giảm; UNKNOWN quote draft có nhãn chưa chấp nhận. Fixture/replay IPTV kiểm chứng nhánh mới, chưa gọi lại đủ11rule bằng AI sau thay đổi cuối.
