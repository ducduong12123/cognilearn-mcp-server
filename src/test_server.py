# src/test_server.py

from mcp.server.fastmcp import FastMCP

# Khởi tạo một server siêu nhẹ, không có lifespan, không có gì phức tạp
mcp = FastMCP(
    name="Test Server",
    port=8003  # Dùng một cổng hoàn toàn mới để tránh xung đột
)

app = mcp.streamable_http_app()

@mcp.tool()
def hello(name: str = "World") -> str:
    """A simple tool that says hello."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="stdio") # Chạy bằng stdio để langflow kết nối