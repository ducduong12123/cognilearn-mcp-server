# minimal_test.py

import sys
import os
import time

# Thêm 'src' vào path để import MemoryManager
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.memory_manager import MemoryManager

TEST_USER_ID = "test-user-minimal"

# --- BẮT ĐẦU KỊCH BẢN TEST TỐI GIẢN ---

# 1. Khởi tạo
print("--- Khởi tạo MemoryManager ---")
memory = MemoryManager()
print("   => Xong.")

# 2. Dọn dẹp
print(f"--- Dọn dẹp ký ức cũ cho user '{TEST_USER_ID}' ---")
memory.delete_user_memory(user_id=TEST_USER_ID)
print("   => Xong.")

# 3. Thêm ký ức đầu tiên và kiểm tra kết quả
print("\n--- Thêm Ký ức 1 ---")
content1 = "Học sinh này rất yêu thích lập trình và thường tham gia các cuộc thi hackathon."
result1 = memory.add_memory(user_id=TEST_USER_ID, text_content=content1)
# BƯỚC 1 THEO HƯỚNG DẪN: KIỂM TRA NỘI DUNG MEMORIES
print(f"==> 'Memories được tạo' (Kết quả trả về từ lệnh 1): {result1}")

# 4. Thêm delay
# BƯỚC 2 THEO HƯỚNG DẪN: THÊM DELAY
print("\n--- Chờ 3 giây ---")
time.sleep(3)

# 5. Thêm ký ức thứ hai và kiểm tra kết quả
print("\n--- Thêm Ký ức 2 ---")
content2 = "Mục tiêu dài hạn của học sinh là trở thành một kỹ sư AI chuyên về NLP."
result2 = memory.add_memory(user_id=TEST_USER_ID, text_content=content2)
# BƯỚC 1 THEO HƯỚNG DẪN: KIỂM TRA NỘI DUNG MEMORIES
print(f"==> 'Memories được tạo' (Kết quả trả về từ lệnh 2): {result2}")

# 6. Kiểm tra kết quả cuối cùng
print("\n--- Kiểm tra lại toàn bộ ký ức trong DB ---")
final_mems = memory.get_all_memories(user_id=TEST_USER_ID)
print(f"==> Số lượng ký ức cuối cùng: {len(final_mems)}")
if final_mems:
    print("    Nội dung:")
    for mem in final_mems:
        print(f"    - {mem.get('text')}")

print("\n--- KẾT THÚC ---")