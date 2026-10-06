# apk-audit

Khung CLI audit APK theo thiết kế v2. Bộ luật mặc định hiện chứa chuẩn **logic ads/init** rút từ `Example-AdLogic-Partner` tại commit `e8f4337` (xem [hợp đồng tham chiếu](docs/base-ads-contract.md)). Mặc định Codex CLI dùng `gpt-6-luna` đọc workspace đã giải mã và đánh giá 10 luật logic; cần cài và đăng nhập Codex CLI. `--engine none` tắt AI và trả `UNKNOWN`. ID ads của base không dùng làm ID kỳ vọng cho app đối tác.

## Chạy ngay

```bash
cd /home/infinity01/Tools/apk-audit
uv sync --extra mcp
uv run apk-audit --help
uv run apk-audit doctor
codex login status
uv run apk-audit examples/workspace --out out/demo
```

Kết quả: `out/demo/facts.json`, `xref_index.json`, `report.md`, `report.json`.
Workspace mẫu chỉ chứa dữ liệu minh họa, không phải APK/app thật.

## Web localhost

```bash
uv run apk-audit serve
```

Mở `http://127.0.0.1:8765`, chọn hoặc kéo APK/XAPK/APKM vào vùng tải lên, rồi bấm **Bắt đầu kiểm tra**. Chọn file không tự chạy. Hai ô ADS SCRIPTS và working file là tùy chọn: chỉ khi chọn **đủ cả hai**, web mới đưa chúng vào pipeline; thiếu một file thì bỏ qua cả cặp. Mỗi tài liệu nhận JSON object hoặc CSV hai cột `key,value`, tối đa 5 MiB. Web dùng font Poppins lưu sẵn trong gói để chạy offline; giấy phép ở `apk_audit/web_assets/fonts/OFL.txt`.

Trang lưu file đã tải và báo cáo dưới `out/web/`, sau đó hiển thị tổng quan và từng luật. Khi chạy, web hiển thị bước hiện tại: tiếp nhận, giải mã, trích xuất dữ liệu, đối chiếu quy tắc, ghi báo cáo. Trình duyệt hỏi xác nhận nếu đóng tab, Back hoặc Reload trong lúc lượt kiểm tra đang chạy. Nếu vẫn Reload, trang lấy lại trạng thái lượt kiểm tra từ server. Việc tiếp tục hiển thị này chỉ hoạt động khi server chưa khởi động lại; job hiện được giữ trong bộ nhớ server. Server chỉ lắng nghe trên `127.0.0.1`, xử lý một file tại một thời điểm; dùng `Ctrl+C` để dừng. Có thể đổi cổng/thư mục bằng `--port` và `--out`, hoặc trỏ bộ luật bằng `--rules`.

Giao diện dùng React và các component Ant Design; font Poppins được phục vụ từ gói local. Mã frontend nằm trong `frontend/`, bản build phục vụ offline nằm trong `apk_audit/web_assets/`. Sau khi sửa frontend, chạy `cd frontend && npm ci && npm run build`; người dùng web không cần cài Node.js. Web mặc định chạy Codex CLI với model `gpt-6-luna` cho mọi luật agent sau khi jadx giải mã. Codex chạy phiên chỉ đọc cho từng luật, có giới hạn thời gian và số lần gọi công cụ; tool kiểm tra lại file/dòng trước khi nhận `PASS` hoặc `FAIL`. Nội dung mã và tài liệu cần thiết được gửi tới model qua Codex; lượt audit có thể dùng quota/tính phí theo tài khoản. Nếu thiếu bằng chứng hoặc Codex lỗi, luật trả `UNKNOWN`. File cần `jadx` và Java như CLI. Trang chỉ nhận file có đuôi `.apk`, `.xapk`, `.apkm`; nội dung archive vẫn được kiểm tra trước khi giải mã.

Đọc APK có sẵn (cần Java và jadx trên PATH, hoặc biến `JADX_PATH`):

```bash
uv run apk-audit /path/to/app.apk --out out/app
uv run apk-audit /path/to/app.xapk --out out/app
uv run apk-audit facts /path/to/app.apk
```

Tool gọi jadx trên bản gốc chỉ để đọc. XAPK/APKM được kiểm tra đường dẫn ZIP rồi đưa tất cả APK con cho jadx. Không cài/chạy app. Workspace bung lưu theo SHA256 trong cache; `--no-cache` tạo lượt bung mới. Mặc định cache lấy từ `platformdirs`; `--cache-dir` cho phép đổi vị trí.

Có thể truyền thẳng thư mục jadx đã bung. `--out` phải nằm ngoài thư mục đầu vào để không sửa dữ liệu đang phân tích.

## Chuẩn ads/init hiện có và cách bổ sung

Chỉnh ba nơi trong `rulepacks/default/`:

1. `context.md`: kiến trúc và luồng tham chiếu từ base; bổ sung khi base đổi logic.
2. `extract.yaml`: regex chuỗi cần tìm và tiền tố package cần thống kê.
3. `rules/*.yaml`: 10 câu hỏi logic hoặc các luật static bổ sung.

Từ thư mục dự án, tool tự nạp `rulepacks/default/`. Khi chạy ở nơi khác, truyền đường dẫn tuyệt đối bằng `--rules`. Nếu không tìm thấy bộ mặc định, dùng bộ rỗng có cảnh báo; đường dẫn `--rules` sai sẽ báo lỗi. Muốn đối chiếu ID thật cần tài liệu ADS SCRIPTS riêng của app qua `--ads-scripts`; muốn đối chiếu package/tokens cần working checklist qua `--checklist`. Tài liệu hỗ trợ JSON object hoặc CSV `key,value`; Codex đánh giá logic và dẫn bằng chứng từ workspace.

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
- `engines.py:Engine`: nhận prompt, bộ tools, ngân sách; trả `AgentResult`. `CodexEngine` gọi Codex CLI với `gpt-6-luna`, phiên chỉ đọc và đầu ra JSON có schema; `none` và `replay` dùng cho kiểm thử/offline. `ClaudeEngine` chưa nối.
- `agent.py`: dựng prompt, thử lại JSON hỏng một lần, kiểm tra ID/status/ngân sách, mở file xác minh evidence. PASS/FAIL thiếu bằng chứng hợp lệ trở thành UNKNOWN.
- `verdict_cache.py`: khóa gồm APK/workspace, nội dung pack/context, luật, engine, tài liệu và phiên bản tool. Cache lưu prompt và trace. Codex đếm lời gọi công cụ từ event JSONL và dừng khi quá ngân sách.
- `unpack.py`: nhận dữ liệu jadx, lưu mã thoát và log. Chưa nối baksmali; có thể cung cấp workspace đã có thư mục `smali/`.
- `apk_audit.run(...)`: API chung cho CLI và các cửa vào tương lai.

Chưa triển khai: tải tự động apkcombo/apkpure, lấy version từ Play, nhóm phiên theo area/chạy song song, quan sát ngoài bộ luật từ AI, `ask` và skill `/audit-play`. Chưa kiểm định chất lượng verdict với APK đối tác thực tế. Mã thoát 0 chỉ nghĩa không có FAIL, không bảo đảm mọi luật PASS.

## Kiểm thử

```bash
uv run --extra mcp python -m unittest discover -s tests -v
```

Kiểm thử trên workspace giả lập, static checks, cache, evidence, path traversal, CLI, web và MCP. Đã chạy 24 kiểm thử trên Linux và một rule bằng Codex CLI `gpt-6-luna` trên workspace mẫu. MCP stdio và web được kiểm tra ngoài sandbox vì sandbox chặn socket localhost. Chưa xác nhận audit đầu-cuối trên APK đối tác thực tế hoặc trên Windows/macOS.

Thư viện được khóa trong `uv.lock`. Thiết kế gốc: `docs/2026-09-10-apk-audit-design.md`; phạm vi bản khung: `docs/implementation-plan.md`.
