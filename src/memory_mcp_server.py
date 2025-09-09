import os
from typing import List, Dict, Any, Optional, AsyncIterator

from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.requests import Request

# Import MemoryService từ module đã có
from src.core.memory_service import MemoryService

# --- LAZY INITIALIZATION SINGLETON PATTERN ---
_memory_service_instance: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    """
    Khởi tạo MemoryService theo kiểu "lazy" và đảm bảo singleton
    trong suốt vòng đời server.
    """
    global _memory_service_instance
    if _memory_service_instance is None:
        print("🚀 Lazily initializing CogniLearn Memory Service for the first time...")
        _memory_service_instance = MemoryService()
        print("✅ Memory Service is ready.")
    return _memory_service_instance

# --- Lifespan siêu nhẹ ---
@asynccontextmanager
async def simple_lifespan(server: FastMCP) -> AsyncIterator[None]:
    print("🚀 MCP Server starting up quickly (lazy initialization enabled).")
    try:
        yield
    finally:
        print("🛑 Shutting down server.")

# --- Khởi tạo MCP Server ---
SERVER_PORT = int(os.getenv("PORT", "8002"))

mcp = FastMCP(
    name="CogniLearn_Memory_Server",
    instructions="A server to manage the long-term memory for CogniLearn students.",
    lifespan=simple_lifespan,
    port=SERVER_PORT,
    log_level="DEBUG",
)

# --- Ứng dụng ASGI chính (Starlette) mà FastMCP mount vào ---
app: Starlette = mcp.streamable_http_app()

# --- Health check cho Render (Starlette không có .get nên dùng add_route/route) ---
async def health_check(request: Request):
    return JSONResponse({"status": "ok", "service": "CogniLearn MCP Server"})

app.add_route("/healthz", health_check, methods=["GET"])

# --- Tools ---
@mcp.tool()
def add_memory(
    user_id: str,
    content: str,
    metadata: dict = None,
    importance: float = 0.5
) -> Dict[str, Any]:
    """
    Lưu một 'ký ức' mới cho học sinh (user_id).
    """
    try:
        memory_service = get_memory_service()
        memory_service.add_memory(
            user_id=user_id,
            content=content,
            metadata=metadata,
            importance=importance
        )
        return {"status": "success", "message": f"Memory added for user {user_id}."}
    except Exception as e:
        print(f"Error in add_memory tool: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def retrieve_similar_memories(
    user_id: str,
    query_text: str,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Truy vấn các ký ức liên quan nhất cho một học sinh (user_id).
    """
    try:
        memory_service = get_memory_service()
        similar_memories = memory_service.retrieve_similar_memories(
            user_id=user_id,
            query_text=query_text,
            top_k=top_k
        )
        if not similar_memories:
            return {"memories": [], "context_text": "Không tìm thấy ký ức nào liên quan."}
        context_text = "Dưới đây là một số ký ức liên quan:\n"
        for i, memory in enumerate(similar_memories):
            context_text += f"{i+1}. {memory.get('content', 'N/A')} (Similarity: {memory.get('similarity', 0):.2f})\n"
        return {"memories": similar_memories, "context_text": context_text.strip()}
    except Exception as e:
        print(f"Error in retrieve_similar_memories tool: {e}")
        return {"status": "error", "message": str(e), "memories": [], "context_text": ""}

# --- Chạy local (Render sẽ không dùng khối này) ---
if __name__ == "__main__":
    print(f"Starting MCP Server for CogniLearn (for local testing) on port {SERVER_PORT}...")
    mcp.run(transport="stdio")
