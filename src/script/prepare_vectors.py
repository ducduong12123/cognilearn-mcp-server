# --- START OF FILE prepare_vectors.py (phiên bản Gọi API Hugging Face) ---

import requests
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# --- Cấu hình ---
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / '.env')

# Tên mô hình chuyên dụng từ Hugging Face
EMBEDDING_MODEL_NAME = "math-similarity/Bert-MLM_arXiv-MP-class_zbMath"
# API URL của Hugging Face cho tác vụ feature-extraction (tạo embedding)
# Quay lại sử dụng endpoint đúng tác vụ
# Sử dụng endpoint trực tiếp của mô hình
API_URL = f"https://api-inference.huggingface.co/models/{EMBEDDING_MODEL_NAME}"

INPUT_QUESTIONS_FILE = project_root / 'data' / 'raw' / 'questions.json'
OUTPUT_DB_FILE = project_root / 'data' / 'processed' / 'vector_database_huggingface_mathbert.json'

def embed_text_batch_hf(texts, api_key, max_retries=5):
    """
    Gọi API của Hugging Face để tạo vector.
    Phiên bản này sử dụng endpoint trực tiếp (/models/...) và payload chính xác 
    cho tác vụ feature-extraction, giải quyết các lỗi trước đó.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # !!! THAY ĐỔI QUAN TRỌNG: Payload cho endpoint /models/ rất đơn giản.
    # Không cần "options" hay các key phức tạp khác.
    payload = {"inputs": texts}
    
    for attempt in range(max_retries):
        wait_time = (attempt + 1) * 3
        try:
            # Gửi yêu cầu đến endpoint trực tiếp của mô hình
            response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if isinstance(result, list) and result:
                        return result
                    else:
                        print(f"Lỗi: API trả về 200 OK nhưng nội dung không hợp lệ. Thử lại sau {wait_time} giây...")
                except json.JSONDecodeError:
                    print(f"Lỗi: API trả về 200 OK nhưng nội dung không phải JSON. Thử lại sau {wait_time} giây...")
            
            elif response.status_code == 503: # Model is loading
                print(f"Model đang tải (503), sẽ thử lại sau {wait_time + 10} giây...")
                time.sleep(wait_time + 10) # Chờ lâu hơn vì model có thể lớn
            else:
                error_message = response.text
                try:
                    error_message = response.json().get("error", response.text)
                except json.JSONDecodeError: pass
                print(f"Lỗi từ API (lần thử {attempt + 1}/{max_retries}): {response.status_code} - {error_message}")

        except requests.exceptions.RequestException as e:
            print(f"Lỗi kết nối (lần thử {attempt + 1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            time.sleep(wait_time)

    print("!! Thất bại sau nhiều lần thử. Bỏ qua lô này.")
    return None

def main():
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_api_key:
        print("Lỗi: Không tìm thấy HUGGINGFACE_API_KEY trong file .env.")
        return

    try:
        with open(INPUT_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file đầu vào tại: {INPUT_QUESTIONS_FILE}")
        return

    vector_database = {}
    total_questions = len(questions)
    
    # API của HF có thể xử lý batch size lớn hơn một chút
    batch_size = 50 
    
    print(f"Bắt đầu quá trình embedding cho {total_questions} câu hỏi bằng API của {EMBEDDING_MODEL_NAME}...")

    for i in range(0, total_questions, batch_size):
        batch = questions[i:i + batch_size]
        
        print(f"Đang xử lý lô từ câu {i+1} đến {i+len(batch)}...")

        texts_to_embed = []
        for q in batch:
            tags = q.get('tags', {})
            topic = tags.get('topic', '')
            sub_topics = ", ".join(q['tags'].get('sub_topic', []))
            content = q.get('content', '')
            
            combined_text = f"Chủ đề chính: {topic}. Dạng toán: {sub_topics}. {topic}. {content}"
            texts_to_embed.append(combined_text)

        embeddings = embed_text_batch_hf(texts_to_embed, hf_api_key)
        
        if embeddings and isinstance(embeddings, list) and len(embeddings) == len(batch):
            ids_in_batch = [q['id'] for q in batch]
            for idx, q_id in enumerate(ids_in_batch):
                original_question = batch[idx]
                answer_info_obj = original_question.get('answer_info', {})

                vector_database[q_id] = {
                    "content": original_question.get('content'),
                    "vector": embeddings[idx], # API đã trả về list, không cần .tolist()
                    "tags": original_question.get('tags', {}),
                    "answer_info": answer_info_obj,
                    "correct_answer": answer_info_obj.get('correct_answer')
                }
        else:
            print(f"!! Cảnh báo: Lô từ câu {i+1} đến {i+len(batch)} xử lý thất bại.")
        
        # Thêm một khoảng nghỉ nhỏ để không spam API
        time.sleep(1)

    OUTPUT_DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(vector_database, f, ensure_ascii=False, indent=4)

    print(f"\nHoàn tất! Đã lưu database vector mới vào file '{OUTPUT_DB_FILE}'.")

if __name__ == "__main__":
    main()