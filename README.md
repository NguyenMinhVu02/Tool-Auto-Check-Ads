# apk-audit

Khung CLI audit APK theo thiết kế v2. Bộ luật mặc định hiện chứa chuẩn **logic ads/init** rút từ `Example-AdLogic-Partner` tại commit `e8f4337` (xem [hợp đồng tham chiếu](docs/base-ads-contract.md)). Các luật logic ở chế độ `agent`; `--engine none` trả `UNKNOWN`, không xác nhận app đạt chuẩn. ID ads của base không dùng làm ID kỳ vọng cho app đối tác.

## Chạy ngay

```bash
cd /home/infinity01/Tools/apk-audit
uv sync --extra mcp
uv run apk-audit --help
uv run apk-audit doctor
uv run apk-audit examples/workspace --out out/demo --engine none
```

Kết quả: `out/demo/facts.json`, `xref_index.json`, `report.md`, `report.json`.
Workspace mẫu chỉ chứa dữ liệu minh họa, không phải APK/app thật.

## Web localhost

```bash
uv run apk-audit serve
```

Mở `http://127.0.0.1:8765` rồi kéo APK, XAPK hoặc APKM vào vùng tải lên. Trang gọi pipeline hiện có, lưu file đã tải và báo cáo dưới `out/web/`, sau đó hiển thị tổng quan và từng luật. Server chỉ lắng nghe trên `127.0.0.1`, xử lý một file tại một thời điểm; dùng `Ctrl+C` để dừng. Có thể đổi cổng/thư mục bằng `--port` và `--out`, hoặc trỏ bộ luật bằng `--rules`.

Đây là khung web có luồng upload và báo cáo thật. Engine mặc định vẫn là `none`: 10 luật logic hiện trả `UNKNOWN` cho đến khi có bộ chấm logic live. File cần `jadx` và Java như CLI. Trang chỉ nhận file có đuôi `.apk`, `.xapk`, `.apkm`; nội dung archive vẫn được kiểm tra trước khi giải mã.

Đọc APK có sẵn (cần Java và jadx trên PATH, hoặc biến `JADX_PATH`):

```bash
uv run apk-audit /path/to/app.apk --out out/app --engine none
uv run apk-audit /path/to/app.xapk --out out/app --engine none
uv run apk-audit facts /path/to/app.apk
```

Tool gọi jadx trên bản gốc chỉ để đọc. XAPK/APKM được kiểm tra đường dẫn ZIP rồi đưa tất cả APK con cho jadx. Không cài/chạy app. Workspace bung lưu theo SHA256 trong cache; `--no-cache` tạo lượt bung mới. Mặc định cache lấy từ `platformdirs`; `--cache-dir` cho phép đổi vị trí.

Có thể truyền thẳng thư mục jadx đã bung. `--out` phải nằm ngoài thư mục đầu vào để không sửa dữ liệu đang phân tích.

## Chuẩn ads/init hiện có và cách bổ sung

Chỉnh ba nơi trong `rulepacks/default/`:

1. `context.md`: kiến trúc và luồng tham chiếu từ base; bổ sung khi base đổi logic.
2. `extract.yaml`: regex chuỗi cần tìm và tiền tố package cần thống kê.
3. `rules/*.yaml`: 10 câu hỏi logic hoặc các luật static bổ sung.

Từ thư mục dự án, tool tự nạp `rulepacks/default/`. Khi chạy ở nơi khác, truyền đường dẫn tuyệt đối bằng `--rules`. Nếu không tìm thấy bộ mặc định, dùng bộ rỗng có cảnh báo; đường dẫn `--rules` sai sẽ báo lỗi. Muốn đối chiếu ID thật cần tài liệu ADS SCRIPTS riêng của app qua `--ads-scripts`; muốn đối chiếu package/tokens cần working checklist qua `--checklist`. Bộ khung hiện chỉ đọc JSON object hoặc CSV `key,value`, và chưa có adapter AI live để tự chấm 10 luật logic.

```bash
uv run apk-audit rules check --rules rulepacks/default
uv run apk-audit rules list --rules rulepacks/default
uv run apk-audit examples/workspace --rules rulepacks/default --out out/demo
```

Mỗi file luật là một **danh sách YAML**. Ví dụ tổng quát bên dưới chỉ minh họa cú pháp, không phải chuẩn quảng cáo:

```yaml
- id: EXAMPLE_CONFIG
  title: Đối chiếu giá trị cấu hình
  mode: static
  area: configuration
  check: manifest_meta
  params:
    key: example.config
    equals: expected-value
  on_missing: unknown
  hint: Xem resources/AndroidManifest.xml
```

Bảy phép kiểm tra tổng quát:

| check | params bắt buộc | So sánh |
|---|---|---|
| `manifest_meta` | `key` | `equals`, `equals_doc` hoặc `regex` |
| `manifest_has` | `collection`, `name` | Tên component có mặt |
| `string_present` | `key` | Candidate có mặt; lọc thêm `equals`/`regex` |
| `string_absent` | `key` | Candidate không có mặt; lọc thêm `equals`/`regex` |
| `asset_json_path` | `file`, `path` | Đường dẫn có giá trị, kể cả `false` |
| `asset_json_match` | `file`, `path` | `equals`, `equals_doc` hoặc `regex` |
| `sdk_version` | `key`, `min` | So phiên bản số; extractor SDK chưa nối nên mặc định UNKNOWN |

`key` của string là tên trong `extract.yaml:string_patterns`.
`file` của JSON là tên tương đối bên trong assets, ví dụ `config.json`.
JSONPath hỗ trợ `$.a.b`, `items[0].id`, `["key.with.dots"]`; chưa hỗ trợ wildcard/filter.
Toàn bộ JSON assets được đọc; `asset_json` được giữ trong cấu trúc extract để mở rộng chọn lọc sau.
Chuỗi hiện lấy từ text đã decode, chưa phải DEX string pool. Các trường SDK/ID chuyên biệt giữ trống; không suy đoán nghiệp vụ.

Luật agent khai báo `question`, `verdict.pass_when`, `verdict.fail_when`, `verdict.unknown_when`, `start_hints`, `budget.max_tool_calls`. Viết các tiêu chí dạng chuỗi (đặt dấu nháy nếu là `yes/no`). Dùng `--engine none` sẽ trả UNKNOWN với lý do engine_disabled.

Tài liệu đầu vào hỗ trợ JSON object hoặc CSV **key,value** qua `--ads-scripts` / `--checklist`; đối chiếu bằng `equals_doc: ads_scripts.some_key`. Chưa đọc URL Google Sheets. Thiếu key/tài liệu trả SKIPPED.

## MCP chỉ đọc

```bash
uv run apk-audit mcp --workspace /absolute/path/to/jadx-workspace
```

Chín tool: `get_facts`, `list_classes`, `search_classes`, `get_class`, `get_smali`, `get_methods`, `xrefs_to`, `grep`, `read_lines`.
`get_facts` giới hạn phản hồi 64 KiB; cần truyền `path` hẹp hơn khi vượt giới hạn.
`xrefs_to` dùng `method` hoặc `class_name`, dựa trên chỉ mục lệnh invoke smali. Thiếu smali trả `available: false`; không coi là không có lời gọi. `get_methods` chỉ nhận dạng khai báo Java theo mẫu, không phải parser hoàn chỉnh.

Cấu hình MCP cho client dùng JSON:

```json
{
  "mcpServers": {
    "apk_audit": {
      "command": "/absolute/path/to/apk-audit/.venv/bin/python",
      "args": ["-m", "apk_audit", "mcp", "--workspace", "/absolute/path/to/workspace"]
    }
  }
}
```

Windows dùng `.venv/Scripts/python.exe`. Server không chỉnh cấu hình toàn cục của client. Cách đăng ký tool và chạy stdio theo [tài liệu FastMCP](https://gofastmcp.com/deployment/running-server).

## Chỗ nối tích hợp

- `fetch.py:DownloadProvider`: adapter tải APK. Hiện link Play được parse package, rồi báo rõ chưa nối provider. Không scrape giả hoặc vượt CAPTCHA.
- `engines.py:Engine`: nhận prompt, bộ tools, ngân sách; trả `AgentResult`. Có `none` và `replay` để kiểm thử. `ClaudeEngine`/`CodexEngine` là điểm mở rộng chưa kích hoạt.
- `agent.py`: dựng prompt, thử lại JSON hỏng một lần, kiểm tra ID/status/ngân sách, mở file xác minh evidence. FAIL thiếu bằng chứng hợp lệ trở thành UNKNOWN.
- `verdict_cache.py`: khóa gồm APK/workspace, nội dung pack/context, luật, engine, tài liệu và phiên bản tool. Cache lưu prompt và trace. Adapter live sau này phải đếm/chặn tool call thật; bản khung chỉ xác nhận số được adapter báo.
- `unpack.py`: nhận dữ liệu jadx, lưu mã thoát và log. Chưa nối baksmali; có thể cung cấp workspace đã có thư mục `smali/`.
- `apk_audit.run(...)`: API chung cho CLI và các cửa vào tương lai.

Chưa triển khai: tải tự động apkcombo/apkpure, lấy version từ Play, AI live, nhóm phiên theo area/chạy song song, quan sát ngoài bộ luật từ AI, `ask` và skill `/audit-play`. Web localhost đã có giao diện/upload/báo cáo, nhưng chưa có engine chấm logic live. Mã thoát 0 chỉ nghĩa không có FAIL, không bảo đảm mọi luật PASS.

## Kiểm thử

```bash
uv run --extra mcp python -m unittest discover -s tests -v
```

Kiểm thử trên workspace giả lập, static checks, cache, evidence, path traversal, CLI và MCP. Đã chạy 16 kiểm thử trên Linux và smoke test jadx với gói APK thử nghiệm chỉ chứa manifest/assets. MCP stdio được kiểm tra ngoài sandbox vì sandbox phiên này gây timeout pipe. Chưa xác nhận audit đầu-cuối trên APK thương mại hoặc trên Windows/macOS.

Thư viện được khóa trong `uv.lock`. Thiết kế gốc: `docs/2026-09-10-apk-audit-design.md`; phạm vi bản khung: `docs/implementation-plan.md`.
