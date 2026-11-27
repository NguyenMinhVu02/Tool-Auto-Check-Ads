# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quy ước dự án

- Giao tiếp bằng tiếng Việt; giữ nguyên tên file, lệnh, thuật ngữ kỹ thuật. Chuỗi hiển thị cho người dùng (CLI help, báo cáo, web) cũng bằng tiếng Việt.
- Đầu phiên đọc `AGENTS.md` và phần **Trạng thái hiện tại** của `SESSION_LOG.md` (file rất dài, chỉ đọc phần đầu). Cuối phiên cập nhật trạng thái và thêm mục phiên mới theo `AGENTS.md`, giờ `Asia/Ho_Chi_Minh`.
- Không tự commit/push/restart server khi chưa được yêu cầu. Sau khi sửa code backend, `serve` đang chạy phải restart mới nạp code/model mới.

## Lệnh thường dùng

```bash
uv sync --extra mcp                                   # cài phụ thuộc (mcp cần cho test MCP)
uv run apk-audit doctor                               # kiểm tra jadx, Java, claude, codex
uv run apk-audit serve                                # web http://127.0.0.1:8765, kết quả ở out/web/
uv run apk-audit audit <apk|workspace> --ads-scripts X.xlsx --checklist Y.xlsx --engine claude
uv run apk-audit audit examples/workspace --engine none --out out/demo   # chạy tất định, không tốn token
uv run apk-audit rules check|list --rules rulepacks/default
uv run apk-audit benchmark --quality                  # bộ ca claim tổng hợp offline, không gọi AI

# Kiểm thử Python (unittest, không dùng pytest)
uv run --extra mcp python -m unittest discover -s tests
uv run python -m unittest tests.test_slicer                         # một file
uv run python -m unittest tests.test_slicer.SlicerTests.test_methods_are_found_with_braces_in_strings_and_comments_ignored   # một test

# Frontend (React + antd + three.js, Vite)
cd frontend && npm ci && npm run build      # build thẳng vào apk_audit/web_assets/ (app.js, app.css được commit)
node --test frontend/src/*.test.js          # test frontend dùng node:test
```

- Test MCP stdio và web mở socket localhost; trong sandbox sẽ fail do timeout/socket bị chặn, cần chạy ngoài sandbox.
- Mã thoát CLI: `1` = có rule FAIL; `7` = tài liệu có vẻ thuộc app khác (vượt bằng `--confirm-mismatch`).

## Kiến trúc

Công cụ audit tĩnh cách app Android tích hợp quảng cáo Infinity: so ID ads với tài liệu và kiểm logic load/show của 4 màn đầu (Splash, Language, Onboarding, Welcome) cùng init SDK/Remote Config.

Luồng chính (`apk_audit/pipeline.py:run`, dùng chung cho CLI `cli.py`, web `web.py` và MCP):

1. **Unpack** (`unpack.py`, `pipeline.prepare`): APK/XAPK/APKM giải mã bằng JADX thành workspace (`sources/`, `resources/`, tùy chọn `smali/`), cache theo hash.
2. **Facts** (`facts/`): manifest, assets JSON (`ad_config.json`, `ad_config_debug.json`), chuỗi theo regex trong `rulepacks/default/extract.yaml`.
3. **Documents** (`documents.py`, `document_structure.py`): đọc ADS SCRIPTS và working file (XLSX/CSV, nhiều sheet, giữ fill/gạch ngang để biết placement không dùng). Parser không hiểu cột thì gọi AI chỉ để ánh xạ tọa độ cột.
4. **Inventory** (`inventory.py`, `placement_policy.py`): đối chiếu tất định ID tài liệu và ID trong app; alias tên placement ở `PLACEMENT_ALIASES`.
5. **Preflight** (`preflight.py`): chặn trước khi tốn quota AI nếu package / AdMob App ID / tài khoản AdMob lệch.
6. **Rules** (`rules/`): rule pack YAML trong `rulepacks/default/rules/` (version ở `pack.yaml`, tham chiếu base ở `context.md` và `base-reference.json`). `mode: static` chạy ngay (`rules/checks.py`, `rules/custom.py`); `mode: agent` gửi AI.
7. **Agent** (`agent.py`, `engines.py`, `claude_engine.py`, `engine_common.py`): dựng prompt cho từng rule, gọi Claude/Codex CLI ở chế độ chỉ đọc với JSON schema, kiểm cấu trúc, xác minh evidence (file + dòng + anchor, tool tự lấy excerpt thật), repair/investigation nối tiếp phiên, review độc lập cho FAIL. Claim lỗi chỉ dựa trên "không thấy" bị hạ thành UNKNOWN khi mã bị làm rối (`claim_verifier.py`).
   - Giảm context: `context_scope.py` lọc tài liệu/inventory theo `area` của rule; `slicer.py` trích sẵn hàm liên quan kèm số dòng thật; `flow_map.py` dựng bản đồ luồng ads; `source_index.py` lập chỉ mục mã.
8. **Cache**: `verdict_cache.py` (khóa theo APK, pack, rule, engine/model/effort, tài liệu, policy), `scoped_cache.py` (dùng lại PASS/FAIL giữa các build khi file AI đã đọc không đổi), `passed_history.py`, `cache_identity.py`. Đổi prompt/schema/verifier phải nâng policy để vô hiệu cache cũ.
9. **Report**: `report.py` (md/json), `marketing.py` (tab Marketing), `dev_view.py` (tab Dev), `report_html.py` (một file HTML).

Thành phần khác: `mcp_server.py` (MCP stdio chỉ đọc trên workspace), `execution.py` (worker song song, tối đa 10), `benchmark.py` + `quality_cases.json`, `scripts/` (đo audit, snapshot base reference).

## Nguyên tắc khi sửa logic audit

- Kết luận dựa trên mã JADX đã giải mã, có thể bị R8 làm rối. Chuỗi, manifest và assets là căn cứ chắc; thiếu tên hàm không được kết luận FAIL khi mã bị làm rối hoặc có file giải mã lỗi.
- PASS chỉ khi đủ mọi yêu cầu bắt buộc. Thiếu bằng chứng thì giữ UNKNOWN có lý do, không nới verifier để giảm số UNKNOWN.
- Model tự chọn theo CLI đã cài, effort luôn `low`, không tự fallback khi model lỗi: Claude dùng alias `sonnet` (Sonnet mới nhất), Codex chọn `gpt-<version>-terra` mới nhất trong `codex debug models` (không có thì `-sol` mới nhất). Ghi đè bằng `APK_AUDIT_CLAUDE_MODEL` / `APK_AUDIT_CODEX_MODEL`. Model/effort nằm trong tên engine và khóa cache (kèm phiên bản CLI).

## Tài liệu

- `README.md`: hướng dẫn dùng cho Marketing/Dev.
- `docs/technical-reference.md`: chi tiết cơ chế, cú pháp rule YAML và các phép `check` static, MCP, chỗ nối tích hợp.
- `docs/base-ads-contract.md`: chuẩn ads/init của base project. `docs/audit-optimization.md`: cache, metrics, benchmark.
- `docs/superpowers/plans/`, `docs/superpowers/specs/`: kế hoạch triển khai theo từng đợt.
