import duckdb
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import uuid

# --- GIAI ĐOẠN 1: THIẾT LẬP MÔI TRƯỜNG MÔ PHỎNG (Không đổi) ---

print("Loading embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
VECTOR_DIM = 384

con = duckdb.connect('cognilearn_memory_test.db')
con.execute(f"""
CREATE OR REPLACE TABLE memories (
    id UUID PRIMARY KEY,
    user_id VARCHAR,
    content VARCHAR,
    embedding FLOAT[{VECTOR_DIM}],
    metadata JSON,
    created_at TIMESTAMP,
    importance FLOAT
);
""")

# --- CÁC HÀM TIỆN ÍCH (Không đổi) ---
def get_embedding(text):
    return embedding_model.encode(text)

def add_memory(user_id, content, metadata=None, importance=0.5):
    embedding = get_embedding(content)
    metadata_str = json.dumps(metadata or {})
    df = pd.DataFrame([{
        "id": uuid.uuid4(),
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
    query = f"""
    SELECT *, list_cosine_similarity(embedding, {query_embedding.tolist()}) AS similarity
    FROM memories
    WHERE user_id = '{user_id}'
    ORDER BY similarity DESC
    LIMIT {top_k}
    """
    return con.execute(query).fetchdf()

def metadata_search(user_id, metadata_filter):
    key, value = list(metadata_filter.items())[0]
    query = f"""
    SELECT *
    FROM memories
    WHERE user_id = '{user_id}' AND json_extract_string(metadata, '$.{key}') = '{value}'
    """
    return con.execute(query).fetchdf()

# --- GIAI ĐOẠN 2: TẠO DỮ LIỆU (Không đổi) ---

print("\nPopulating memories for student 'An'...")
add_memory("An", "Làm sai câu HH KG về thể tích khối chóp.", 
           metadata={"type": "exam_weakness", "topic": "space_geometry"}, importance=0.9)
add_memory("An", "Hỏi về cách áp dụng định lý Vi-et.", 
           metadata={"type": "student_question", "topic": "vi-et-theorem"}, importance=0.6)
add_memory("An", "Đạt 9 điểm bài kiểm tra đại số, làm tốt câu Vi-et.", 
           metadata={"type": "exam_strength", "topic": "vi-et-theorem"}, importance=0.8)
add_memory("An", "Nói rằng em ấy thích lập trình và muốn tìm hiểu về AI.", 
           metadata={"type": "student_interest", "topic": "programming"}, importance=0.7)
add_memory("An", "Lại mất điểm câu HH KG về góc giữa hai mặt phẳng.", 
           metadata={"type": "exam_weakness", "topic": "space_geometry"}, importance=0.95)

# --- GIAI ĐOẠN 3: "WORKING MEMORY COMPOSER" (PHIÊN BẢN NÂNG CẤP) ---

# Cải tiến 1: Phân loại Ý định
def classify_intent(query):
    query = query.lower()
    if "ngành gì" in query or "nghề nghiệp" in query or "sau này" in query:
        return "career_advisory"
    if "khó" in query or "không hiểu" in query or "bài tập" in query:
        return "academic_struggle"
    return "general_inquiry"

def get_synthesized_context_for_an(query):
    print("\n========================================================")
    print(f"QUERY: '{query}'")
    print("========================================================")

    # 3.1. Phân loại ý định trước
    intent = classify_intent(query)
    print(f"\n[Step 1.1: Intent Classified as '{intent}']")

    # 3.2. Truy xuất đa chiều ĐỘNG
    print("\n[Step 1.2: Dynamic Multi-faceted Retrieval]")
    
    # Truy vấn ngữ nghĩa luôn được thực hiện
    semantic_results = vector_search("An", query, top_k=2)
    print(f"\nSemantic Search Results:\n{semantic_results[['content', 'similarity']]}")
    
    # Cải tiến 2: Truy vấn có cấu trúc động
    structural_results = pd.DataFrame() # Khởi tạo rỗng
    if intent == "career_advisory":
        print("\n-> Dynamic search: Looking for interests and strengths.")
        interest_results = metadata_search("An", {"type": "student_interest"})
        strength_results = metadata_search("An", {"type": "exam_strength"})
        structural_results = pd.concat([interest_results, strength_results])
    elif intent == "academic_struggle":
        print("\n-> Dynamic search: Looking for weaknesses.")
        structural_results = metadata_search("An", {"type": "exam_weakness"})
    
    if not structural_results.empty:
        print(f"\nStructural Search Results:\n{structural_results[['content', 'metadata']]}")

    # 3.3. Tập hợp, Lọc và Xếp hạng theo Ngữ cảnh
    print("\n[Step 2: Contextual Rank & Filter]")
    combined_df = pd.concat([semantic_results, structural_results]).drop_duplicates(subset=['id'])
    
    combined_df['similarity'] = combined_df['similarity'].fillna(0)

    # Cải tiến 3: Logic xếp hạng theo ngữ cảnh
    if intent == "career_advisory":
        w_similarity, w_importance = 0.7, 0.3 # Ưu tiên độ tương đồng ngữ nghĩa
    else: # academic_struggle or general
        w_similarity, w_importance = 0.3, 0.7 # Ưu tiên độ quan trọng của ký ức
    print(f"\nUsing weights: similarity={w_similarity}, importance={w_importance}")

    combined_df['relevance_score'] = (combined_df['similarity'] * w_similarity) + (combined_df['importance'] * w_importance)
    
    final_memories_df = combined_df.sort_values(by='relevance_score', ascending=False).head(4)
    print(f"\nTop memories selected for synthesis:\n{final_memories_df[['content', 'relevance_score']]}")
    
    # 3.4. Tổng hợp và Diễn giải (Không đổi)
    print("\n[Step 3: Synthesize & Narrate]")
    if final_memories_df.empty:
        context = "Ghi chú cho Mentor: Không có ký ức nào đặc biệt liên quan đến vấn đề này."
    else:
        memory_list = final_memories_df['content'].tolist()
        
        # Mô phỏng việc gọi LLM để tổng hợp
        context = "Ghi chú cho Mentor:\n"
        context += "Dựa trên lịch sử, hãy lưu ý các điểm sau:\n"
        for mem in memory_list:
            context += f"- {mem}\n"
        
        # Thêm gợi ý thông minh hơn
        if intent == "career_advisory":
            context += "=> Gợi ý: Học sinh có thiên hướng rõ ràng về lập trình/AI. Hãy khai thác điểm này."
        elif intent == "academic_struggle":
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