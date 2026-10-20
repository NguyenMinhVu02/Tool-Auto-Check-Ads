"""Small local-only HTTP front end for the existing audit pipeline."""

import json
from datetime import datetime, timezone
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from .documents import list_sheets, load_document
from .marketing import build_marketing_summary
from .errors import AuditError
from .engines import detect_engines
from .execution import MAX_WORKERS, valid_workers
from .pipeline import run
from .utils import write_json


MAX_UPLOAD_BYTES = 4 * 1024**3
MAX_DOCUMENT_BYTES = 5 * 1024**2
ALLOWED_EXTENSIONS = {".apk", ".xapk", ".apkm"}
DOCUMENT_EXTENSIONS = {".xlsx", ".csv", ".json"}
DOCUMENT_KINDS = {"ads_scripts", "checklist"}
ASSETS = Path(__file__).with_name("web_assets")
JOB_PUBLIC_FIELDS = {
    "id", "filename", "state", "stage", "docs_used", "engine", "upload_complete",
    "resumable", "interrupted", "created_at", "updated_at", "error", "summary", "package",
    "warnings", "rule_total", "rule_completed", "current_rule", "current_rule_title",
    "current_rules", "active_rules", "last_rule",
}
JOB_PRIVATE_FIELDS = {"documents", "archive_path", "output_path", "report_path"}


class AuditJobs:
    def __init__(self, output_root, rules=None, workers=1):
        self.output_root = Path(output_root).resolve()
        self.rules = Path(rules).resolve() if rules else None
        if not valid_workers(workers):
            raise ValueError(f"workers phải từ 1 đến {MAX_WORKERS}")
        self.workers = workers
        self.jobs = {}
        self.documents = {}
        self.active = None
        self.lock = threading.RLock()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._recover()

    def _path(self, value, *, exists=False):
        if not isinstance(value, (str, Path)):
            raise ValueError("Đường dẫn job không hợp lệ")
        path = Path(value)
        if not path.is_absolute():
            path = self.output_root / path
        if ".." in path.parts or not path.is_relative_to(self.output_root):
            raise ValueError("Đường dẫn job vượt ngoài output_root")
        current = path
        while current != self.output_root:
            if current.is_symlink():
                raise ValueError("Đường dẫn job không được chứa symlink")
            current = current.parent
        if not path.resolve().is_relative_to(self.output_root):
            raise ValueError("Đường dẫn job vượt ngoài output_root")
        if exists and not path.is_file():
            raise ValueError("File của lượt kiểm tra không còn tồn tại")
        return path

    def _metadata_path(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise ValueError("ID lượt kiểm tra không hợp lệ")
        return self._path(self.output_root / "jobs" / f"{job_id}.json")

    def _validate_paths(self, job, *, inputs=False):
        job_id = job["id"]
        self._metadata_path(job_id)
        archive = self._path(job["archive_path"], exists=inputs)
        if archive.parent != self.output_root / "uploads" or archive.stem != job_id or archive.suffix not in ALLOWED_EXTENSIONS:
            raise ValueError("Đường dẫn archive không hợp lệ")
        if self._path(job["output_path"]) != self.output_root / job_id:
            raise ValueError("Đường dẫn output không hợp lệ")
        if job.get("report_path") and self._path(job["report_path"]) != self.output_root / job_id / "report.json":
            raise ValueError("Đường dẫn report không hợp lệ")
        documents = job.get("documents", {})
        if not isinstance(documents, dict) or set(documents) not in (set(), DOCUMENT_KINDS):
            raise ValueError("Cần đủ cặp tài liệu đã upload")
        if bool(documents) != job.get("docs_used", False):
            raise ValueError("Thông tin tài liệu không hợp lệ")
        for value in documents.values():
            path = self._path(value, exists=inputs)
            if path.parent != self.output_root / "documents" or path.suffix not in DOCUMENT_EXTENSIONS:
                raise ValueError("Đường dẫn tài liệu không hợp lệ")
        if inputs and (not job.get("upload_complete") or archive.stat().st_size == 0):
            raise ValueError("Upload chưa hoàn tất; hãy chọn lại ứng dụng")
        return archive

    def _persist(self, job):
        write_json(self._metadata_path(job["id"]),
                   {key: value for key, value in job.items() if key in JOB_PUBLIC_FIELDS | JOB_PRIVATE_FIELDS})

    def _recover(self):
        directory = self._path(self.output_root / "jobs")
        if not directory.exists():
            return
        for path in directory.glob("*.json"):
            try:
                self._path(path, exists=True)
                if path.stat().st_size > 1024 * 1024:
                    continue
                job = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(job, dict) or path != self._metadata_path(job.get("id")):
                    continue
                if job.get("state") not in {"uploading", "running", "done", "error"} or job.get("engine") not in {"codex", "claude"}:
                    continue
                job = {key: value for key, value in job.items() if key in JOB_PUBLIC_FIELDS | JOB_PRIVATE_FIELDS}
                if any(not isinstance(job.get(key, ""), str) for key in ("created_at", "updated_at", "filename", "stage")):
                    continue
                if any(type(job.get(key, False)) is not bool for key in ("docs_used", "upload_complete", "interrupted")):
                    continue
                self._validate_paths(job)
                if job["state"] in {"uploading", "running"}:
                    job.update(state="error", interrupted=True,
                               error="Lượt kiểm tra bị gián đoạn khi server dừng. Bấm Tiếp tục để chạy phần còn thiếu bằng cache hợp lệ.")
                job["resumable"] = False
                if job.get("interrupted") and job["state"] == "error":
                    try:
                        self._validate_paths(job, inputs=True)
                        job["resumable"] = True
                    except (ValueError, OSError):
                        pass
                self.jobs[job["id"]] = job
                self._persist(job)
            except (OSError, ValueError, KeyError, TypeError):
                # A damaged record must not trigger work or hide healthy history.
                continue

    @staticmethod
    def _public(job):
        return {key: value for key, value in job.items() if key in JOB_PUBLIC_FIELDS}

    def list_jobs(self):
        with self.lock:
            return [self._public(job) for job in sorted(self.jobs.values(),
                    key=lambda item: item.get("created_at", ""), reverse=True)]

    def read_report(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            self._validate_paths(job)
            if job["state"] != "done":
                raise ValueError("Báo cáo chưa hoàn tất")
            path = self._path(job["report_path"], exists=True)
            documents = dict(job.get("documents") or {})
            sheets = job.get("document_sheets") or {}
        raw = path.read_bytes()
        report = json.loads(raw)
        if "marketing" in report or "inventory" not in report:
            return raw
        # Reports made before the Marketing summary existed: rebuild it from saved inputs.
        try:
            facts = json.loads((path.parent / "facts.json").read_text(encoding="utf-8"))
            loaded = {"ads_scripts": load_document(self._path(documents["ads_scripts"], exists=True), "ads_scripts",
                                                   sheet=sheets.get("ads_scripts"))} if documents.get("ads_scripts") else {}
            report["marketing"] = build_marketing_summary(loaded, facts, report["inventory"], report["findings"])
        except (OSError, ValueError, KeyError, AuditError):
            return raw
        return json.dumps(report, ensure_ascii=False).encode("utf-8")

    def resume(self, job_id):
        with self.lock:
            if self.active is not None:
                raise RuntimeError("Đang xử lý một file khác; hãy đợi kết quả")
            self._metadata_path(job_id)
            job = self.jobs[job_id]
            if job["state"] != "error" or not job.get("interrupted") or not job.get("resumable"):
                raise ValueError("Lượt kiểm tra này không thể tiếp tục")
            archive = self._validate_paths(job, inputs=True)
            detected = detect_engines()
            if not any(item["id"] == job["engine"] and item["installed"] for item in detected["engines"]):
                raise ValueError(f"Không tìm thấy {job['engine']} CLI; hãy cài và đăng nhập CLI đã chọn")
            self.active = job_id
            self.update(job_id, state="running", stage="documents", interrupted=False, resumable=False,
                        error=None, current_rules=[], active_rules=[], current_rule=None,
                        current_rule_title=None, rule_completed=0)
        threading.Thread(target=self._execute, args=(job_id, archive, True), daemon=True).start()
        return job_id

    def store_document(self, kind, filename, stream, size):
        name = Path(unquote(filename).replace("\\", "/")).name
        if kind not in DOCUMENT_KINDS or Path(name).suffix.lower() not in DOCUMENT_EXTENSIONS:
            raise ValueError("Tài liệu cần là XLSX, CSV hoặc JSON của ADS SCRIPTS/working file")
        document_id = uuid4().hex
        path = self._path(self.output_root / "documents" / (document_id + Path(name).suffix.lower()))
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            remaining = size
            with path.open("wb") as output:
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise OSError("Upload tài liệu bị ngắt giữa chừng")
                    output.write(chunk)
                    remaining -= len(chunk)
        except OSError:
            path.unlink(missing_ok=True)
            raise
        try:
            sheets = list_sheets(path, kind)
        except (OSError, ValueError, KeyError) as exc:
            path.unlink(missing_ok=True)
            raise ValueError(str(exc) or "File XLSX không hợp lệ") from exc
        with self.lock:
            self.documents[document_id] = (kind, path, sheets)
        return document_id, sheets

    def reserve(self, filename, ads_id=None, checklist_id=None, engine=None, ads_sheet=None, checklist_sheet=None,
                cross_flow=False):
        name = Path(unquote(filename).replace("\\", "/")).name
        if not name or Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError("Chỉ nhận file .apk, .xapk hoặc .apkm")
        if bool(ads_id) != bool(checklist_id):
            raise ValueError("Cần cả ADS SCRIPTS và working file; nếu thiếu một file hãy bỏ qua cả hai")
        detected = detect_engines()
        engine = detected['default'] if engine is None else engine
        if engine is None:
            raise ValueError("Chưa tìm thấy Codex CLI hoặc Claude CLI trên PATH của máy chạy server")
        if engine not in {'codex', 'claude'}:
            raise ValueError("Engine không hợp lệ; chọn codex hoặc claude")
        if not any(item['id'] == engine and item['installed'] for item in detected['engines']):
            raise ValueError(f"Không tìm thấy {engine} CLI; cài CLI vào PATH rồi bấm Phát hiện lại")
        with self.lock:
            if self.active is not None:
                raise RuntimeError("Đang xử lý một file khác; hãy đợi kết quả")
            documents, sheets = {}, {}
            if ads_id:
                for key, token, sheet in (("ads_scripts", ads_id, ads_sheet), ("checklist", checklist_id, checklist_sheet)):
                    entry = self.documents.get(token)
                    if entry is None or entry[0] != key:
                        raise ValueError("Tài liệu không hợp lệ hoặc đã dùng; hãy chọn lại hai file")
                    if sheet and sheet not in entry[2]:
                        raise ValueError(f"Sheet không thuộc tài liệu đã tải: {sheet}")
                    if not sheet and len(entry[2]) > 1:
                        raise ValueError("Workbook có nhiều sheet; hãy chọn sheet của app cần kiểm cho từng tài liệu")
                    documents[key] = str(self._path(entry[1], exists=True))
                    if sheet:
                        sheets[key] = sheet
                self.documents.pop(ads_id)
                self.documents.pop(checklist_id)
            job_id = uuid4().hex
            archive = self._path(self.output_root / "uploads" / (job_id + Path(name).suffix.lower()))
            self._path(self.output_root / job_id)
            self.jobs[job_id] = {"id": job_id, "filename": name, "state": "uploading", "stage": "upload", "docs_used": bool(documents), "engine": engine,
                                 "cross_flow": bool(cross_flow)}
            self.jobs[job_id].update(documents=documents, document_sheets=sheets, archive_path=str(archive),
                                     output_path=str(self.output_root / job_id), upload_complete=False,
                                     resumable=False, interrupted=False,
                                     created_at=datetime.now(timezone.utc).isoformat())
            self._persist(self.jobs[job_id])
            self.active = job_id
        return job_id, archive

    def update(self, job_id, **fields):
        with self.lock:
            self.jobs[job_id].update(fields)
            self.jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._persist(self.jobs[job_id])
            if fields.get("state") in {"done", "error"} and self.active == job_id:
                self.active = None

    def get(self, job_id):
        with self.lock:
            return dict(self.jobs[job_id]) if job_id in self.jobs else None

    def start(self, job_id, archive):
        with self.lock:
            job = self.jobs[job_id]
            if self.active != job_id or job["state"] != "uploading":
                raise ValueError("Lượt upload không còn hoạt động")
            if self._path(archive, exists=True) != self._path(job["archive_path"]):
                raise ValueError("Archive không khớp lượt upload")
            self.update(job_id, upload_complete=True)
            self._validate_paths(job, inputs=True)
            self.update(job_id, state="running", stage="documents")
        threading.Thread(target=self._execute, args=(job_id, archive), daemon=True).start()

    def _execute(self, job_id, archive, resumed=False):
        try:
            documents = self.get(job_id)["documents"]
            def rule_progress(event, detail):
                with self.lock:
                    active = {item["rule_id"]: item for item in self.jobs[job_id].get("current_rules", [])}
                    if event == "activity":
                        item = active.get(detail["rule_id"])
                        if item is None:
                            return
                        item = dict(item)
                        for key in ("phase", "attempt", "allowance", "tool_calls"):
                            if key in detail:
                                item[key] = detail[key]
                        if detail.get("command"):
                            item["command"] = detail["command"]
                            item["recent_commands"] = (item.get("recent_commands", []) + [detail["command"]])[-6:]
                        elif "phase" in detail:
                            item["command"] = None
                        item["activity_at"] = datetime.now(timezone.utc).isoformat()
                        active[detail["rule_id"]] = item
                        self.update(job_id, current_rules=list(active.values()), active_rules=list(active.values()))
                        return
                    if event == "start":
                        active[detail["rule_id"]] = {"rule_id": detail["rule_id"], "title": detail["title"],
                                                     "started_at": datetime.now(timezone.utc).isoformat()}
                    else:
                        active.pop(detail["rule_id"], None)
                    current = next(iter(active.values()), {})
                    fields = dict(rule_total=detail["total"], rule_completed=detail["completed"],
                                  current_rule=current.get("rule_id"), current_rule_title=current.get("title"),
                                  current_rules=list(active.values()), active_rules=list(active.values()))
                    if event == "complete":
                        fields["last_rule"] = {"rule_id": detail["rule_id"], "status": detail["status"],
                                               "from_cache": detail["from_cache"]}
                    self.update(job_id, **fields)
            report = run(
                self._validate_paths(self.get(job_id), inputs=True),
                rules=self.rules,
                out=self._path(self.get(job_id)["output_path"]),
                cache_dir=self._path(self.output_root / "cache"),
                workers=self.workers,
                resume=resumed,
                engine=self.get(job_id)["engine"],
                cross_flow=self.get(job_id).get("cross_flow", False),
                ads_scripts=self._path(documents["ads_scripts"], exists=True) if documents else None,
                checklist=self._path(documents["checklist"], exists=True) if documents else None,
                ads_sheet=self.get(job_id).get("document_sheets", {}).get("ads_scripts"),
                checklist_sheet=self.get(job_id).get("document_sheets", {}).get("checklist"),
                progress=lambda stage: self.update(job_id, stage=stage),
                rule_progress=rule_progress,
            )
            report_path = self._path(Path(report["output"]) / "report.json", exists=True)
            if report_path != self.output_root / job_id / "report.json":
                raise ValueError("Pipeline trả report ngoài thư mục job")
            self.update(
                job_id,
                state="done", resumable=False, interrupted=False, current_rules=[], active_rules=[],
                stage="done",
                summary=report["summary"],
                package=report["package"],
                warnings=report["warnings"],
                report_path=str(report_path),
            )
        except (AuditError, OSError, ValueError) as exc:
            self.update(job_id, state="error", error=str(exc))
        except Exception:
            self.update(job_id, state="error", error="Lỗi phân tích ngoài dự kiến; xem log server")


def make_handler(jobs):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status, value):
            self._send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            route = urlsplit(self.path).path
            if route == "/api/jobs":
                self._json(200, {"jobs": jobs.list_jobs()})
                return
            if route == '/api/engines':
                self._json(200, detect_engines())
                return
            static = {"/": ("index.html", "text/html"), "/app.css": ("app.css", "text/css"), "/app.js": ("app.js", "text/javascript")}
            for weight in ("Regular", "Medium", "SemiBold", "Bold"):
                static[f"/fonts/Poppins-{weight}.ttf"] = (f"fonts/Poppins-{weight}.ttf", "font/ttf")
            if route in static:
                filename, mime = static[route]
                self._send(200, (ASSETS / filename).read_bytes(), mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
                return
            parts = route.strip("/").split("/")
            if len(parts) in {3, 4} and parts[:2] == ["api", "jobs"]:
                job = jobs.get(parts[2])
                if job is None:
                    self._json(404, {"error": "Không tìm thấy lượt kiểm tra"})
                    return
                if len(parts) == 3:
                    self._json(200, jobs._public(job))
                    return
                if parts[3] == "report" and job["state"] == "done":
                    try:
                        report = jobs.read_report(parts[2])
                    except (ValueError, OSError, KeyError):
                        self._json(400, {"error": "Báo cáo không còn hợp lệ hoặc đã bị di chuyển"})
                        return
                    self._send(200, report, "application/json; charset=utf-8")
                    return
            self._json(404, {"error": "Đường dẫn không tồn tại"})

        def do_POST(self):
            route = urlsplit(self.path).path
            parts = route.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "resume":
                try:
                    job_id = jobs.resume(parts[2])
                except KeyError:
                    self._json(404, {"error": "Không tìm thấy lượt kiểm tra"})
                    return
                except RuntimeError as exc:
                    self._json(409, {"error": str(exc)})
                    return
                except (ValueError, OSError) as exc:
                    self._json(400, {"error": str(exc)})
                    return
                self._json(202, {"id": job_id, "state": "running"})
                return
            if route not in {"/api/jobs", "/api/documents"}:
                self._json(404, {"error": "Đường dẫn không tồn tại"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                size = 0
            limit = MAX_DOCUMENT_BYTES if route == "/api/documents" else MAX_UPLOAD_BYTES
            if size <= 0 or size > limit:
                self._json(413, {"error": "File rỗng hoặc vượt giới hạn " + ("5 MiB" if route == "/api/documents" else "4 GiB")})
                return
            if route == "/api/documents":
                try:
                    document_id, sheets = jobs.store_document(
                        self.headers.get("X-Document-Kind", ""),
                        self.headers.get("X-Filename", ""), self.rfile, size,
                    )
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                except OSError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                self._json(201, {"id": document_id, "sheets": sheets})
                return
            try:
                job_id, archive = jobs.reserve(
                    self.headers.get("X-Filename", ""),
                    self.headers.get("X-Ads-Scripts-Id"),
                    self.headers.get("X-Checklist-Id"),
                    self.headers.get("X-Audit-Engine"),
                    unquote(self.headers.get("X-Ads-Scripts-Sheet", "")) or None,
                    unquote(self.headers.get("X-Checklist-Sheet", "")) or None,
                    self.headers.get("X-Cross-Flow") == "1",
                )
            except (ValueError, OSError) as exc:
                self._json(400, {"error": str(exc)})
                return
            except RuntimeError as exc:
                self._json(409, {"error": str(exc)})
                return
            try:
                archive.parent.mkdir(parents=True, exist_ok=True)
                remaining = size
                with archive.open("wb") as stream:
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise OSError("Upload bị ngắt giữa chừng")
                        stream.write(chunk)
                        remaining -= len(chunk)
            except OSError as exc:
                archive.unlink(missing_ok=True)
                jobs.update(job_id, state="error", error=str(exc))
                self._json(400, {"error": str(exc)})
                return
            try:
                jobs.start(job_id, archive)
            except (ValueError, OSError) as exc:
                jobs.update(job_id, state="error", error=str(exc))
                self._json(400, {"error": str(exc)})
                return
            self._json(202, {"id": job_id, "state": "running"})

    return Handler


def serve(port=8765, output_root="out/web", rules=None, workers=6):
    jobs = AuditJobs(output_root, rules, workers=workers)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(jobs))
    print(f"apk-audit web: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
