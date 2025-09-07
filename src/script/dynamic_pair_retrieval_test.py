import numpy as np
import json
from pathlib import Path
from itertools import combinations

# --- Cấu hình ---
project_root = Path(__file__).parent.parent.parent
VECTOR_DB_FILE = project_root / 'data' / 'processed' / 'vector_database_gemini_final2.json'

# Ngưỡng độ tương đồng để coi là một "cặp đáng quan tâm"
SIMILARITY_THRESHOLD = 0.75

# --- Hàm tính toán (không đổi) ---
def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

# --- Main Script ---
def main():
    # 1. Tải "Bản đồ Kiến thức" (Vector DB) vào bộ nhớ
    try:
        with open(VECTOR_DB_FILE, 'r', encoding='utf-8') as f:
            vector_db = json.load(f)
        print(f"Đã tải thành công {len(vector_db)} vector từ cơ sở dữ liệu.\n")
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file cơ sở dữ liệu vector tại: {VECTOR_DB_FILE}")
        return

    # 2. Giả lập một bài làm của học sinh
    # Đây là danh sách các ID câu hỏi mà một học sinh đã làm trong bài thi.
    student_exam_submission = [
        "MATH_ALG_001", 
        "PHYS_MECHANICS_001",
        "MATH_ALG_003", 
        "PROG_PYTHON_001",
        "MATH_GEOMETRY_001"
    ]
    print(f"Giả lập bài làm của học sinh gồm các câu hỏi: {student_exam_submission}\n")
    print("--- Bắt đầu quá trình truy xuất động theo cặp ---")

    # 3. Tạo tất cả các cặp câu hỏi có thể có từ bài làm
    question_pairs = list(combinations(student_exam_submission, 2))
    print(f"Đã tạo ra {len(question_pairs)} cặp câu hỏi từ bài làm để phân tích.")

    found_pairs = []

    # 4. Lặp qua từng cặp, tra cứu vector và tính toán độ tương đồng
    for q1_id, q2_id in question_pairs:
        # Lấy vector đã được tính sẵn từ DB
        v1 = vector_db.get(q1_id, {}).get('vector')
        v2 = vector_db.get(q2_id, {}).get('vector')

        if not v1 or not v2:
            print(f"Cảnh báo: Không tìm thấy vector cho cặp ({q1_id}, {q2_id}). Bỏ qua.")
            continue
        
        # Tính toán độ tương đồng
        similarity = cosine_similarity(v1, v2)

        # 5. Chỉ giữ lại những cặp có độ tương đồng cao
        if similarity >= SIMILARITY_THRESHOLD:
            found_pairs.append({
                "pair": (q1_id, q2_id),
                "similarity": similarity
            })
            print(f"  -> Phát hiện cặp tương đồng cao: ({q1_id}, {q2_id}) - Độ tương đồng: {similarity:.4f}")

    print("\n--- Kết quả Phân tích ---")
    if not found_pairs:
        print("Không tìm thấy cặp câu hỏi nào có độ tương đồng cao trong bài làm này.")
    else:
        print(f"Hệ thống đã xác định được {len(found_pairs)} cặp câu hỏi có cấu trúc tương tự để phân tích 'Hiệu ứng Học tập':")
        for item in found_pairs:
            print(f"  - Cặp: {item['pair'][0]} và {item['pair'][1]}")

if __name__ == "__main__":
    main()