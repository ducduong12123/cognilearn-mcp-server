# --- START OF FILE verify_vector.py ---

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import numpy as np

# --- Cấu hình ---
project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(dotenv_path=project_root / '.env')

# --- Kết nối đến Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Lỗi: Vui lòng thêm SUPABASE_URL và SUPABASE_SERVICE_KEY vào file .env.")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_vector_normalization(target_id):
    """
    Lấy vector từ Supabase và kiểm tra xem nó đã được chuẩn hóa hay chưa.
    """
    print(f"--- Đang kiểm tra vector của ID: {target_id} trên Supabase ---")
    try:
        response = supabase.table('questions3').select('vector').eq('id', target_id).single().execute()
        
        if not response.data or 'vector' not in response.data:
            print(f"Lỗi: Không tìm thấy dữ liệu hoặc vector cho ID: {target_id}")
            return

        vector = np.array(response.data['vector'])
        
        # Tính toán độ dài (L2 norm / magnitude) của vector
        magnitude = np.linalg.norm(vector)
        
        print(f"\nĐộ dài (Magnitude) của vector là: {magnitude:.6f}")
        
        if 0.999 < magnitude < 1.001:
            print("\nKẾT QUẢ: TUYỆT VỜI! Vector đã được chuẩn hóa chính xác.")
        else:
            print("\nCẢNH BÁO: VẤN ĐỀ Ở ĐÂY! Vector CHƯA được chuẩn hóa. Dữ liệu trên Supabase là dữ liệu cũ hoặc sai.")

    except Exception as e:
        print(f"Đã xảy ra lỗi khi truy vấn Supabase: {e}")


if __name__ == "__main__":
    # Sử dụng chính ID câu hỏi Elip để kiểm tra
    TARGET_QUESTION_ID = "MATH_GEO10_100" 
    verify_vector_normalization(TARGET_QUESTION_ID)