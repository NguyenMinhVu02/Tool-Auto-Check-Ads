# Kế hoạch: báo cáo dễ đọc, audit nhanh hơn, ít token hơn

Ngày lập: 2026-10-21 (Asia/Ho_Chi_Minh). Nhánh đề xuất: `feat/readable-fast-cheap-audit` tách từ `main`.

## Mục tiêu và mốc so sánh

| Chỉ số | Mốc hiện có | Mục tiêu |
|---|---|---|
| Thời gian lượt đầu (APK AI Learn, Sonnet) | 242s (Sonnet medium, 4 workers, trước khi tiết kiệm token) | 120–180s |
| Audit lại bản build mới, ít file đổi | bằng lượt đầu | < 60s |
| Token mỗi lượt | cache write ~1.07M, cache read ~2.35M, output ~126K (Sonnet medium) | giảm 40–60% |
| Độ chính xác | 5 PASS / 2 FAIL / 4 UNKNOWN (11 rule AI) | ≥ hiện tại, ít UNKNOWN hơn |

Dữ liệu chuẩn để đo: APK `out/web/uploads/c7d5612c346240a2b8d2d831d9e900bc.apk`, ADS SCRIPTS `out/web/documents/6d730ae4f3624eeb853444c0cd7b859e.csv`, working file `out/web/documents/491b36ed85304717b670cd3b59b54cde.csv`, cache `out/web/cache`.

Nguyên tắc: làm từng giai đoạn, mỗi giai đoạn có test RED→GREEN; không đổi model/effort/budget ngoài phạm vi đã ghi; PASS/FAIL vẫn bắt buộc evidence + review như hiện tại; không tự commit/push.

---

## Giai đoạn 0 — Đo lường (làm đầu tiên)

**Task 0.1 — Token theo rule trong metrics và UI**
- `apk_audit/pipeline.py`: `metrics.rules[].usage_observed` đã có; thêm tổng hợp `metrics.usage_totals` = tổng `input_tokens`, `cache_read_input_tokens|cached_input_tokens`, `cache_creation_input_tokens|cache_write_input_tokens`, `output_tokens` theo engine; thêm `resumed_attempts` mỗi rule (đếm `attempt['resumed']`).
- `frontend/src/App.jsx`: trong Collapse metrics, mỗi rule hiện `đọc cache / ghi cache / đầu ra`, dòng tổng ở đầu. Rule tĩnh hiện "không dùng AI".
- Test: `tests/test_execution.py` thêm ca usage hai rule → tổng đúng, rule tĩnh 0.

**Task 0.2 — Script benchmark tái lập**
- `scripts/measure_audit.sh` (hoặc lệnh `apk-audit benchmark` hiện có): chạy audit với dữ liệu chuẩn, `--engine claude --workers 6`, in thời gian, tổng token, PASS/FAIL/UNKNOWN; ghi `out/measure/<timestamp>/`.
- Chạy 1 lượt thật **sau khi người dùng xác nhận quota**. Ghi số vào `docs/audit-optimization-validation.md` làm mốc mới.

Chấp nhận: có số đo thật của code hiện tại (Sonnet low + resume + scoped context).

---

## Giai đoạn 1 — Báo cáo dễ đọc cho Dev và MKT

**Task 1.1 — Tab Marketing / Dev trên trang kết quả**
- `frontend/src/App.jsx`: `Tabs` với `Marketing` (mặc định) và `Dev`. Marketing = `MarketingSummary` hiện có. Dev = danh sách mới (Task 1.2). Giữ "Tài liệu đã đọc", metrics trong tab Dev.

**Task 1.2 — Dev view gom theo màn, ngắn gọn**
- `apk_audit/marketing.py` → tách hàm `build_dev_view(findings)` (hoặc file mới `apk_audit/dev_view.py`): nhóm rule theo màn: Splash, Language, Onboarding, Welcome/App Open, Cấu hình & khởi tạo (INIT, REMOTE, ID, CONFIG_FLAGS, DEV_TOGGLE), Render/Tracking/Banner, Lỗi chéo.
- Mỗi rule: `status_label` (Đạt / Cần sửa / Cần dev xem lại / Không áp dụng), `conclusion` (dòng "Kết luận:" từ reasoning), `fixes` (các ý "Cần sửa:"), `locations` (file:dòng từ claims violation, tối đa 5), `unknown_reason_label` (map reason → lời thường: `unverified_evidence` → "AI dẫn chứng chưa khớp code", `engine_error` → "Lỗi CLI/hết quota", `tool_budget` → "Hết ngân sách đọc code", `missing_fact` → "Thiếu dữ liệu trong APK"...).
- Bằng chứng đầy đủ để trong `Collapse` gập.
- `report.py`: report.md phần kỹ thuật theo cùng nhóm màn và cùng nhãn.
- Test: `tests/test_dev_view.py` — nhóm đúng màn, parse Kết luận/Cần sửa, map reason.

**Task 1.3 — Không lặp lỗi giữa rule**
- Khi `ADS_ID_SOURCE_AND_COVERAGE` FAIL chỉ vì ID lệch đã có trong `marketing.id_problems`, Dev view ghi "ID sai — xem bảng ID" thay vì lặp danh sách. Quy tắc: so tên placement trong claims violation với `id_problems`.

**Task 1.4 — Xuất cho người không chạy tool**
- Marketing tab: nút "Copy danh sách ID lỗi" (text: màn — placement — tình trạng — ID tài liệu → ID app) và "Tải CSV".
- `GET /api/jobs/<id>/report.html`: `apk_audit/report.py` thêm `write_html` (1 file, CSS inline, không JS ngoài) gồm Marketing + Dev view. Nút "Tải báo cáo HTML".
- Test: `tests/test_web.py` route html 200 + chứa "Tóm tắt cho Marketing"; CSV header đúng.

**Task 1.5 — Nhãn thống nhất**
- Một bảng nhãn dùng chung Python/JS: PASS=Đạt, FAIL=Cần sửa, UNKNOWN=Cần dev xem lại, SKIPPED=Không áp dụng. Áp dụng cả report.md.

Chấp nhận: build đạt; MKT thấy danh sách ID lỗi + màn trong 1 màn hình; Dev thấy mỗi rule ≤ 3 dòng trước khi mở chi tiết.

---

## Giai đoạn 2 — Nhanh hơn

**Task 2.1 — Thêm rule tĩnh, bớt việc cho AI**
- `apk_audit/rules/custom.py` thêm:
  - `remote_config_keys`: file `remote_config_defaults`/xml defaults và các key Remote Config base dùng (lấy danh sách từ `base-reference.json` hoặc params) có mặt trong APK; FAIL nếu thiếu key bắt buộc.
  - `interstitial_interval`: giá trị interval inter (35s theo notes ADS SCRIPTS) xuất hiện ở config/init.
  - `screen_class_names`: các Activity Splash/Language/Onboarding/Welcome có trong manifest với tên theo tài liệu.
- Thu hẹp `ADS_ID_SOURCE_AND_COVERAGE` (question/verdict trong `rulepacks/default/rules/ads-flow.yaml`): AI chỉ kiểm đường getter → config.id → SDK load; phần so ID/thiếu/thừa do inventory + marketing đảm nhận. Bump pack 0.6.0.
- Test RED/GREEN cho từng check trong `tests/test_custom_rules.py`.

**Task 2.2 — Không áp dụng thì không gọi AI**
- `pipeline.execute`: trước khi gọi AI, nếu tài liệu xác định placement chính của rule đều disabled/không có (vd Welcome: `native_welcome`, `inter_welcome*`, `open_resume` đều không dùng) → `SKIPPED` lý do `not_applicable_by_document`. Bảng ánh xạ rule → placement trong `context_scope.py` (đã có `AREA_PLACEMENTS`).
- Test: Welcome không dùng → SKIPPED, 0 tool calls.

**Task 2.3 — Cache theo file liên quan (audit lại build mới)**
- Khi lưu verdict (`verdict_cache.py`), ghi thêm `dependencies.files`: tập file đã đọc trong trace (`source_read` command paths + evidence files) kèm sha256 nội dung, cùng hash của `scope_documents`/`scope_inventory` của rule và `ad_config*.json`.
- Khóa phụ "rule-scoped": `digest(rule, pack, policy, engine identity, scoped docs/inventory)` không gồm hash toàn APK. Khi khóa chính trượt, tìm bản ghi theo khóa phụ; nếu mọi file trong `dependencies.files` còn tồn tại với cùng hash → dùng lại, đánh dấu `from_cache: 'rule_files'`.
- Không dùng lại nếu: verdict UNKNOWN, rule cross-flow, thiếu danh sách file, hoặc bất kỳ file đổi/mất.
- UI: hiện "dùng lại vì code liên quan không đổi".
- Test: hai workspace khác nhau một file không liên quan → reuse; đổi file trong evidence → chạy lại.
- Rủi ro: AI kết luận dựa vào file không nằm trong evidence/trace → chỉ lấy file từ trace `source_read` + evidence; ghi rõ giới hạn trong README.

**Task 2.4 — Bản đồ luồng quảng cáo dựng sẵn**
- `apk_audit/source_index.py`: hàm `ad_flow_map(facts, inventory)` tất định: Activity của 4 màn (manifest + tên), file/dòng các lời gọi `load*`/`show*`/`getShouldDisplay*`/`setOnAdminAdToggleListener`, file chứa `ad_config` loader. Gắn vào context mỗi rule thay cho phần trùng của `evidence_bundle` (≤ 4KB).
- Đo: số tool call trung bình mỗi rule trước/sau trên dữ liệu chuẩn.

Chấp nhận: lượt đầu ≤ 180s; audit lại cùng APK với một file không liên quan đổi chỉ gọi AI cho rule bị ảnh hưởng.

---

## Giai đoạn 3 — Ít token hơn

**Task 3.1 — Cắt context gửi AI**
- `source_index.bundle(max_chars=20000)` → tham số theo rule (`rule.budget.context_chars`, mặc định 12000); bỏ snippet đã có trong `ad_flow_map`.
- `base-reference.json`: gửi `static_goal`, `required_paths`, `caveats` + tối đa 2 snippet ngắn nhất thay vì toàn bộ (giảm 12–17KB còn ≤ 6KB).
- Đo bằng replay (không gọi AI) như đã làm: tổng prompt 11 rule trước/sau.

**Task 3.2 — Giới hạn đầu ra**
- `AUDIT_PROMPT`: 6–12 evidence, reasoning tối đa ~8 dòng; schema giữ nguyên. Kiểm không tăng `unverified_*`.

**Task 3.3 (tùy chọn, cần người dùng duyệt) — Model theo độ khó rule**
- `rule.budget.model_tier: light|standard`; light chạy Haiku cho rule đơn giản (FIREBASE_EVENTS, BANNER_RELOAD) nếu người dùng đồng ý; còn lại Sonnet. Mặc định tắt.

Chấp nhận: token giảm ≥ 40% so với mốc Giai đoạn 0, PASS/FAIL không giảm, UNKNOWN không tăng.

---

## Kiểm tra cuối và bàn giao
1. `uv run python -m unittest discover -s tests` đạt toàn bộ.
2. `cd frontend && npm run build` đạt; xem trực quan 2 tab trên trình duyệt.
3. `apk-audit rules check` đạt (pack 0.6.0).
4. Chạy lại script đo của Giai đoạn 0 trên dữ liệu chuẩn; ghi bảng trước/sau vào `docs/audit-optimization-validation.md`.
5. Cập nhật README (tab Dev/MKT, xuất HTML/CSV, cache theo file, rule tĩnh mới) và `SESSION_LOG.md`.
6. Restart server khi không có job chạy; hỏi người dùng trước khi commit/push.

## Thứ tự thực hiện
0.1 → 0.2 (đo) → 1.1–1.5 → 2.1 → 2.2 → 2.3 → 2.4 → 3.1 → 3.2 → đo lại → (3.3 nếu được duyệt).
