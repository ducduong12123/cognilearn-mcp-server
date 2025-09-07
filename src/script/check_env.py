import os
from dotenv import load_dotenv

print("--- BẮT ĐẦU KIỂM TRA MÔI TRƯỜNG ---")

# 1. Tính toán đường dẫn đến file .env, giống hệt script chính
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")
print(f"Đang cố gắng tải file .env từ: {DOTENV_PATH}")

# 2. Kiểm tra xem file có thực sự tồn tại ở đường dẫn đó không
if os.path.exists(DOTENV_PATH):
    print("THÀNH CÔNG: Đã tìm thấy file .env.")
else:
    print("LỖI: KHÔNG tìm thấy file .env tại đường dẫn đã tính toán.")
    print("Vui lòng kiểm tra lại cấu trúc thư mục của bạn.")
    # Dừng lại nếu không tìm thấy file
    exit()

# 3. Tải file
load_success = load_dotenv(dotenv_path=DOTENV_PATH)
if load_success:
    print("THÀNH CÔNG: Hàm load_dotenv() đã thực thi.")
else:
    print("CẢNH BÁO: Hàm load_dotenv() trả về False, có thể nó không tải được gì.")

# 4. Kiểm tra biến môi trường cụ thể
api_key = os.getenv("GEMINI_API_KEY")
print("\n--- KẾT QUẢ KIỂM TRA ---")
if api_key:
    print(f"THÀNH CÔNG: Đã tìm thấy GEMINI_API_KEY.")
    print(f"Giá trị bắt đầu bằng: {api_key[:4]}...") # In ra 4 ký tự đầu để xác nhận
else:
    print("LỖI: KHÔNG tìm thấy biến GEMINI_API_KEY trong môi trường.")
    print("Vui lòng kiểm tra lại TÊN BIẾN và NỘI DUNG bên trong file .env của bạn.")

print("\n--- KẾT THÚC KIỂM TRA ---")