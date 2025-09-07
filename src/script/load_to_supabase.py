# --- START OF FILE load_to_supabase.py ---

import json
from pathlib import Path
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# --- Cấu hình ---
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / '.env')

# Đường dẫn đến file JSON đã được embedding
# !!! QUAN TRỌNG: Đảm bảo tên file này khớp với file output của script prepare_vectors.py
VECTOR_DB_FILE = project_root / 'data' / 'processed' / 'final_vector_database_finetuned.json'

# --- Kết nối đến Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Lỗi: Vui lòng thêm SUPABASE_URL và SUPABASE_SERVICE_KEY vào file .env.")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Main Script ---
def main():
    # 1. Đọc file JSON
    try:
        with open(VECTOR_DB_FILE, 'r', encoding='utf-8') as f:
            vector_db = json.load(f)
        print(f"Đã đọc thành công {len(vector_db)} câu hỏi từ file JSON.")
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {VECTOR_DB_FILE}")
        return

    # 2. Chuẩn bị dữ liệu để nạp
    data_to_insert = []
    for q_id, data in vector_db.items():
        # === THAY ĐỔI QUAN TRỌNG: THÊM TẤT CẢ CÁC TRƯỜNG DỮ LIỆU ===
        # Tên key ở đây phải khớp chính xác với tên cột trong Supabase
        data_to_insert.append({
            "id": q_id,
            "content": data.get('content'),
            "tags": data.get('tags'),         # Supabase tự động xử lý object Python -> jsonb
            "vector": data.get('vector'),
            "answer_info": data.get('answer_info'), # Dữ liệu đáp án
            "correct_answer": data.get('correct_answer') # Đáp án đúng
        })
        # =========================================================

    # 3. Nạp dữ liệu vào Supabase bằng .upsert()
    print("Bắt đầu nạp dữ liệu vào Supabase...")
    try:
        # Gửi dữ liệu theo lô để hiệu quả hơn
        response = supabase.table('questions').insert(data_to_insert).execute()
        
        if response.data:
             print(f"Thành công! Đã nạp/cập nhật {len(response.data)} bản ghi vào bảng 'questions'.")
        else:
             print("Có lỗi xảy ra trong quá trình nạp dữ liệu. Không có dữ liệu trả về.")
             # Để debug: print("Phản hồi từ Supabase:", response)

    except Exception as e:
        print(f"Đã xảy ra lỗi nghiêm trọng khi kết nối hoặc nạp dữ liệu: {e}")

if __name__ == "__main__":
    main()