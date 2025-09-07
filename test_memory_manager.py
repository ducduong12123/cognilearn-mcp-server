# test_memory_manager.py

import sys
import os
import time

# ... phần xử lý import ...
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.memory_manager import MemoryManager

def run_tests():
    """
    Hàm thực hiện các bài test tuần tự để kiểm tra MemoryManager.
    """
    print("--- BẮT ĐẦU KIỂM TRA MEMORY MANAGER ---")

    TEST_USER_ID = "test-user-007"

    # 1. Khởi tạo MemoryManager
    print("\n[TEST 1] Khởi tạo MemoryManager...")
    try:
        memory = MemoryManager()
        print("=> THÀNH CÔNG: Instance MemoryManager đã được tạo.")
    except Exception as e:
        print(f"=> THẤT BẠI: Không thể khởi tạo MemoryManager. Lỗi: {e}")
        return

    # 2. Dọn dẹp ký ức cũ
    print(f"\n[TEST 2] Dọn dẹp ký ức cũ của user '{TEST_USER_ID}'...")
    try:
        memory.delete_user_memory(user_id=TEST_USER_ID)
        print("=> THÀNH CÔNG: Dọn dẹp hoàn tất.")
    except Exception as e:
        print(f"=> LƯU Ý: Có thể không có ký ức cũ để xóa. Lỗi: {e}")

    # 3. Thêm ký ức mới (VỚI NỘI DUNG HOÀN TOÀN KHÁC BIỆT)
    print(f"\n[TEST 3] Thêm 2 ký ức mới và khác biệt cho user '{TEST_USER_ID}'...")
    try:
        # Ký ức 1: Một sự thật về sở thích cá nhân
        memory.add_memory(
            user_id=TEST_USER_ID,
            text_content="Học sinh này rất yêu thích lập trình và thường tham gia các cuộc thi hackathon.",
            metadata={"category": "hobby", "field": "programming"}
        )
        time.sleep(1) 
        # Ký ức 2: Một sự thật về mục tiêu nghề nghiệp
        memory.add_memory(
            user_id=TEST_USER_ID,
            text_content="Mục tiêu dài hạn của học sinh là trở thành một kỹ sư AI chuyên về xử lý ngôn ngữ tự nhiên.",
            metadata={"category": "career_goal", "field": "AI/NLP"}
        )
        print("=> THÀNH CÔNG: Đã thêm 2 ký ức.")
    except Exception as e:
        print(f"=> THẤT BẠI: Không thể thêm ký ức. Lỗi: {e}")
        return

    # 4. Lấy tất cả ký ức
    print(f"\n[TEST 4] Lấy lại tất cả ký ức của user '{TEST_USER_ID}'...")
    try:
        all_mems = memory.get_all_memories(user_id=TEST_USER_ID)
        assert len(all_mems) == 2, f"Kỳ vọng 2 ký ức, nhận được {len(all_mems)}"
        print(f"=> THÀNH CÔNG: Lấy được {len(all_mems)} ký ức.")
        print("Dữ liệu:")
        for mem in all_mems:
            print(f"  - {mem}")
    except Exception as e:
        print(f"=> THẤT BẠI: Không thể lấy tất cả ký ức. Lỗi: {e}")
        return

    # 5. Tìm kiếm ký ức liên quan (VỚI CÂU QUERY MỚI)
    print(f"\n[TEST 5] Tìm kiếm ký ức liên quan đến 'dự định tương lai'...")
    try:
        query = "Học sinh này muốn làm gì trong tương lai?"
        search_results = memory.retrieve_memories(user_id=TEST_USER_ID, query_text=query, top_k=1)
        assert len(search_results) > 0, "Không tìm thấy kết quả nào."
        assert "kỹ sư AI" in search_results[0]['text'], "Kết quả tìm kiếm không liên quan đến mục tiêu nghề nghiệp."
        print(f"=> THÀNH CÔNG: Tìm thấy ký ức liên quan:")
        print(f"  - {search_results[0]}")
    except Exception as e:
        print(f"=> THẤT BẠI: Tìm kiếm thất bại. Lỗi: {e}")
        return
        
    print("\n--- TẤT CẢ CÁC BÀI TEST ĐÃ HOÀN THÀNH ---")

run_tests()