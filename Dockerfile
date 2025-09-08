# Bước 1: Chọn một "hệ điều hành" cơ bản
FROM python:3.12-slim

# Bước 2: Tạo một thư mục bên trong "hộp" Docker để chứa code
WORKDIR /app

# Bước 3: Cài đặt công cụ quản lý gói 'uv'
RUN pip install uv

# Bước 4: Sao chép file định nghĩa các thư viện vào trước
COPY requirements.txt ./

# Bước 5: Cài đặt tất cả các thư viện từ requirements.txt
# Sử dụng 'uv pip install' thay vì 'uv sync'
RUN uv pip install --system -r requirements.txt

# Bước 6: Bây giờ mới sao chép toàn bộ mã nguồn của dự án vào
COPY . .

# Bước 7: "Mở" cổng 8002 của container
EXPOSE 8002

# Bước 8: Lệnh cuối cùng để chạy server khi container khởi động
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "src.memory_mcp_server:app", "--bind", "0.0.0.0:$PORT"]
