import argparse
import json
from pathlib import Path
import sys
from .config import doctor
from .errors import AuditError
from .facts import build_facts
from .pipeline import run, prepare
from .rules.loader import load_pack

def parser():
    result = argparse.ArgumentParser(prog="apk-audit", description="Khung audit APK; bổ sung chuẩn ads/init bằng rule pack bên ngoài.")
    sub = result.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="Audit APK hoặc workspace jadx (có thể bỏ từ audit)")
    audit.add_argument("target")
    audit.add_argument("--rules", type=Path)
    audit.add_argument("--out", type=Path)
    audit.add_argument("--engine", choices=["none","claude","codex"], default="codex", help="codex: gpt-6-luna (mặc định); claude: model mặc định Claude CLI; none: tắt AI")
    audit.add_argument("--static-only", action="store_true")
    audit.add_argument("--only")
    audit.add_argument("--max-tool-calls", type=int, default=400)
    audit.add_argument("--refresh", action="store_true")
    audit.add_argument("--refresh-rule")
    audit.add_argument("--trace", action="store_true")
    audit.add_argument("--format", choices=["md","json","both"], default="both")
    audit.add_argument("--quiet", action="store_true")
    audit.add_argument("--no-cache", action="store_true")
    audit.add_argument("--cache-dir", type=Path)
    audit.add_argument("--ads-scripts", type=Path)
    audit.add_argument("--checklist", type=Path)
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
    return result

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    commands = {"audit","facts","mcp","rules","doctor","ask","serve"}
    if argv and argv[0] not in commands and argv[0] not in {"-h","--help"}:
        argv.insert(0,"audit")
    args = vars(parser().parse_args(argv))
    command = args.pop("command")
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
        elif command == "ask":
            raise AuditError("ask chưa nối adapter AI; dùng apk-audit mcp --workspace với MCP client.", 6)
        elif command == "serve":
            from .web import serve
            serve(port=args["port"], output_root=args["out"], rules=args["rules"])
        else:
            quiet = args.pop("quiet")
            if args.pop("static_only"):
                args["engine"] = "none"
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
