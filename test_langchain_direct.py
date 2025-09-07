# test_langchain_direct.py

import os
from dotenv import load_dotenv

print("--- BẮT ĐẦU BÀI TEST CÔ LẬP LANGCHAIN ---")

# Tải biến môi trường
print("[1] Đang tải biến môi trường từ file .env...")
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    print("=> THẤT BẠI: Không tìm thấy GOOGLE_API_KEY trong file .env.")
else:
    print("=> THÀNH CÔNG: Đã tải GOOGLE_API_KEY.")

# Bước quan trọng nhất: Thử import và khởi tạo đối tượng gây lỗi
print("\n[2] Đang thử import và khởi tạo ChatGoogleGenerativeAI...")
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    print("   - Import ChatGoogleGenerativeAI thành công.")
    
    google_llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=google_api_key,
        temperature=0.7
    )
    
    print("   - Khởi tạo ChatGoogleGenerativeAI thành công.")
    print("\n=> KIỂM TRA THÀNH CÔNG! Môi trường LangChain và Google GenAI hoạt động bình thường.")
    
except ImportError as e:
    print(f"\n=> KIỂM TRA THẤT BẠI! Lỗi ImportError khi cố gắng import.")
    print(f"   Lỗi cụ thể: {e}")
    print("   Điều này xác nhận vấn đề nằm ở môi trường hoặc thư viện LangChain/Google.")
    
except Exception as e:
    print(f"\n=> KIỂM TRA THẤT BẠI! Lỗi không xác định khi khởi tạo.")
    print(f"   Lỗi cụ thể: {e}")

print("\n--- KẾT THÚC BÀI TEST ---")