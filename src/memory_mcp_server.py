import os
import time
from typing import AsyncIterator, Dict, Any
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from src.core.memory_service import MemoryService

# ---------------------- Lazy singleton ----------------------
_memory_service_instance: MemoryService | None = None

def get_memory_service() -> MemoryService:
    global _memory_service_instance
    if _memory_service_instance is None:
        print("🚀 Lazily initializing CogniLearn Memory Service for the first time...")
        _memory_service_instance = MemoryService()
        print("✅ Memory Service is ready.")
    return _memory_service_instance

# ---------------------- Lifespan ----------------------
@asynccontextmanager
async def simple_lifespan(server: FastMCP) -> AsyncIterator[None]:
    print("🚀 MCP Server starting up quickly (lazy initialization enabled).")
    try:
        yield
    finally:
        print("🛑 Shutting down server.")

# ---------------------- Config ----------------------
SERVER_PORT = int(os.getenv("PORT", "8002"))
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "").strip() or ""  # dùng chuỗi rỗng, không dùng None

# ---------------------- MCP & ASGI app ----------------------
mcp = FastMCP(
    name="CogniLearn_Memory_Server",
    instructions="A server to manage the long-term memory for CogniLearn students.",
    lifespan=simple_lifespan,
    port=SERVER_PORT,
    log_level="DEBUG",
    stateless_http=True,   # <<< thêm dòng này
)


app: Starlette = mcp.streamable_http_app()

# ---------------------- (Optional) CORS ----------------------
if os.getenv("ENABLE_CORS", "1") not in ("0", "false", "False"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ---------------------- Logging middleware ----------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    dur_ms = (time.perf_counter() - start) * 1000
    print(f"[HTTP] {request.method} {request.url.path} -> {response.status_code} in {dur_ms:.1f}ms")
    return response

# ---------------------- Routes tiện kiểm tra ----------------------
async def index(request: Request):
    return JSONResponse({"ok": True, "service": "CogniLearn MCP Server", "endpoint": "/mcp", "health": "/healthz"})
app.add_route("/", index, methods=["GET"])

async def health_check(request: Request):
    return JSONResponse({"status": "ok", "service": "CogniLearn MCP Server"})
app.add_route("/healthz", health_check, methods=["GET"])

# ---------------------- Tools (KHÔNG dùng Optional/None trong type) ----------------------
@mcp.tool()
def add_memory(
    user_id: str,                # required string (không Optional)
    content: str,                # required string
    metadata: Dict[str, Any] = {},   # object trống mặc định (tránh None để khỏi tạo union)
    importance: float = 0.5      # number
) -> Dict[str, Any]:
    """
    Thêm 'memory' cho user. Nếu bạn muốn fallback, truyền user_id="" và xử lý bên dưới.
    """
    try:
        uid = user_id or DEFAULT_USER_ID
        if not uid:
            return {
                "status": "error",
                "code": "USER_ID_REQUIRED",
                "message": "Thiếu user_id và DEFAULT_USER_ID trống."
            }

        ms = get_memory_service()
        # an toàn với default tham chiếu
        meta = dict(metadata) if metadata else {}
        ms.add_memory(
            user_id=uid,
            content=content,
            metadata=meta,
            importance=importance
        )
        return {"status": "success", "message": f"Memory added for user {uid}."}
    except Exception as e:
        print(f"Error in add_memory tool: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def retrieve_similar_memories(
    user_id: str,            # required string
    query_text: str,         # required string
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Truy vấn các ký ức liên quan nhất cho user.
    """
    try:
        uid = user_id or DEFAULT_USER_ID
        if not uid:
            return {
                "status": "error",
                "code": "USER_ID_REQUIRED",
                "message": "Thiếu user_id và DEFAULT_USER_ID trống.",
                "memories": [],
                "context_text": ""
            }

        ms = get_memory_service()
        results = ms.retrieve_similar_memories(
            user_id=uid,
            query_text=query_text,
            top_k=top_k
        )
        if not results:
            return {"memories": [], "context_text": "Không tìm thấy ký ức nào liên quan."}

        lines = []
        for i, m in enumerate(results, 1):
            lines.append(f"{i}. {m.get('content', 'N/A')} (Similarity: {m.get('similarity', 0):.2f})")

        return {"memories": results, "context_text": "\n".join(lines)}
    except Exception as e:
        print(f"Error in retrieve_similar_memories tool: {e}")
        return {"status": "error", "message": str(e), "memories": [], "context_text": ""}

# ---------------------- Local run ----------------------
if __name__ == "__main__":
    print(f"Starting MCP Server for CogniLearn (for local testing) on port {SERVER_PORT}...")
    mcp.run(transport="stdio")
