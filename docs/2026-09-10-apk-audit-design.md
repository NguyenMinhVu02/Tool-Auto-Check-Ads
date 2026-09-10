# apk-audit — Thiết kế và hướng dẫn triển khai

**Phiên bản:** 2.0 · **Ngày:** 2026-09-10 · **Trạng thái:** Bản thiết kế, chưa triển khai

> **Thay đổi so với 1.0:** AI trở thành thành phần chính thay vì phụ trợ. Công cụ
> dựng một MCP server chạy nền trên thư mục đã bung, AI tự tìm tự đào qua bộ
> tool đó. `facts.json` không còn là bữa ăn dọn sẵn mà là **chỉ mục khởi đầu**.
> Tính lặp lại của audit được giữ bằng **cache phán quyết**, không phải bằng
> cách hạn chế AI. Xem mục 2.4 và mục 7.

Tài liệu này mô tả **khung** của công cụ. Bộ luật cụ thể về quảng cáo (thứ tự
khởi tạo, quy tắc gắn placement, luồng show interstitial…) **không** nằm trong
tài liệu này — nó là dữ liệu đầu vào, được lấy từ dự án mẫu và nạp vào lúc chạy.
Xem mục 5.

---

## 1. Mục tiêu

Dán một link Google Play, nhận về báo cáo đối chiếu cách app đó tích hợp quảng
cáo với chuẩn của dự án mẫu.

Thay thế quy trình thủ công hiện tại: mở link Play → tải APK từ apkcombo → mở
jadx-gui → tìm chỗ khởi tạo quảng cáo → so bằng mắt với base → ghi tay chỗ sai.

### Trong phạm vi

- Phân giải link Play thành package name và phiên bản
- Tải APK/XAPK và lưu cache
- Bung code bằng jadx
- Dựng chỉ mục khởi đầu (`facts.json`) từ những nguồn R8 không đụng tới
- Cung cấp một MCP server chạy nền trên thư mục đã bung
- Để AI (`claude` hoặc `codex`) tự đào qua MCP và kết luận từng luật
- Kết xuất báo cáo cho người và cho máy

### Ngoài phạm vi

- Sửa code app đối tác
- Cài, chạy, hoặc phân tích động (Frida, emulator, adb install)
- Upload APK lên bất kỳ dịch vụ nào
- Bỏ qua bảo vệ bản quyền hay giải mã APK đã bị mã hóa
- Giao diện đồ họa ở giai đoạn đầu (xem mục 12, cột mốc M7)

---

## 2. Nguyên tắc thiết kế

Năm nguyên tắc dưới đây quyết định gần như toàn bộ cấu trúc code. Khi phân vân
lúc triển khai, quay lại đây.

### 2.1. Chia luật theo chi phí, không theo sở thích

Mỗi luật đi một trong hai đường:

- **`static`** — dữ liệu cần thiết nằm sẵn trong `facts.json`, so sánh là xong.
  Vài mili giây, không tốn token, kết quả tuyệt đối ổn định. Dùng cho: ID, token,
  khóa cấu hình, phiên bản SDK, sự có mặt của màn hình.
- **`agent`** — cần hiểu code, cần lần theo lời gọi, cần đọc qua lớp làm rối.
  AI tự đào qua MCP. Dùng cho: thứ tự khởi tạo, luồng preload/load/show, cổng
  kiểm tra, cấu trúc Activity vs Fragment.

Không có luật nào phải chọn đường vì "AI xịn hơn" hay "code an toàn hơn". Chọn
theo: **dữ liệu có sẵn trong `facts.json` không?** Có thì `static`, không thì
`agent`.

Đây là điều chỉnh lớn nhất so với bản 1.0. Bản cũ đẩy gần hết sang `static` rồi
mới nhờ AI vá chỗ thủng. Bản này để AI cầm hẳn phần code, và chỉ giữ `static`
cho phần AI làm cũng được nhưng tốn tiền vô ích.

### 2.2. `facts.json` là chỉ mục, không phải bữa ăn

Vẫn giữ, nhưng đổi vai. Nó không còn phải mô tả đầy đủ mọi thứ trong APK. Nó chỉ
cần chứa những gì **R8 không đụng tới** và **AI sẽ phải hỏi ngay trong ba lượt
đầu**:

- `AndroidManifest.xml` đã parse
- Nội dung các file JSON trong `assets/`
- Kho chuỗi ký tự đã lọc theo mẫu
- Tên lớp Application và đường dẫn file của nó
- Danh sách màn hình

Lợi ích: AI gọi `get_facts()` một lượt là có ngay nền tảng, khỏi đào lại thứ đã
biết. Và phần `static` vẫn chấm được mà không cần đánh thức AI.

Cái bị cắt so với bản 1.0: `code.py` không còn phải dựng cây lời gọi, không phải
lần xref. Đó là phần khó nhất và tốn công nhất — giờ giao cho AI qua tool
`xrefs_to` và `get_smali`. **Riêng cắt này đã giảm khoảng một phần ba khối lượng
code phải viết.**

### 2.3. Ba trạng thái, không phải hai

`PASS` / `FAIL` / `UNKNOWN`. APK trên Play đã qua R8 nên có thứ **không ai** biết
chắc — kể cả AI. `UNKNOWN` là kết quả hợp lệ, không phải lỗi.

**Cấm đoán bừa.** Công cụ kiểu này chết vì báo sai oan: vài lần là người dùng hết
tin rồi bỏ. Mỗi `UNKNOWN` phải kèm gợi ý cụ thể (tên file, số dòng) để người mở
jadx-gui xem tay.

Với luật `agent`, "tôi không kết luận được" là câu trả lời được chấp nhận và
được tính là làm đúng việc. Prompt phải nói rõ điều này, nếu không AI sẽ có xu
hướng cố nặn ra một kết luận.

### 2.4. Tính lặp lại đến từ cache, không từ việc trói AI

Audit cần chạy hai lần ra cùng kết quả. Cần: sửa luật rồi chạy lại 20 app cũ,
biết chắc thay đổi là do luật chứ không phải do AI hôm nay nghĩ khác.

Cách giữ điều đó mà vẫn để AI tự do: **cache phán quyết theo khóa**

```
khóa = sha256(APK) + rule_id + phiên bản rule pack + tên engine
```

Chạy lần đầu tốn AI. Mọi lần sau đọc cache, ra kết quả giống hệt, không tốn
token. Đổi luật → khóa đổi → chỉ luật đó chạy lại. Ép chạy lại bằng `--refresh`.

Cache lưu cả **nhật ký hội thoại**: AI gọi tool nào, nhận gì, kết luận vì sao.
Nghi ngờ một finding thì mở nhật ký ra xem AI đã đi đường nào — đây là thứ mà
audit thuần AI không có, và là lý do có thể tin được kết quả để mang đi làm việc
với đối tác.

### 2.5. AI được đào tự do, nhưng bị chặn ở đúng hai chỗ

Không giới hạn AI gọi tool nào, đọc file nào, đi bao nhiêu lượt. Nhưng:

1. **`FAIL` phải kèm bằng chứng** — ít nhất một mục có file và số dòng, và số
   dòng đó phải tồn tại thật (công cụ kiểm tra lại). Không có bằng chứng thì hạ
   xuống `UNKNOWN`.
2. **Chỉ trả lời đúng luật được hỏi** — AI không được tự sinh finding mới trộn
   vào danh sách chấm. Thứ nó phát hiện thêm đi vào mục **Quan sát ngoài bộ
   luật** ở cuối báo cáo, không tính vào tổng đạt/sai.

Mục quan sát này thực ra rất có giá trị: nó chính là nguồn để bạn bổ sung luật
mới cho rule pack. Nhưng phải tách khỏi phần chấm điểm.

---

## 3. Kiến trúc

### 3.1. Dây chuyền

```
Link Play
   │ 1. resolve    playstore.py     ── không mạng ngoài trang Play
   ▼
package + version
   │ 2. fetch      fetch.py         ── bước DUY NHẤT chạm Internet
   ▼
file .apk / .xapk (cache)
   │ 3. unpack     unpack.py        ── bước DUY NHẤT chạm jadx
   ▼
thư mục workspace  ◄──────────────┐
   │ 4. facts      facts.py        │  mcp_server.py phục vụ tool
   ▼                               │  trên chính thư mục này
facts.json ──────────────────────┐ │
   │ 5. static     rules/         │ │
   ▼                             │ │
findings (phần static)           │ │
   │ 6. agent      agent.py ──────┴─┘  AI tự đào qua MCP
   ▼
findings (đầy đủ) + observations
   │ 7. report     report.py
   ▼
report.md + report.json + trace/
```

Khác bản 1.0: bước 6 không còn là "vá chỗ thủng". Nó là vòng lặp agent, và nó
chạm ngược vào workspace ở bước 3 thông qua MCP server.

### 3.2. Bố cục repo

```
apk-audit/
├─ pyproject.toml              # quản lý bằng uv, entry point `apk-audit`
├─ README.md
├─ docs/
│  └─ 2026-09-10-apk-audit-design.md      # tài liệu này
├─ apk_audit/
│  ├─ __init__.py
│  ├─ cli.py                   # phân tích tham số, điều phối các bước
│  ├─ config.py                # đường dẫn cache, dò jadx/claude/codex
│  ├─ playstore.py             # bước 1
│  ├─ fetch.py                 # bước 2
│  ├─ unpack.py                # bước 3
│  ├─ facts/
│  │  ├─ __init__.py           # điều phối, ghép facts.json
│  │  ├─ manifest.py           # AndroidManifest
│  │  ├─ assets.py             # assets/, res/
│  │  └─ strings.py            # kho chuỗi ký tự
│  ├─ mcp_server.py            # MCP chạy nền trên workspace  ★ mới
│  ├─ tools.py                 # cài đặt từng tool, dùng chung cho MCP
│  ├─ rules/
│  │  ├─ __init__.py
│  │  ├─ loader.py             # nạp và kiểm tra bộ luật YAML
│  │  ├─ checks.py             # cài đặt các kiểu luật static
│  │  └─ engine.py             # chạy phần static, sinh findings
│  ├─ agent.py                 # vòng lặp agent cho luật mode: agent  ★ mới
│  ├─ engines.py               # adapter claude / codex
│  ├─ verdict_cache.py         # cache phán quyết + nhật ký  ★ mới
│  ├─ report.py                # bước 7
│  └─ contracts.py             # dataclass cho facts / finding / rule
├─ rulepacks/
│  └─ .gitkeep                 # bộ luật lấy từ dự án mẫu, đặt vào đây
└─ tests/
   ├─ fixtures/
   │  ├─ facts/                # facts.json mẫu, test phần static
   │  ├─ traces/               # nhật ký agent đã ghi, để phát lại
   │  └─ apks/                 # 1-2 APK nhỏ để test đầu-cuối
   └─ ...
```

### 3.3. Ba cửa vào, một lõi

Lõi là hàm `apk_audit.run(...)`. Ba cửa vào đều gọi nó:

1. **Dòng lệnh** — `apk-audit "<link>"`. Làm trước, bắt buộc.
2. **Skill trong Claude/Codex** — `/audit-play <link>`. Vỏ mỏng ~30 dòng: chạy
   CLI, đọc `report.json`, tóm tắt. Giá trị nằm ở chỗ hỏi tiếp bằng lời sau đó.
3. **Web tại máy** — `apk-audit serve` → `localhost:8765`. Làm sau cùng.

---

## 4. Hợp đồng dữ liệu: `facts.json`

Chỉ mục khởi đầu. Chứa những gì R8 không đụng tới, cộng vài thứ AI sẽ hỏi ngay.

Nguyên tắc: trung tính tuyệt đối. Không có trường nào tên là `is_valid`,
`compliant`, `error`. Chỉ ghi lại sự thật đọc được.

```jsonc
{
  "schema_version": 2,
  "generated_at": "2026-09-10T09:14:22Z",
  "tool_versions": { "apk_audit": "0.1.0", "jadx": "1.5.6" },

  "source": {
    "play_url": "https://play.google.com/store/apps/details?id=com.foo.bar",
    "package": "com.foo.bar",
    "version_name": "2.4.1",
    "version_code": 241,
    "download_source": "apkcombo",
    "file_name": "com.foo.bar-2.4.1.apk",
    "file_size": 44040192,
    "sha256": "…",                  // đồng thời là khóa cache phán quyết
    "is_split": false,
    "split_names": []
  },

  "workspace": {
    "root": "/home/…/cache/com.foo.bar/2.4.1/workspace",
    "sources_dir": "sources",
    "smali_dir": "smali",
    "resources_dir": "resources",
    "file_count": 6812
  },

  "manifest": {
    "package": "com.foo.bar",
    "min_sdk": 24,
    "target_sdk": 34,
    "application_class": "com.foo.bar.App",
    "application_file": "sources/com/foo/bar/App.java",   // AI nhảy thẳng vào
    "permissions": ["android.permission.INTERNET", "…"],
    "meta_data": {
      "com.google.android.gms.ads.APPLICATION_ID": "ca-app-pub-1234~5678"
    },
    "activities": [
      {
        "name": "com.foo.bar.ui.SplashActivity",
        "file": "sources/com/foo/bar/ui/SplashActivity.java",
        "exported": true,
        "is_launcher": true
      }
    ],
    "services": [], "receivers": [], "providers": []
  },

  "assets": {
    "files": [ { "path": "assets/ad_config.json", "size": 4821, "sha256": "…" } ],
    // JSON trong assets parse nguyên vẹn. Nguồn giàu nhất vì R8 không đụng assets.
    "json": {
      "ad_config.json":       { "…": "nội dung gốc" },
      "ad_config_debug.json": { "…": "nội dung gốc" }
    }
  },

  "strings": {
    "admob_app_ids":  [ { "value": "ca-app-pub-1234~5678", "source": "manifest" } ],
    "ad_unit_ids":    [ { "value": "ca-app-pub-1234/9999", "source": "assets/ad_config.json" } ],
    "sdk_versions":   { "play_services_ads": "23.1.0" },
    "candidates": {
      "adjust_token":          [ { "value": "abc123", "source": "dex_string_pool" } ],
      "facebook_client_token": [],
      "tiktok_token":          [],
      "remote_config_keys":    [ { "value": "ad_remote_config", "source": "dex_string_pool" } ]
    }
  },

  "code_index": {
    "obfuscated": true,
    "obfuscation_ratio": 0.87,          // tỉ lệ tên class 1-2 ký tự
    "class_count": 6812,
    // Chỉ đánh dấu các gói SDK nhận ra được, để AI biết chỗ nào đáng đào
    "known_packages": [
      { "prefix": "com.google.android.gms.ads", "class_count": 412, "obfuscated": false },
      { "prefix": "com.itg", "class_count": 88, "obfuscated": false },
      { "prefix": "com.foo.bar", "class_count": 1204, "obfuscated": true }
    ]
  }
}
```

### Quy tắc bắt buộc

1. Không trường nào mang ý nghĩa đúng/sai.
2. Không suy diễn. Không đọc được thì để trống, không đoán.
3. Mọi đường dẫn file phải tương đối so với `workspace.root`, để AI dùng thẳng
   làm tham số cho tool.
4. `schema_version` tăng khi đổi cấu trúc; loader của rule pack kiểm tra số này.
5. File phải đọc được bằng mắt.

---

## 5. Bộ luật (rule pack) — phần lấy từ dự án mẫu

**Đây là chỗ toàn bộ kiến thức về quảng cáo được cắm vào.** Công cụ không chứa
sẵn luật nào; nó nạp từ `--rules <thư mục>` (mặc định `rulepacks/default/`).

Quy trình lấy luật từ dự án mẫu:

1. Đọc dự án mẫu, liệt kê từng quy tắc
2. Với mỗi quy tắc, hỏi: *"dữ liệu để chấm nó có nằm sẵn trong `facts.json` không?"*
3. Có → viết luật `mode: static`
4. Không → viết luật `mode: agent`, mô tả bằng lời cho AI đi tìm

### 5.1. Cấu trúc thư mục rule pack

```
rulepacks/default/
├─ pack.yaml            # metadata: tên, phiên bản, schema_version yêu cầu
├─ extract.yaml         # khai báo cho bước 4: cần rút thêm gì khỏi APK
├─ context.md           # bối cảnh chung nạp vào mọi prompt agent  ★ mới
└─ rules/
   ├─ 010-identity.yaml
   ├─ 020-init.yaml
   ├─ 030-placements.yaml
   ├─ 040-flow.yaml
   └─ 050-screens.yaml
```

### 5.2. `extract.yaml` — dạy bước 4 cần tìm gì

```yaml
schema_version: 2

# Mẫu nhận dạng chuỗi, kết quả đổ vào strings.candidates
string_patterns:
  admob_unit_id:  '^ca-app-pub-\d+/\d+$'
  admob_app_id:   '^ca-app-pub-\d+~\d+$'
  adjust_token:   '^[a-z0-9]{12}$'
  remote_config:  '^ad_remote_config$'

# File cấu hình trong assets cần parse
asset_json:
  - assets/ad_config.json
  - assets/ad_config_debug.json

# Tiền tố gói cần đánh dấu trong code_index
known_packages:
  - com.google.android.gms.ads
  - com.itg
```

So với bản 1.0, mục `sdk_entrypoints` bị bỏ — AI tự tìm bằng tool `xrefs_to`.

### 5.3. `context.md` — bối cảnh chung cho agent

Một file Markdown mô tả kiến trúc chuẩn của dự án mẫu bằng lời: SDK nào, lớp nào
làm gì, luồng chuẩn ra sao, thuật ngữ riêng. Nạp vào **mọi** prompt agent làm nền.

Đây là chỗ đắt giá nhất của cả rule pack. AI có bối cảnh này thì đọc code làm rối
nhanh hơn hẳn, vì nó biết đang tìm cái gì thay vì mò từ đầu.

Giữ dưới khoảng 2000 từ. Dài quá thì tốn token mỗi lượt gọi mà không thêm giá trị.

### 5.4. Luật `mode: static`

```yaml
- id: ID_ADMOB_APP_ID
  title: AdMob APP ID trong manifest khớp tài liệu
  mode: static
  severity: high
  area: identity
  check: manifest_meta
  params:
    key: com.google.android.gms.ads.APPLICATION_ID
    equals_doc: ads_scripts.admob_app_id      # cần tài liệu, thiếu thì SKIPPED
  on_missing: unknown          # unknown (mặc định) | pass | fail
  hint: Xem meta-data trong AndroidManifest.xml
```

Các kiểu `check` cần cài đặt:

| `check` | Đọc gì trong facts | Dùng cho |
|---|---|---|
| `manifest_meta` | `manifest.meta_data[key]` | AdMob APP ID, cờ cấu hình |
| `manifest_has` | `manifest.activities/services/...` | Màn hình bắt buộc có mặt |
| `string_present` | `strings.candidates[*]` | Token Adjust/Facebook/TikTok, khóa Remote Config |
| `string_absent` | như trên | Cấm lọt ID test của Google vào bản release |
| `asset_json_path` | `assets.json[file]` theo JSONPath | Bật/tắt placement, ID từng chỗ |
| `asset_json_match` | như trên, so giá trị/regex | Đối chiếu ID với tài liệu ADS SCRIPTS |
| `sdk_version` | `strings.sdk_versions` | Phiên bản SDK tối thiểu |

Bảy kiểu, giảm từ mười một ở bản 1.0. Bốn kiểu bị bỏ (`init_order`, `api_called`,
`api_caller_in`, `screen_shape`) đều là loại phải đọc code — chuyển hết sang
`mode: agent`.

### 5.5. Luật `mode: agent`

```yaml
- id: ARCH_GLOBAL_INIT_ORDER
  title: Thứ tự khởi tạo trong Application
  mode: agent
  severity: high
  area: init

  # Mô tả bằng lời cho AI. Đây là "code" của luật agent.
  question: >
    Trong lớp Application của app, hãy xác định thứ tự thực tế của các lời gọi
    khởi tạo trong onCreate. Chuẩn yêu cầu MobileAds.initialize phải chạy trước
    DevConfig.init. Lưu ý tên lớp trong app có thể đã bị làm rối, hãy lần theo
    lời gọi tới SDK thay vì tin vào tên.

  # Tiêu chí kết luận, viết cho AI đọc
  verdict:
    pass_when: MobileAds.initialize chạy trước DevConfig.init
    fail_when: DevConfig.init chạy trước, hoặc thiếu hẳn MobileAds.initialize
    unknown_when: Không xác định được thứ tự do code bị làm rối quá nặng

  # Gợi ý điểm khởi đầu. Không bắt buộc, AI được tự do đi hướng khác.
  start_hints:
    - facts_path: manifest.application_file
    - tool: xrefs_to
      args: { method: "com.google.android.gms.ads.MobileAds.initialize" }

  budget:
    max_tool_calls: 25          # mặc định 25, luật nặng có thể nâng lên 60
  hint: Mở lớp Application trong jadx-gui, xem thứ tự lời gọi trong onCreate
```

Viết luật `agent` là viết bằng tiếng Việt hoặc tiếng Anh cho AI đọc, không phải
viết logic. Ba trường quyết định chất lượng:

- **`question`** — nói rõ tìm gì, và cảnh báo trước các bẫy (tên bị làm rối)
- **`verdict`** — ba nhánh phải rạch ròi, đặc biệt là `unknown_when`. Thiếu nhánh
  này thì AI sẽ cố nặn ra kết luận.
- **`start_hints`** — tiết kiệm được vài lượt gọi tool đầu tiên

### 5.6. Đối chiếu với tài liệu ADS SCRIPTS / checklist

Hai chế độ:

- **Không có tài liệu** — `apk-audit "<link>"` chạy ngay, chấm mọi luật không cần
  hợp đồng (thứ tự khởi tạo, luồng, cấu trúc màn hình, khóa cấu hình).
- **Có tài liệu** — thêm `--ads-scripts x.csv --checklist y.csv`, mở khoá các
  luật so ID và token.

Báo cáo phải ghi rõ mục nào **không chấm được vì thiếu tài liệu** (`SKIPPED`) —
tách hẳn khỏi `UNKNOWN` do làm rối code. Hai lý do khác nhau, cách xử lý khác nhau.

---

## 6. Hợp đồng dữ liệu: `findings.json`

```jsonc
{
  "schema_version": 2,
  "package": "com.foo.bar",
  "version_name": "2.4.1",
  "apk_sha256": "…",
  "rulepack": { "name": "infinity-base", "version": "1.0.0" },
  "engine": "codex",
  "docs_provided": { "ads_scripts": true, "checklist": false },

  "summary": {
    "pass": 26, "fail": 3, "unknown": 5, "skipped": 2, "total": 36,
    "static": 14, "agent": 22,
    "from_cache": 0, "tool_calls": 187, "duration_seconds": 214
  },

  "findings": [
    {
      "rule_id": "ARCH_GLOBAL_INIT_ORDER",
      "title": "Thứ tự khởi tạo trong Application",
      "area": "init",
      "severity": "high",
      "mode": "agent",
      "status": "FAIL",              // PASS | FAIL | UNKNOWN | SKIPPED
      "expected": "MobileAds.initialize trước DevConfig.init",
      "actual":   "DevConfig.init (dòng 88) trước MobileAds.initialize (dòng 104)",
      "evidence": [
        { "file": "sources/com/foo/bar/App.java", "line": 88,
          "excerpt": "DevConfig.init(this, …);", "verified": true }
      ],
      "reasoning": "Một câu AI giải thích vì sao kết luận như vậy.",
      "resolved_by": "agent:codex",
      "tool_calls": 9,
      "trace": "trace/ARCH_GLOBAL_INIT_ORDER.json"
    },
    {
      "rule_id": "FLOW_WELCOME_NATIVE_AND_INTER",
      "mode": "agent",
      "status": "UNKNOWN",
      "reason": "obfuscated",
      "reasoning": "Tìm được 3 lời gọi khả nghi nhưng không lớp nào giữ dấu vết đủ để khẳng định.",
      "hint": "Xem tay smali/com/foo/bar/a/b/c.smali:412",
      "evidence": [],
      "resolved_by": "agent:codex",
      "tool_calls": 25,
      "exhausted_budget": true
    },
    {
      "rule_id": "ID_ADMOB_UNIT_MATCH",
      "mode": "static",
      "status": "SKIPPED",
      "reason": "missing_document",
      "detail": "Cần file ADS SCRIPTS để đối chiếu ad unit ID."
    }
  ],

  // AI phát hiện thêm, KHÔNG tính vào summary. Nguồn để bổ sung luật mới.
  "observations": [
    {
      "title": "Thấy interstitial được show trực tiếp từ Activity",
      "detail": "…",
      "evidence": [ { "file": "…", "line": 233 } ],
      "suggested_rule_area": "flow"
    }
  ]
}
```

Bốn trạng thái, phân biệt rõ:

| Trạng thái | Nghĩa | Xử lý |
|---|---|---|
| `PASS` | Có bằng chứng làm đúng | — |
| `FAIL` | Có bằng chứng làm sai | Báo đối tác |
| `UNKNOWN` | Không đủ căn cứ kết luận | Xem tay theo `hint` |
| `SKIPPED` | Thiếu tài liệu đầu vào | Cung cấp tài liệu rồi chạy lại |

---

## 7. MCP server chạy nền

Thành phần mới, là trung tâm của bản 2.0.

### 7.1. Vì sao tự viết thay vì dùng `jadx-mcp-server` sẵn có

Bản `jadx-mcp-server` trên máy (`/home/infinity01/JADX/SYN-12/`) là client của
plugin chạy **bên trong jadx-gui** — các tool của nó nói rõ điều đó
(`fetch_current_class`: *"from the JADX-GUI plugin"*, `get_selected_text`). Dùng
nó thì mỗi app phải mở giao diện, nạp APK, đợi index — không tự động được, không
chạy hàng loạt được.

MCP của `apk-audit` chạy trên **thư mục jadx đã bung ở bước 3**. Không cửa sổ,
không plugin, khởi động trong một giây, chạy được song song nhiều app.

Hai cái không đụng nhau. `jadx-mcp-server` giữ nguyên vai cho lúc ngồi đào tay
một app sau khi báo cáo chỉ ra chỗ `UNKNOWN`.

### 7.2. Bộ tool

Chín tool. Giữ ít và đủ — mỗi tool thêm vào là thêm một hướng để AI đi lạc.

| Tool | Tham số | Trả về |
|---|---|---|
| `get_facts` | `path` (JSONPath, rỗng = cả file) | Phần tương ứng của `facts.json` |
| `list_classes` | `prefix`, `limit`, `offset` | Tên class theo tiền tố gói |
| `search_classes` | `pattern` (regex tên class) | Danh sách class khớp |
| `get_class` | `name` hoặc `file` | Mã Java đã decompile |
| `get_smali` | `name`, `method` (tuỳ chọn) | Bytecode, dùng khi Java decompile hỏng |
| `get_methods` | `name` | Danh sách method của class kèm số dòng |
| `xrefs_to` | `method` hoặc `class` | Mọi nơi gọi tới, kèm file và dòng |
| `grep` | `pattern`, `path_glob`, `limit` | Dòng khớp, kèm file và số dòng |
| `read_lines` | `file`, `start`, `end` | Đoạn code cụ thể |

### 7.3. Quy tắc cài đặt

- **Chống ngập context.** Mọi tool có `limit` mặc định. `get_class` quá 2000 dòng
  thì cắt và ghi rõ đã cắt, kèm gợi ý dùng `get_methods` + `read_lines`.
- **Kết quả luôn kèm vị trí.** Mọi kết quả có `file` và `line` để AI trích dẫn
  làm bằng chứng. Không có vị trí thì không thành bằng chứng được.
- **Chỉ đọc.** Không tool nào ghi, xoá, hay chạy gì. Đường dẫn phải nằm trong
  `workspace.root`, chặn `..`.
- **`xrefs_to` là tool đắt nhất.** Cài bằng cách quét chỉ mục dựng sẵn một lần ở
  bước 4 (bảng ngược method → nơi gọi), không quét lại mỗi lần gọi.
- **Dùng chung code với phần static.** `tools.py` chứa cài đặt thật; `mcp_server.py`
  chỉ bọc lại thành tool MCP. Nhờ vậy test được `tools.py` mà không cần MCP.

### 7.4. Cách hai engine nạp MCP

- **Claude:** `claude -p --mcp-config <file.json>` với server khai báo là lệnh
  `uv run apk-audit mcp --workspace <đường dẫn>`
- **Codex:** khai báo trong `~/.codex/config.toml` hoặc truyền
  `-c mcp_servers.apk_audit.command=…`

Công cụ tự sinh file cấu hình MCP tạm cho mỗi lượt chạy, trỏ đúng workspace của
app đang audit. Không đụng cấu hình toàn cục của người dùng.

---

## 8. Vòng lặp agent (`agent.py`)

### 8.1. Luồng một luật

```
1. Tra cache theo khóa (sha256 + rule_id + rulepack version + engine)
   → trúng thì trả kết quả, hết.
2. Dựng prompt:
     - context.md của rule pack
     - question + verdict của luật
     - start_hints
     - luật lệ đầu ra (mục 8.2)
3. Gọi engine với MCP đã nạp, ngân sách max_tool_calls.
4. Nhận JSON kết quả, kiểm tra theo mục 8.3.
5. Ghi cache + nhật ký vào trace/<rule_id>.json.
```

### 8.2. Khung prompt

Prompt phải nói đủ năm điều, thiếu điều nào là chất lượng tụt:

1. **Bối cảnh** — nội dung `context.md`
2. **Việc cần làm** — `question` của luật
3. **Tiêu chí kết luận** — ba nhánh của `verdict`, nhấn mạnh `unknown_when` là
   câu trả lời hợp lệ và được khuyến khích khi không chắc
4. **Công cụ** — có gì, nên bắt đầu từ đâu (`start_hints`), ngân sách bao nhiêu lượt
5. **Định dạng đầu ra** — đúng một khối JSON, mọi `FAIL` phải có bằng chứng kèm
   file và dòng thật

Câu quan trọng nhất cần có trong prompt, viết nguyên văn:

> Nếu không đủ căn cứ, hãy trả `UNKNOWN` kèm gợi ý file và dòng đáng ngờ nhất.
> `UNKNOWN` là kết quả đúng khi code đã bị làm rối. Đoán bừa gây hại hơn nhiều so
> với việc nói thẳng là không biết.

### 8.3. Kiểm tra kết quả trả về

Sáu rào chắn. Cái nào cũng bắt buộc:

1. Parse JSON thất bại → thử lại tối đa **1 lần** với lời nhắc định dạng; vẫn hỏng
   thì `UNKNOWN`
2. `status` ngoài bốn giá trị hợp lệ → `UNKNOWN`
3. `FAIL` mà `evidence` rỗng → hạ xuống `UNKNOWN`
4. **Xác minh bằng chứng:** mở file, kiểm tra số dòng có tồn tại, `excerpt` có
   khớp nội dung dòng đó không. Không khớp → đánh dấu `verified: false`; nếu
   *mọi* bằng chứng đều không khớp thì hạ xuống `UNKNOWN`
5. `rule_id` trả về không đúng luật đang hỏi → bỏ, `UNKNOWN`
6. Hết ngân sách tool mà chưa kết luận → `UNKNOWN` kèm `exhausted_budget: true`

Rào chắn số 4 là thứ phân biệt công cụ này với việc hỏi AI suông. Nó bắt được
đúng kiểu lỗi nguy hiểm nhất: bằng chứng nghe rất thuyết phục nhưng không tồn tại.

### 8.4. Chạy song song và ngân sách

- Nhóm luật cùng `area` chạy chung một phiên để tận dụng ngữ cảnh đã đào được
- Tối đa 3 phiên song song (tránh nghẽn I/O và giới hạn tốc độ của engine)
- Ngân sách toàn cục `--max-tool-calls` mặc định 400 cho cả lượt audit; vượt thì
  các luật còn lại thành `UNKNOWN` kèm lý do `global_budget`
- `--engine none` bỏ hẳn bước 6: mọi luật `agent` thành `UNKNOWN`. Vẫn ra báo cáo,
  vẫn có giá trị nhờ phần `static`

### 8.5. Cache phán quyết (`verdict_cache.py`)

```
<cache_dir>/verdicts/<apk_sha256>/<rulepack_version>/<engine>/<rule_id>.json
```

Mỗi file chứa: finding đầy đủ, nhật ký tool (gọi gì, nhận gì), prompt đã dùng,
thời điểm, phiên bản công cụ.

- `--refresh` — bỏ qua cache, chạy lại tất cả
- `--refresh-rule <id>` — chạy lại một luật
- Đổi `context.md` hoặc bất kỳ file luật nào → `rulepack_version` phải tăng, nếu
  không cache cũ sẽ che mất luật mới. **Cho `pack.yaml` một trường `version` và
  bắt buộc tăng khi sửa luật.** Cân nhắc dùng hash nội dung thư mục rule pack
  thay cho số phiên bản viết tay, để khỏi quên.

---

## 9. Adapter engine (`engines.py`)

Một giao diện, hai cài đặt, chọn bằng `--engine`.

```python
class Engine(Protocol):
    name: str
    def available(self) -> bool: ...
    def run_agent(
        self,
        prompt: str,
        mcp_config: Path,
        max_tool_calls: int,
        timeout: int = 600,
    ) -> AgentResult: ...     # gồm: text đầu ra, nhật ký tool, số lượt đã dùng
```

| Engine | Lệnh | Ghi chú |
|---|---|---|
| `claude` | `claude -p --output-format json --mcp-config <file>` | Prompt qua stdin |
| `codex` | `codex exec --json -c mcp_servers…` | Prompt qua stdin |
| `none` | — | Bỏ bước 6, mọi luật `agent` thành `UNKNOWN` |

Mặc định: dò `claude` trước, không có thì `codex`, không có nữa thì `none` kèm
cảnh báo.

Nhật ký tool lấy từ luồng JSON của engine. Định dạng hai bên khác nhau —
`engines.py` chuẩn hoá về một dạng chung trước khi ghi cache.

---

## 10. Giao diện dòng lệnh

```
apk-audit <target> [tuỳ chọn]

<target>   Link Google Play, hoặc đường dẫn file .apk/.xapk có sẵn

Tài liệu hợp đồng:
  --ads-scripts <file|url>   CSV hoặc link Google Sheets của ADS SCRIPTS
  --checklist   <file|url>   CSV hoặc link Google Sheets của working checklist

Bộ luật:
  --rules <thư mục>          Mặc định: rulepacks/default/
  --only <area|rule_id>      Chỉ chạy một nhóm hoặc một luật
  --static-only              Bỏ mọi luật agent (bằng --engine none)

AI:
  --engine claude|codex|none Mặc định: tự dò
  --max-tool-calls <n>       Ngân sách toàn cục, mặc định 400
  --refresh                  Bỏ qua cache phán quyết, chạy lại tất cả
  --refresh-rule <id>        Chạy lại một luật

Đầu ra:
  --out <thư mục>            Mặc định: ./out/<package>-<version>/
  --format md|json|both      Mặc định: both
  --trace                    Ghi kèm nhật ký agent vào thư mục out
  --quiet                    Chỉ in đường dẫn báo cáo

Cache:
  --no-cache                 Tải lại APK kể cả khi đã có
  --cache-dir <thư mục>      Ghi đè vị trí cache mặc định

Lệnh phụ:
  apk-audit facts <target>       Chỉ chạy tới bước 4, in facts.json
  apk-audit mcp --workspace <d>  Chạy MCP server (engine gọi, ít khi gọi tay)
  apk-audit ask <target> "<câu hỏi>"   Hỏi tự do một app, không theo bộ luật
  apk-audit rules check          Kiểm tra tính hợp lệ của bộ luật
  apk-audit rules list           Liệt kê luật, gom theo area
  apk-audit serve                Giao diện web tại localhost:8765  (M7)
```

`apk-audit ask` là quà kèm theo của kiến trúc MCP: đã có sẵn tool và workspace
thì hỏi tự do gần như không tốn thêm công viết. Rất hữu dụng lúc đào tay.

### Mã thoát

| Mã | Nghĩa |
|---|---|
| 0 | Chạy xong, không có `FAIL` |
| 1 | Chạy xong, có ít nhất một `FAIL` |
| 2 | Lỗi đầu vào (link sai, thiếu file) |
| 3 | Lỗi tải APK |
| 4 | Lỗi jadx |
| 5 | Lỗi bộ luật |
| 6 | Lỗi engine AI (không có engine, hết hạn đăng nhập) |

### Đầu ra mẫu

```
$ apk-audit "https://play.google.com/store/apps/details?id=com.foo.bar"

đọc link   com.foo.bar 2.4.1
tải        apkcombo → 42 MB (đã có trong cache)
bung       jadx → 6.812 file, 41 giây
chỉ mục    23 màn hình · 2 file cấu hình · 891 chuỗi · khởi tạo: com.foo.bar.App
static     14 luật → 11 đạt · 1 sai · 2 bỏ qua
agent      22 luật · codex · 187 lượt tool · 174 giây
           → 15 đạt · 2 sai · 5 chưa rõ

báo cáo    ./out/com.foo.bar-2.4.1/report.md
nhật ký    ./out/com.foo.bar-2.4.1/trace/

SAI       Thứ tự khởi tạo · DevConfig.init gọi trước MobileAds.initialize
          bằng chứng: sources/com/foo/bar/App.java:88 ✓
SAI       Cổng kiểm tra UA · native_home thiếu gate
          bằng chứng: sources/com/foo/bar/a/k.java:142 ✓
CHƯA RÕ   Luồng Welcome · hết ngân sách sau 25 lượt — xem tay a/b/c.smali:412
BỎ QUA    Đối chiếu ad unit ID · cần file ADS SCRIPTS

3 quan sát ngoài bộ luật — xem cuối báo cáo
```

---

## 11. Chi tiết từng bước

### Bước 1 — `playstore.py`

- Nhận link Play, rút `id=` từ query string
- Tải trang Play lấy `version_name` (không có thì để trống, không chặn)
- Không cần đăng nhập, không cần API key

**Vỡ khi:** link sai định dạng, app đã gỡ khỏi Play, trang Play đổi bố cục.
**Xử lý:** vẫn chạy tiếp nếu có package name.

### Bước 2 — `fetch.py`

- Nguồn chính: apkcombo. Dự phòng: apkpure.
- Cache theo `<cache_dir>/<package>/<version>/`; đã có thì bỏ qua tải
- Kiểm tra: file phải là ZIP hợp lệ, có `AndroidManifest.xml`
- Ghi `source.sha256` — đây là khóa của cache phán quyết, phải chính xác

**Vỡ khi:** site đổi HTML, Cloudflare chặn, app không có trên nguồn đó.
**Xử lý:** báo lỗi rõ ràng kèm hướng dẫn tải tay và thả file vào thư mục cache,
rồi chạy lại. Không bao giờ để pipeline tắc chỉ vì bước này.

Đây là bước dễ vỡ nhất trong toàn hệ thống. Cô lập nó.

### Bước 3 — `unpack.py`

- XAPK/APKM: giải nén, tìm base APK (`base.apk` hoặc APK lớn nhất có manifest)
- Chạy `jadx --no-debug-info --no-inline-anonymous -d <workspace> <apk>`
- Bung thêm smali (`--to-smali` hoặc `baksmali`) — agent cần khi Java hỏng
- Ghi `unpack.json` (số file, thời gian, mã thoát của jadx)

**Lưu ý:** jadx có thể trả mã thoát khác 0 mà vẫn bung được phần lớn code. Kiểm
tra thư mục đầu ra chứ đừng chỉ tin mã thoát.

### Bước 4 — `facts/`

Ba module con: `manifest.py`, `assets.py`, `strings.py`. Nhẹ hơn hẳn bản 1.0 vì
không còn phải dựng cây lời gọi.

Thêm một việc: **dựng chỉ mục ngược cho `xrefs_to`.** Quét một lượt toàn bộ smali,
lập bảng `method đích → [nơi gọi]`, ghi ra `workspace/xref_index.json`. Làm một
lần ở đây thì tool `xrefs_to` trả lời tức thì, thay vì quét lại mỗi lượt AI hỏi.

Module nào không đọc được phần của mình thì để trống và ghi cảnh báo, không được
ném lỗi làm hỏng cả bước.

### Bước 5 — `rules/` (phần static)

- `loader.py` nạp YAML, kiểm tra `schema_version`, kiểm tra mã luật không trùng
- `engine.py` chạy luật `mode: static`, bắt lỗi riêng từng luật (một luật hỏng
  không được làm hỏng cả lượt — luật đó thành `UNKNOWN` kèm lý do `rule_error`)
- Luật cần tài liệu mà không có tài liệu → `SKIPPED`

### Bước 6 — `agent.py`

Xem mục 8.

### Bước 7 — `report.py`

`report.md` xếp theo thứ tự người đọc cần:

1. Tóm tắt một dòng: đạt / sai / chưa rõ / bỏ qua, kèm số lượt tool và thời gian
2. **Sai** — gom theo `area`; mỗi mục kèm mong đợi, thực tế, bằng chứng đã xác
   minh, và một câu lý giải của AI
3. **Chưa rõ** — kèm gợi ý file và dòng để mở jadx-gui; ghi rõ hết ngân sách hay
   thật sự bó tay
4. **Bỏ qua** — nói rõ thiếu tài liệu nào
5. **Đạt** — gộp lại, mặc định thu gọn
6. **Quan sát ngoài bộ luật** — thứ AI thấy thêm, không tính điểm
7. Phụ lục: phiên bản công cụ, rule pack, engine, sha256 của APK, đường dẫn nhật ký

`report.json` là `findings.json` cộng metadata — dùng cho skill AI và script tự động.

---

## 12. Thứ tự triển khai

Mỗi cột mốc phải chạy được và kiểm chứng được trước khi sang cột mốc sau.

### M0 — Khung dự án

- `pyproject.toml` với `uv`, entry point `apk-audit`
- `contracts.py`: dataclass cho `Facts`, `Finding`, `Rule`
- `config.py`: dò jadx, dò engine, đường dẫn cache theo hệ điều hành
- CLI khung, mới chỉ in tham số đã nhận

**Xong khi:** `uv run apk-audit --help` chạy được trên cả ba hệ điều hành.

### M1 — Lấy hàng (bước 1-3)

- `playstore.py`, `fetch.py`, `unpack.py`
- Cache hoạt động; nhận trực tiếp đường dẫn APK, bỏ qua bước 1-2

**Xong khi:** `apk-audit --out /tmp/x <link>` cho ra thư mục đã bung code.
**Kiểm chứng:** 3 app thật khác nhau, trong đó có 1 XAPK.

### M2 — Chỉ mục (bước 4)

Thứ tự dễ trước: `manifest.py` → `assets.py` → `strings.py` → chỉ mục ngược xref.

**Xong khi:** `apk-audit facts <apk>` in JSON đúng lược đồ mục 4, và
`workspace/xref_index.json` tồn tại.
**Kiểm chứng:** mở `facts.json` của 3 app thật, đối chiếu tay với jadx-gui.

### M3 — MCP server và bộ tool  ★ cột mốc mới

- `tools.py` — cài đặt chín tool
- `mcp_server.py` — bọc thành MCP
- `apk-audit ask` — cửa vào để thử tay

**Xong khi:** `apk-audit ask <apk> "lớp Application gọi những gì trong onCreate?"`
cho câu trả lời đúng, chạy được với cả `claude` lẫn `codex`.
**Kiểm chứng:** đây là cột mốc chứng minh cả kiến trúc bản 2.0. Nếu bước này chật
vật thì dừng lại xem lại thiết kế tool trước khi đi tiếp.

### M4 — Chấm luật static (bước 5)

- `loader.py`, `checks.py`, `engine.py`; bảy kiểu luật ở mục 5.4
- Viết phần `static` của rule pack đầu tiên

**Xong khi:** `apk-audit rules check` báo hợp lệ, chạy trên `facts.json` mẫu ra
`findings.json` đúng lược đồ mục 6.

### M5 — Báo cáo (bước 7)

Làm trước vòng lặp agent. Có báo cáo là đã dùng được, dù mọi luật `agent` còn
đang `UNKNOWN`.

**Xong khi:** `report.md` đọc được, `report.json` parse được.

### M6 — Vòng lặp agent (bước 6)

- `engines.py` với hai cài đặt
- `agent.py` với đủ sáu rào chắn ở mục 8.3
- `verdict_cache.py`
- Viết phần `agent` của rule pack

**Xong khi:** chạy được cả `--engine claude` lẫn `--engine codex`; `--engine none`
vẫn ra báo cáo đầy đủ; chạy lại lần hai đọc cache, ra kết quả giống hệt.
**Kiểm chứng:** ép AI trả JSON hỏng, ép bằng chứng trỏ dòng không tồn tại → công
cụ hạ xuống `UNKNOWN`, không sập, không nhận bằng chứng giả.

### M7 — Cửa vào phụ

- Skill `/audit-play` cho Claude và Codex (~30 dòng, gọi lại CLI)
- `apk-audit serve` — web tại máy

Chỉ làm khi M0-M6 đã ổn định.

---

## 13. Kiểm thử

| Tầng | Cách test | Cần mạng | Cần AI |
|---|---|---|---|
| `rules/` static | `facts.json` mẫu trong `tests/fixtures/facts/` | không | không |
| `report.py` | `findings.json` mẫu | không | không |
| `tools.py` | workspace nhỏ dựng sẵn, khẳng định từng tool | không | không |
| `agent.py` | phát lại nhật ký đã ghi trong `tests/fixtures/traces/` | không | không |
| Rào chắn 8.3 | engine giả trả JSON hỏng / bằng chứng bịa | không | không |
| `facts/` | 1-2 APK nhỏ trong `tests/fixtures/apks/` | không | không |
| `fetch.py` | test đánh dấu riêng, chạy tay | có | không |
| Đầu-cuối | 1 app thật, đánh dấu riêng | có | có |

Nguyên tắc: **phần lớn test không được cần mạng và không được cần AI.**

Kỹ thuật then chốt là **phát lại nhật ký**: mọi lượt agent thật đều ghi nhật ký
tool. Cất vài nhật ký vào `tests/fixtures/traces/`, engine giả phát lại đúng chuỗi
đó. Nhờ vậy test được toàn bộ `agent.py` — gồm cả rào chắn — mà không tốn một
token nào.

Bộ test hồi quy: giữ `facts.json` cộng nhật ký của vài app đã audit tay, kèm kết
quả mong đợi. Sửa rule pack thì chạy lại để biết có làm hỏng gì không.

---

## 14. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| AI bịa bằng chứng | cao | Rào chắn 8.3 mục 4: mở file xác minh từng dòng |
| Chi phí token tăng theo số app | cao | Cache phán quyết; luật rẻ đi đường `static`; ngân sách tool có trần |
| AI đi lạc, hết ngân sách mà chưa kết luận | trung bình | `start_hints`; `context.md` tốt; nhật ký để chỉnh lại luật |
| Hai engine trả kết quả khác nhau | trung bình | Ghi tên engine vào báo cáo và vào khóa cache; chốt một engine cho một đợt audit |
| apkcombo đổi HTML | cao | Cô lập trong `fetch.py`; luôn có đường tải tay |
| APK dùng bảo vệ/mã hoá | trung bình | Phát hiện sớm, báo rõ, không đoán bừa |
| Bộ luật lệch khỏi dự án mẫu | cao | Ghi phiên bản rule pack vào báo cáo; test hồi quy mục 13 |
| Quên tăng `rulepack version` → cache che luật mới | trung bình | Dùng hash nội dung thư mục rule pack thay số viết tay |
| Đường dẫn dài trên Windows | cao | Xử lý ở mục 15.2, làm ngay từ M0 |

---

## 15. Chạy trên Windows, Mac, Linux

### 15.1. Tìm jadx và Java

- jadx cần JDK 11 trở lên
- Tên file: `jadx` (Mac/Linux) và `jadx.bat` (Windows)
- Thứ tự dò: biến môi trường `JADX_PATH` → `PATH` → vị trí cài mặc định
- Không thấy → báo lỗi kèm lệnh cài. **Không tự chạy `apt install`, `brew
  install`, hay `curl … | bash`.**

### 15.2. Đường dẫn quá dài trên Windows

Vấn đề chắc chắn gặp. jadx sinh cây thư mục rất sâu, vượt giới hạn 260 ký tự,
jadx chết giữa chừng với lỗi khó hiểu.

Xử lý:
- Cache mặc định đặt ở đường dẫn ngắn nhất có thể
- Cho phép `--cache-dir C:\ap` để rút ngắn thủ công
- Phát hiện lỗi liên quan độ dài → in hướng dẫn bật `LongPathsEnabled`
- Dùng tiền tố `\\?\` cho thao tác file khi cần

### 15.3. Vị trí cache

Dùng `platformdirs`, không viết cứng:

| Hệ | Đường dẫn |
|---|---|
| Linux | `~/.cache/apk-audit/` |
| macOS | `~/Library/Caches/apk-audit/` |
| Windows | `%LOCALAPPDATA%\apk-audit\` |

Thư mục con: `apks/`, `workspaces/`, `verdicts/`.

### 15.4. Gọi `claude` và `codex`

Trên Windows hai lệnh này là `.cmd` shim. `subprocess` phải dò đủ đuôi
`.cmd`/`.exe`/`.bat`, hoặc dùng `shutil.which` với `PATHEXT`. Không xử thì phần
AI im lặng không chạy.

### 15.5. Đường dẫn trong cấu hình MCP

File cấu hình MCP sinh tự động phải dùng đường dẫn tuyệt đối đã chuẩn hoá. Trên
Windows, dấu `\` trong JSON phải escape đúng.

---

## 16. Quan hệ với công cụ sẵn có

| Công cụ | Vai |
|---|---|
| `jadx` bản dòng lệnh | Nằm trong dây chuyền, bước 3 |
| Skill `android-apk-decompiler` | Tham khảo script bung file; có thể gọi lại |
| Skill `infinity-ads-compliance-audit` | Nguồn để rút rule pack, đặc biệt là `context.md`. Phần chấm luật cũ đọc mã nguồn Kotlin nên không dùng lại được cho APK |
| `jadx-mcp-server` (SYN-12) | **Không** nằm trong dây chuyền — nó cần jadx-gui mở sẵn. Giữ nguyên cho việc đào tay một app sau khi báo cáo chỉ ra chỗ `UNKNOWN`. Xem mục 7.1 |

---

## 17. Việc cần làm tiếp

1. Chốt lược đồ `facts.json` ở mục 4 và bộ chín tool ở mục 7.2 — hai hợp đồng
   này khoá lại trước khi viết luật
2. Đọc dự án mẫu, viết `context.md` — đây là thứ ảnh hưởng chất lượng nhiều nhất
3. Với mỗi quy tắc trong dự án mẫu, phân loại `static` hay `agent` theo tiêu chí
   mục 2.1
4. Viết `rulepacks/default/` đầu tiên
5. Bắt đầu M0

---

## Phụ lục A — Lệnh dựng dự án

```bash
mkdir -p ~/apk-audit && cd ~/apk-audit
uv init --package .
uv add httpx beautifulsoup4 platformdirs pyyaml rich fastmcp
uv add --dev pytest pytest-cov

# cài để dùng toàn hệ thống
uv tool install --editable .

# trên máy khác
uv tool install git+<url repo>
```

## Phụ lục B — Thư viện

| Thư viện | Dùng cho |
|---|---|
| `httpx` | Tải trang Play và APK |
| `beautifulsoup4` | Parse HTML apkcombo/apkpure |
| `platformdirs` | Đường dẫn cache theo hệ điều hành |
| `pyyaml` | Nạp bộ luật |
| `rich` | In tiến trình và bảng ra terminal |
| `fastmcp` | Dựng MCP server |
| `pytest` | Kiểm thử |

Parse `AndroidManifest.xml`: jadx đã decode sẵn ra XML thường, dùng
`xml.etree.ElementTree` của thư viện chuẩn. Không cần thêm thư viện Android.

## Phụ lục C — Giữ nguyên các ràng buộc an toàn

Kế thừa từ skill `android-apk-decompiler`, áp dụng cho mọi bước, gồm cả các tool
MCP:

- Không cài, không chạy, không khởi động app đã tải
- Không chạy bất cứ thứ gì lấy ra từ trong gói
- Không upload APK lên bất kỳ dịch vụ nào
- Không sửa hay di chuyển file đầu vào
- Mọi tool MCP chỉ đọc, và chỉ trong phạm vi `workspace.root`
- Không chạy `sudo`, `apt install`, hay `curl … | bash` để tự cài công cụ thiếu

## Phụ lục D — Thay đổi so với bản 1.0

| Bản 1.0 | Bản 2.0 | Vì sao |
|---|---|---|
| AI đọc file được đẩy sẵn | AI tự đào qua MCP | AI chỉ đọc thứ nó cần, đi sâu được tới đâu tuỳ tình huống |
| `facts.json` mô tả đầy đủ, gồm cây lời gọi | `facts.json` là chỉ mục, bỏ phần phân tích code | Cắt bỏ phần khó nhất của bước 4; AI làm tốt hơn qua tool |
| 11 kiểu luật static | 7 kiểu static + `mode: agent` | Luật đọc code chuyển hẳn sang agent |
| Tính lặp lại bằng cách hạn chế AI | Tính lặp lại bằng cache phán quyết | Vẫn lặp lại được mà không phải trói AI |
| Không có nhật ký | `trace/<rule_id>.json` cho mỗi luật | Kiểm chứng được kết luận; test phát lại không tốn token |
| Bằng chứng tin theo lời AI | Mở file xác minh từng dòng | Chặn đúng kiểu lỗi nguy hiểm nhất |
| Không có `apk-audit ask` | Có | Kiến trúc MCP cho không |
