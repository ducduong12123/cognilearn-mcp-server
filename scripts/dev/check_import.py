# check_import.py

import sys
import os

def run_diagnostics():
    print("--- BẮT ĐẦU CHẨN ĐOÁN MÔI TRƯỜNG PYTHON ---")
    
    print(f"\n[1] Phiên bản Python đang chạy:\n{sys.version}")
    print(f"\n[2] Đường dẫn thực thi Python (quan trọng):\n{sys.executable}")
    
    # Kiểm tra xem chúng ta có đang ở trong venv không
    is_in_venv = sys.prefix != sys.base_prefix
    print(f"\n[3] Có đang ở trong môi trường ảo (venv) không? {'CÓ' if is_in_venv else 'KHÔNG'}")

    print("\n[4] Kiểm tra thư viện 'google':")
    try:
        import google
        # In ra đường dẫn của file __init__.py của package 'google'
        google_path = os.path.dirname(google.__file__)
        print(f"   => THÀNH CÔNG: Thư viện 'google' được import từ:\n      {google_path}")
    except ImportError:
        print("   => THẤT BẠI: Không thể import thư viện 'google'.")
        print("--- CHẨN ĐOÁN KẾT THÚC ---")
        return
    except Exception as e:
        print(f"   => LỖI BẤT NGỜ: {e}")
        print("--- CHẨN ĐOÁN KẾT THÚC ---")
        return

    print("\n[5] Kiểm tra module 'google.generativeai' (đây là nơi gây lỗi):")
    try:
        # Chúng ta thử import chính module gây ra lỗi
        import google.generativeai as genai
        genai_path = os.path.dirname(genai.__file__)
        print(f"   => THÀNH CÔNG: Module 'google.generativeai' được import từ:\n      {genai_path}")
    except ImportError as e:
        print(f"   => THẤT BẠI: Không thể import 'google.generativeai'.\n      Lỗi cụ thể: {e}")
    except Exception as e:
        print(f"   => LỖI BẤT NGỜ KHÁC: {e}")
        
    print("\n--- CHẨN ĐOÁN KẾT THÚC ---")

if __name__ == "__main__":
    run_diagnostics()