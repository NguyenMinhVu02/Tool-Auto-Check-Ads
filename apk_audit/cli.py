import argparse
import json
from pathlib import Path
import sys
from .config import doctor
from .setup_tools import activate as activate_tools
from .errors import AuditError
from .facts import build_facts
from .pipeline import run, prepare
from .execution import MAX_WORKERS
from .rules.loader import load_pack

def parser():
    result = argparse.ArgumentParser(prog="apk-audit", description="Khung audit APK; bổ sung chuẩn ads/init bằng rule pack bên ngoài.")
    sub = result.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="Audit APK hoặc workspace jadx (có thể bỏ từ audit)")
    audit.add_argument("target")
    audit.add_argument("--rules", type=Path)
    audit.add_argument("--out", type=Path)
    audit.add_argument("--engine", choices=["none","claude","codex"], help="AI dùng để audit; mặc định là CLI đã cài (ưu tiên claude). claude: Sonnet mới nhất / low; codex: model Sol mới nhất CLI hỗ trợ / low; none: tắt AI")
    audit.add_argument("--static-only", action="store_true")
    audit.add_argument("--only")
    audit.add_argument("--max-tool-calls", type=int, default=400)
    audit.add_argument("--refresh", action="store_true")
    audit.add_argument("--resume", action="store_true", help="Tiếp tục các rule đã lưu checkpoint đúng đầu vào")
    audit.add_argument("--workers", type=int, choices=range(1, MAX_WORKERS + 1), default=1, metavar="1-10", help="Số rule độc lập chạy đồng thời (mặc định 1)")
    audit.add_argument("--refresh-rule")
    audit.add_argument("--trace", action="store_true")
    audit.add_argument("--format", choices=["md","json","both"], default="both")
    audit.add_argument("--quiet", action="store_true")
    audit.add_argument("--no-cache", action="store_true")
    audit.add_argument("--cache-dir", type=Path)
    audit.add_argument("--ads-scripts", type=Path)
    audit.add_argument("--checklist", type=Path)
    audit.add_argument("--no-scoped-cache", dest="scoped_cache", action="store_false", help="Không dùng lại kết quả theo file liên quan giữa các bản build")
    audit.add_argument("--recheck-all", action="store_true", help="Chạy lại cả rule đã đạt ở bản trước (rule có skip_after_pass)")
    audit.add_argument("--confirm-mismatch", action="store_true", help="Tiếp tục dù tài liệu có vẻ không thuộc app (package/AdMob App ID/tài khoản AdMob lệch)")
    audit.add_argument("--full", dest="full_scope", action="store_true", help="Kiểm đầy đủ: thêm rule Load/observe và Banner (mặc định chỉ khởi tạo, Remote/consent/fallback, ID và 4 màn đầu)")
    audit.add_argument("--cross-flow", action="store_true", help="Chạy thêm rule rà lỗi chéo giữa các luồng (tốn thêm token)")
    audit.add_argument("--ads-sheet", help="Tên sheet XLSX của ADS SCRIPTS khi workbook có nhiều app")
    audit.add_argument("--checklist-sheet", help="Tên sheet XLSX của working file khi workbook có nhiều app")
    facts = sub.add_parser("facts", help="In facts JSON từ APK/workspace")
    facts.add_argument("target")
    facts.add_argument("--rules", type=Path)
    facts.add_argument("--cache-dir", type=Path)
    mcp = sub.add_parser("mcp", help="Chạy MCP stdio chỉ đọc")
    mcp.add_argument("--workspace", type=Path, required=True)
    rules = sub.add_parser("rules", help="Kiểm tra/liệt kê rule pack")
    rules.add_argument("action", choices=["check","list"])
    rules.add_argument("--rules", type=Path)
    sub.add_parser("doctor", help="Kiểm tra công cụ trong máy")
    ask = sub.add_parser("ask", help="Điểm mở rộng hỏi AI (chưa nối)")
    ask.add_argument("target")
    ask.add_argument("question")
    web = sub.add_parser("serve", help="Mở giao diện audit trên localhost")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--out", type=Path, default=Path("out/web"))
    web.add_argument("--rules", type=Path)
    web.add_argument("--workers", type=int, choices=range(1, MAX_WORKERS + 1), default=6, metavar="1-10", help="Số rule chạy đồng thời (mặc định 6)")
    web.add_argument("--open", action="store_true", help="Mở trình duyệt; nếu server đã chạy thì chỉ mở trình duyệt")
    shortcut = sub.add_parser("shortcut", help="Tạo biểu tượng APK Audit trên màn hình chính")
    shortcut.add_argument("--desktop", type=Path, help="Thư mục Desktop (mặc định tự tìm)")
    bench = sub.add_parser("benchmark", help="Đo cold/warm audit hoặc bộ ca claim tổng hợp")
    bench.add_argument("target", nargs="?")
    bench.add_argument("--quality", action="store_true", help="Chạy ca tổng hợp offline, không gọi AI")
    bench.add_argument("--rules", type=Path)
    bench.add_argument("--out", type=Path, default=Path("out/benchmark"))
    bench.add_argument("--engine", choices=["none","codex","claude"], default="none")
    bench.add_argument("--workers", type=int, choices=range(1, MAX_WORKERS + 1), default=1, metavar="1-10")
    bench.add_argument("--repeats", type=int, default=2)
    bench.add_argument("--cache-dir", type=Path)
    bench.add_argument("--ads-scripts", type=Path)
    bench.add_argument("--checklist", type=Path)
    return result

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    commands = {"audit","facts","mcp","rules","doctor","ask","serve","benchmark","shortcut"}
    if argv and argv[0] not in commands and argv[0] not in {"-h","--help"}:
        argv.insert(0,"audit")
    args = vars(parser().parse_args(argv))
    command = args.pop("command")
    activate_tools()
    try:
        if command == "doctor":
            print(json.dumps(doctor(), indent=2, ensure_ascii=False))
        elif command == "rules":
            pack = load_pack(args["rules"])
            if args["action"] == "check":
                print(f"Hợp lệ: {pack.name} {pack.version}; {len(pack.rules)} luật" + (" — chưa có luật ads/init" if not pack.rules else ""))
            else:
                for rule in sorted(pack.rules, key=lambda r:(r.area,r.id)):
                    print(f"{rule.area}\t{rule.id}\t{rule.mode}\t{rule.title}")
                if not pack.rules:
                    print("Chưa có luật.")
        elif command == "facts":
            pack = load_pack(args["rules"])
            workspace, source = prepare(args["target"], args["cache_dir"])
            print(json.dumps(build_facts(workspace, source, pack.extract).to_dict(), indent=2, ensure_ascii=False))
        elif command == "mcp":
            from .mcp_server import serve
            workspace, _ = prepare(args["workspace"])
            serve(workspace)
        elif command == "benchmark":
            from .benchmark import benchmark, quality_suite
            if args.pop("quality"):
                from .utils import write_json
                result = quality_suite()
                write_json(args["out"] / "quality.json", result)
                print(json.dumps(result, ensure_ascii=False))
                return 0 if result["matched"] == result["total"] else 1
            if not args["target"]:
                raise AuditError("benchmark cần target hoặc --quality")
            target = args.pop("target")
            result = benchmark(target, **args)
            print(json.dumps({"runs":[r["summary"] for r in result["runs"]],"comparisons":result["comparisons"]},ensure_ascii=False))
        elif command == "ask":
            raise AuditError("ask chưa nối adapter AI; dùng apk-audit mcp --workspace với MCP client.", 6)
        elif command == "serve":
            from .web import serve
            from .launcher import open_browser_later, server_running
            url = f"http://127.0.0.1:{args['port']}/"
            if args["open"] and server_running(args["port"]):
                print(f"APK Audit đã chạy sẵn, mở {url}")
                import webbrowser
                webbrowser.open(url)
                return 0
            if args["open"]:
                open_browser_later(url)
            code = serve(port=args["port"], output_root=args["out"], rules=args["rules"], workers=args["workers"])
            if code:
                return code
        elif command == "shortcut":
            from .launcher import create_shortcut
            for path in create_shortcut(args["desktop"]):
                print(f"Đã tạo: {path}")
        else:
            quiet = args.pop("quiet")
            if args.pop("static_only"):
                args["engine"] = "none"
            if args["engine"] is None:
                from .engines import detect_engines
                args["engine"] = detect_engines()["default"] or "none"
                if args["engine"] == "none":
                    print("Không tìm thấy Claude CLI hoặc Codex CLI: chỉ chạy kiểm tra tĩnh.", file=sys.stderr)
            result = run(**args)
            output = Path(result["output"])
            if not quiet:
                print(json.dumps(result["summary"], ensure_ascii=False))
                if "no_rules" in result["warnings"]:
                    print("Chưa có luật; chưa đánh giá chuẩn ads/init.", file=sys.stderr)
            for fmt in (["md","json"] if args["format"] == "both" else [args["format"]]):
                print(output / ("report." + fmt))
            return 1 if result["summary"]["fail"] else 0
        return 0
    except AuditError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return exc.code
    except (OSError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2
