# ========= Base =========
FROM python:3.12-slim

# Log/IO ổn định & tắt cảnh báo pip khi chạy root
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# (Tuỳ gói) tool build wheel
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl wget \
    && rm -rf /var/lib/apt/lists/*

# ========= Install deps =========
# Lưu ý: trong requirements.txt nên để uvicorn >= 0.31.1 để khớp mcp==1.13.x
COPY requirements.txt ./
RUN set -eux; \
    python -V; pip -V; \
    pip install --upgrade pip setuptools wheel; \
    pip install -r requirements.txt

# ========= App code =========
COPY . .

# Render sẽ set $PORT; EXPOSE chỉ để tham khảo local
EXPOSE 8002

# ========= Healthcheck (tuỳ chọn, nên có) =========
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:${PORT:-8002}/healthz >/dev/null 2>&1 || exit 1

# ========= Start command =========
# - Không dùng 'sh -l' (gây exit sớm, không có log)
# - Đẩy access/error log ra stdout/stderr để Render hiển thị
CMD ["sh","-c","exec gunicorn -w ${WORKERS:-2} -k uvicorn.workers.UvicornWorker src.memory_mcp_server:app --bind 0.0.0.0:${PORT:-8002} --timeout ${TIMEOUT:-0} --keep-alive ${KEEPALIVE:-5} --log-level info --access-logfile - --error-logfile -"]
