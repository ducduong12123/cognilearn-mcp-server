import os
from typing import List, Dict, Any, Optional, AsyncIterator

from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

# Import MemoryService từ module đã có
from src.core.memory_service import MemoryService

# --- LAZY INITIALIZATION SINGLETON PATTERN ---
_memory_service_instance: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    """
    Hàm này khởi tạo MemoryService một cách "lười biếng" (chỉ khi được gọi lần đầu)
    và đảm bảo chỉ có một instance duy nhất trong suốt vòng đời của server.
    """
    global _memory_service_instance
    if _memory_service_instance is None:
        print("🚀 Lazily initializing CogniLearn Memory Service for the first time...")
        # Lỗi sẽ xảy ra ở đây nếu thiếu biến môi trường, giúp gỡ lỗi dễ hơn
        _memory_service_instance = MemoryService()
        print("✅ Memory Service is now ready.")
    return _memory_service_instance

# --- Vòng đời (Lifespan) đơn giản ---
@asynccontextmanager
async def simple_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Lifespan siêu nhẹ, giúp server khởi động ngay lập tức."""
    print("🚀 MCP Server starting up quickly (lazy initialization enabled).")
    try:
        yield
    finally:
        print("🛑 Shutting down server.")

# --- Khởi tạo MCP Server ---
mcp = FastMCP(
    name="CogniLearn Memory Server",
    instructions="A server to manage the long-term memory for CogniLearn students.",
    lifespan=simple_lifespan,
    port=8002,
    log_level="DEBUG"
)

# --- Tạo biến cho ứng dụng ASGI ---
app = mcp.streamable_http_app()

# --- Định nghĩa các Tools ---
@mcp.tool()
def add_memory(
    user_id: str,
    content: str,
    metadata: dict = None,
    importance: float = 0.5
    # Bỏ ctx đi nếu bạn đang dùng phiên bản lazy-init
) -> Dict[str, Any]:
    """
    Lưu một thông tin hoặc 'ký ức' mới vào bộ nhớ dài hạn cho một học sinh cụ thể.
    
    Args:
        user_id (str): Mã định danh duy nhất của học sinh. BẮT BUỘC phải có.
        content (str): Nội dung của ký ức cần lưu, dưới dạng một câu tóm tắt. BẮT BUỘC phải có.
        metadata (dict): Một đối tượng JSON chứa dữ liệu bổ sung. Có thể bỏ qua nếu không có.
        importance (float, optional): Một số từ 0.0 đến 1.0 để đánh giá mức độ quan trọng của ký ức. Mặc định là 0.5.
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
    # Bỏ ctx đi nếu bạn đang dùng phiên bản lazy-init
) -> Dict[str, Any]:
    """
    Tìm kiếm và truy xuất các ký ức liên quan nhất từ bộ nhớ dài hạn của một học sinh.
    
    Args:
        user_id (str): Mã định danh duy nhất của học sinh cần tìm kiếm. BẮT BUỘC phải có.
        query_text (str): Một câu hỏi hoặc một chuỗi văn bản mô tả những gì bạn muốn tìm. BẮT BUỘC phải có.
        top_k (int, optional): Số lượng kết quả ký ức gần nhất cần trả về. Mặc định là 5.
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

# --- Chạy Server (chỉ để kiểm tra thủ công) ---
if __name__ == "__main__":
    # LangFlow sẽ chạy file này như một module, nên khối này không được thực thi
    # khi chạy qua LangFlow. Chúng ta sẽ dùng stdio để LangFlow giao tiếp.
    mcp.run(transport="sse")