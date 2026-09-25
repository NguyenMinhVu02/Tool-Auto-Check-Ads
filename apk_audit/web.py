"""Small local-only HTTP front end for the existing audit pipeline."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from .errors import AuditError
from .pipeline import run


MAX_UPLOAD_BYTES = 4 * 1024**3
MAX_DOCUMENT_BYTES = 5 * 1024**2
ALLOWED_EXTENSIONS = {".apk", ".xapk", ".apkm"}
DOCUMENT_EXTENSIONS = {".csv", ".json"}
DOCUMENT_KINDS = {"ads_scripts", "checklist"}
ASSETS = Path(__file__).with_name("web_assets")


class AuditJobs:
    def __init__(self, output_root, rules=None):
        self.output_root = Path(output_root).resolve()
        self.rules = Path(rules).resolve() if rules else None
        self.jobs = {}
        self.documents = {}
        self.active = None
        self.lock = threading.Lock()

    def store_document(self, kind, filename, stream, size):
        name = Path(unquote(filename).replace("\\", "/")).name
        if kind not in DOCUMENT_KINDS or Path(name).suffix.lower() not in DOCUMENT_EXTENSIONS:
            raise ValueError("Tài liệu cần là CSV hoặc JSON của ADS SCRIPTS/working file")
        document_id = uuid4().hex
        path = self.output_root / "documents" / (document_id + Path(name).suffix.lower())
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
        with self.lock:
            self.documents[document_id] = (kind, path)
        return document_id

    def reserve(self, filename, ads_id=None, checklist_id=None):
        name = Path(unquote(filename).replace("\\", "/")).name
        if not name or Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError("Chỉ nhận file .apk, .xapk hoặc .apkm")
        if bool(ads_id) != bool(checklist_id):
            raise ValueError("Cần cả ADS SCRIPTS và working file; nếu thiếu một file hãy bỏ qua cả hai")
        with self.lock:
            if self.active is not None:
                raise RuntimeError("Đang xử lý một file khác; hãy đợi kết quả")
            documents = {}
            if ads_id:
                for key, token in (("ads_scripts", ads_id), ("checklist", checklist_id)):
                    entry = self.documents.get(token)
                    if entry is None or entry[0] != key:
                        raise ValueError("Tài liệu không hợp lệ hoặc đã dùng; hãy chọn lại hai file")
                    documents[key] = entry[1]
                self.documents.pop(ads_id)
                self.documents.pop(checklist_id)
            job_id = uuid4().hex
            self.active = job_id
            self.jobs[job_id] = {"id": job_id, "filename": name, "state": "uploading", "stage": "upload", "docs_used": bool(documents)}
            self.jobs[job_id]["documents"] = documents
        return job_id, self.output_root / "uploads" / (job_id + Path(name).suffix.lower())

    def update(self, job_id, **fields):
        with self.lock:
            self.jobs[job_id].update(fields)
            if fields.get("state") in {"done", "error"}:
                self.active = None

    def get(self, job_id):
        with self.lock:
            return dict(self.jobs[job_id]) if job_id in self.jobs else None

    def start(self, job_id, archive):
        self.update(job_id, state="running", stage="unpack")
        threading.Thread(target=self._execute, args=(job_id, archive), daemon=True).start()

    def _execute(self, job_id, archive):
        try:
            documents = self.get(job_id)["documents"]
            report = run(
                archive,
                rules=self.rules,
                out=self.output_root / job_id,
                engine="none",
                ads_scripts=documents.get("ads_scripts"),
                checklist=documents.get("checklist"),
                progress=lambda stage: self.update(job_id, stage=stage),
            )
            self.update(
                job_id,
                state="done",
                stage="done",
                summary=report["summary"],
                package=report["package"],
                warnings=report["warnings"],
                report_path=str(Path(report["output"]) / "report.json"),
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
            self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status, value):
            self._send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            route = urlsplit(self.path).path
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
                    job.pop("report_path", None)
                    job.pop("documents", None)
                    self._json(200, job)
                    return
                if parts[3] == "report" and job["state"] == "done":
                    report = Path(job["report_path"]).read_bytes()
                    self._send(200, report, "application/json; charset=utf-8")
                    return
            self._json(404, {"error": "Đường dẫn không tồn tại"})

        def do_POST(self):
            route = urlsplit(self.path).path
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
                    document_id = jobs.store_document(
                        self.headers.get("X-Document-Kind", ""),
                        self.headers.get("X-Filename", ""), self.rfile, size,
                    )
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                except OSError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                self._json(201, {"id": document_id})
                return
            try:
                job_id, archive = jobs.reserve(
                    self.headers.get("X-Filename", ""),
                    self.headers.get("X-Ads-Scripts-Id"),
                    self.headers.get("X-Checklist-Id"),
                )
            except ValueError as exc:
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
            jobs.start(job_id, archive)
            self._json(202, {"id": job_id, "state": "running"})

    return Handler


def serve(port=8765, output_root="out/web", rules=None):
    jobs = AuditJobs(output_root, rules)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(jobs))
    print(f"apk-audit web: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
