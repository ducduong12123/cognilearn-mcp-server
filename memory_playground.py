import duckdb
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import uuid # <-- ĐÃ THÊM

# --- GIAI ĐOẠN 1: THIẾT LẬP MÔI TRƯỜNG MÔ PHỎNG ---

# 1.1. Mô phỏng Embedding Model (dùng model nhỏ chạy trên máy)
print("Loading embedding model...")
# all-MiniLM-L6-v2 là một model nhỏ, nhanh, kích thước vector là 384
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
VECTOR_DIM = 384

# 1.2. Mô phỏng CSDL Supabase bằng DuckDB
# DuckDB sẽ tạo một file CSDL ngay trong thư mục, rất tiện lợi
con = duckdb.connect('cognilearn_memory_test.db')

# Tạo bảng memories nếu chưa có
con.execute(f"""
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY,
    user_id VARCHAR,
    content VARCHAR,
    embedding FLOAT[{VECTOR_DIM}],
    metadata JSON,
    created_at TIMESTAMP,
    importance FLOAT
);
""")

# 1.3. Mô phỏng MemoryService
def get_embedding(text):
    return embedding_model.encode(text)

def add_memory(user_id, content, metadata=None, importance=0.5):
    embedding = get_embedding(content)
    # DuckDB không có kiểu JSON sẵn, ta lưu dưới dạng string
    metadata_str = json.dumps(metadata or {})
    
    # Tạo một DataFrame để dễ dàng insert
    df = pd.DataFrame([{
        "id": uuid.uuid4(), # <-- ĐÃ SỬA
        "user_id": user_id,
        "content": content,
        "embedding": embedding,
        "metadata": metadata_str,
        "created_at": pd.Timestamp.now(),
        "importance": importance
    }])
    con.execute("INSERT INTO memories SELECT * FROM df")
    print(f"-> Added memory for {user_id}: '{content}'")

def vector_search(user_id, query_text, top_k=3):
    query_embedding = get_embedding(query_text)
    # DuckDB dùng hàm list_cosine_similarity để so sánh vector
    query = f"""
    SELECT *, list_cosine_similarity(embedding, {query_embedding.tolist()}) AS similarity
    FROM memories
    WHERE user_id = '{user_id}'
    ORDER BY similarity DESC
    LIMIT {top_k}
    """
    return con.execute(query).fetchdf()

def metadata_search(user_id, metadata_filter):
    # Tìm kiếm chính xác dựa trên metadata
    key, value = list(metadata_filter.items())[0]
    # json_extract_string là cách truy vấn JSON trong DuckDB
    query = f"""
    SELECT *
    FROM memories
    WHERE user_id = '{user_id}' AND json_extract_string(metadata, '$.{key}') = '{value}'
    """
    return con.execute(query).fetchdf()

# --- GIAI ĐOẠN 2: TẠO DỮ LIỆU GIẢ LẬP CHO HỌC SINH "AN" ---

print("\nPopulating memories for student 'An'...")
# Xóa dữ liệu cũ để chạy lại
con.execute("DELETE FROM memories WHERE user_id = 'An'")

# Tuần 1: Gặp khó khăn
add_memory("An", "Làm sai câu HH KG về thể tích khối chóp.", 
           metadata={"type": "exam_weakness", "topic": "space_geometry"}, importance=0.9)
add_memory("An", "Hỏi về cách áp dụng định lý Vi-et.", 
           metadata={"type": "student_question", "topic": "vi-et-theorem"}, importance=0.6)

# Tuần 2: Thể hiện sự tiến bộ và sở thích
add_memory("An", "Đạt 9 điểm bài kiểm tra đại số, làm tốt câu Vi-et.", 
           metadata={"type": "exam_strength", "topic": "vi-et-theorem"}, importance=0.8)
add_memory("An", "Nói rằng em ấy thích lập trình và muốn tìm hiểu về AI.", 
           metadata={"type": "student_interest", "topic": "programming"}, importance=0.7)

# Hôm qua: Lại gặp vấn đề cũ
add_memory("An", "Lại mất điểm câu HH KG về góc giữa hai mặt phẳng.", 
           metadata={"type": "exam_weakness", "topic": "space_geometry"}, importance=0.95)


# --- GIAI ĐOẠN 3: MÔ PHỎNG "WORKING MEMORY COMPOSER" ---

def get_synthesized_context_for_an(query):
    print("\n========================================================")
    print(f"QUERY: '{query}'")
    print("========================================================")

    # 3.1. Truy xuất đa chiều
    print("\n[Step 1: Multi-faceted Retrieval]")
    
    # Truy vấn ngữ nghĩa
    semantic_results = vector_search("An", query, top_k=2)
    print(f"\nSemantic Search Results:\n{semantic_results[['content', 'similarity']]}")
    
    # Truy vấn có cấu trúc (luôn tìm điểm yếu cố hữu)
    weakness_results = metadata_search("An", {"type": "exam_weakness"})
    print(f"\nStructural Search for 'weakness':\n{weakness_results[['content', 'metadata']]}")

    # 3.2. Tập hợp và Lọc
    print("\n[Step 2: Rank & Filter]")
    combined_df = pd.concat([semantic_results, weakness_results]).drop_duplicates(subset=['id'])
    
    # Tạo "sức mạnh" của ký ức = độ tương đồng + độ quan trọng
    # Gán similarity=0 cho các kết quả từ metadata search để không bị lỗi
    combined_df['similarity'] = combined_df['similarity'].fillna(0)
    combined_df['relevance_score'] = combined_df['similarity'] + combined_df['importance']
    
    final_memories_df = combined_df.sort_values(by='relevance_score', ascending=False).head(4)
    print(f"\nTop memories selected for synthesis:\n{final_memories_df[['content', 'relevance_score']]}")
    
    # 3.3. Tổng hợp và Diễn giải
    print("\n[Step 3: Synthesize & Narrate]")
    if final_memories_df.empty:
        context = "Ghi chú cho Mentor: Không có ký ức nào đặc biệt liên quan đến vấn đề này."
    else:
        memory_list = final_memories_df['content'].tolist()
        
        # Mô phỏng việc gọi LLM để tổng hợp
        # Ở đây ta chỉ dùng f-string đơn giản
        context = "Ghi chú cho Mentor:\n"
        context += "Dựa trên lịch sử, hãy lưu ý các điểm sau:\n"
        for mem in memory_list:
            context += f"- {mem}\n"
        context += "=> Gợi ý: Vấn đề về Hình học không gian là một điểm yếu cố hữu và nghiêm trọng."

    print("\n----------------- FINAL CONTEXT -----------------")
    print(context)
    print("-------------------------------------------------")
    return context

# --- GIAI ĐOẠN 4: CHẠY THỬ NGHIỆM ---

# Kịch bản 1: An hỏi một câu chung chung về hình học
get_synthesized_context_for_an("Em thấy hình học hơi khó, thầy ạ.")

# Kịch bản 2: An hỏi về định hướng nghề nghiệp
get_synthesized_context_for_an("Em nên học ngành gì sau này?")

con.close()