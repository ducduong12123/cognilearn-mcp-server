# 1) Base image
FROM python:3.12-slim

# 2) Workdir
WORKDIR /app

# 3) Tool to install deps fast
RUN pip install --no-cache-dir uv

# 4) Copy requirements first to leverage layer cache
COPY requirements.txt ./

# 5) Install deps into system env (verbose + fallback to pip)
#    - In case uv resolver gặp xung đột, fallback pip sẽ backtrack kỹ hơn.
RUN set -eux; \
    python -V; uv --version; \
    uv pip install --system -r requirements.txt -v || \
    (python -m pip install --upgrade pip setuptools wheel && \
     pip install --no-cache-dir -r requirements.txt)

# 6) Copy project code
COPY . .

# 7) Expose a default dev port (Render sẽ đặt $PORT khi deploy)
EXPOSE 8002

# 8) Start command
CMD ["sh","-lc","exec gunicorn -w ${WORKERS:-2} -k uvicorn.workers.UvicornWorker src.memory_mcp_server:app --bind 0.0.0.0:${PORT:-8002} --timeout ${TIMEOUT:-0} --keep-alive ${KEEPALIVE:-5} --log-level info --access-logfile - --error-logfile -"]

