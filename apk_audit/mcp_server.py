from .tools import WorkspaceTools
from .errors import AuditError

TOOL_NAMES = ("get_facts", "list_classes", "search_classes", "get_class", "get_smali", "get_methods", "xrefs_to", "grep", "read_lines")

def create_server(workspace):
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise AuditError("Cài phần MCP bằng: uv sync --extra mcp", 2) from exc
    server = FastMCP("apk-audit", version="0.1.0")
    tools = WorkspaceTools(workspace)
    for name in TOOL_NAMES:
        server.tool(getattr(tools, name))
    return server

def serve(workspace):
    create_server(workspace).run(transport="stdio", show_banner=False)
