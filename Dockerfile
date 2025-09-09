# 1) Base image
FROM python:3.12-slim

# 2) Workdir
WORKDIR /app

# 3) Tool to install deps fast
RUN pip install uv

# 4) Copy requirements first to leverage layer cache
COPY requirements.txt ./

# 5) Install deps into system env
RUN uv pip install --system -r requirements.txt

# 6) Copy project code
COPY . .

# 7) Expose a default dev port (Render tự đặt $PORT khi deploy)
EXPOSE 8002

# 8) Start command: bind theo $PORT của Render (fallback 8002)
#    Cho phép chỉnh số worker qua biến WORKERS (mặc định 4)
CMD ["sh", "-c", "gunicorn -w ${WORKERS:-4} -k uvicorn.workers.UvicornWorker src.memory_mcp_server:app --bind 0.0.0.0:${PORT:-8002}"]
