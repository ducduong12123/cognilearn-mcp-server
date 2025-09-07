# --- START OF FILE memory_service.py ---

import os
import uuid
import time
import re
from typing import List, Dict, Any

from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

# Tải các biến môi trường từ file .env
load_dotenv()

class MemoryService:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
        self.supabase_client: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized for MemoryService.")

        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY must be set in .env file")
        genai.configure(api_key=google_api_key)
        self.embedding_model_name = "models/text-embedding-004"
        print(f"✅ Google AI (genai) client initialized for MemoryService.")

    def _normalize_text(self, text: str) -> str:
        """
        Hàm chuẩn hóa văn bản để cải thiện độ chính xác của tìm kiếm vector.
        """
        text = text.lower()
        text = re.sub(r'\b(tôi|tên tôi|của tôi)\b', 'người dùng', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text

    def _get_embedding(self, text: str, task_type: str) -> List[float]:
        """Tạo vector embedding cho một đoạn văn bản."""
        normalized_text = self._normalize_text(text)
        print(f"   - Normalizing '{text}' -> '{normalized_text}'")
        
        normalized_text = normalized_text[:1024]
        
        try:
            result = genai.embed_content(
                model=self.embedding_model_name,
                content=normalized_text,
                task_type=task_type
            )
            return result['embedding']
        except Exception as e:
            print(f"Error getting embedding for text: '{normalized_text}'. Error: {e}")
            # Trả về một vector zero nếu có lỗi
            return [0.0] * 768

    def add_memory(self, user_id: str, content: str, metadata: Dict[str, Any] = None, importance: float = 0.5):
        """Thêm một ký ức mới vào cơ sở dữ liệu."""
        print(f"Adding memory for user '{user_id}' with content: '{content}'")
        try:
            embedding = self._get_embedding(content, "RETRIEVAL_DOCUMENT")
            
            # <<< SỬA ĐỔI CHÍNH: Sửa 'user_id' thành 'userid' >>>
            self.supabase_client.table("memories").insert({
                "id": str(uuid.uuid4()),
                "userid": user_id, 
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {},
                "importance": importance
            }).execute()
            
            print(f"✅ Memory add request sent for user {user_id}.")
            # Có thể không cần sleep trong môi trường production
            # time.sleep(1) 
        except Exception as e:
            print(f"❌ Error adding memory for user {user_id}: {e}")

    def retrieve_similar_memories(self, user_id: str, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Truy xuất các ký ức tương đồng nhất."""
        print(f"Retrieving memories for user '{user_id}' with query: '{query_text}'")
        
        min_similarity_threshold = 0.5 

        try:
            query_embedding = self._get_embedding(query_text, "RETRIEVAL_QUERY")
            # Giả định bạn có một hàm RPC tên là 'match_memories'
            results = self.supabase_client.rpc('match_memories', {
                'p_user_id': user_id,
                'query_embedding': query_embedding,
                'match_count': top_k,
                'min_similarity': min_similarity_threshold
            }).execute()
            
            if results.data:
                print(f"✅ Found {len(results.data)} memories above similarity threshold {min_similarity_threshold}.")
            else:
                print(f"❌ No memories found above similarity threshold {min_similarity_threshold}.")

            return results.data
        except Exception as e:
            print(f"❌ Error retrieving memories: {e}")
            return []

# --- Phần Test (phiên bản đã sửa tên cột và dùng UUID hợp lệ) ---
if __name__ == '__main__':
    print("\n" + "="*50)
    print("--- RUNNING MEMORY SERVICE STANDALONE TEST ---")
    print("="*50 + "\n")
    
    try:
        memory_service = MemoryService()
        
        # <<< SỬA ĐỔI: Sử dụng một UUID hợp lệ để test >>>
        # !!! QUAN TRỌNG: Hãy thay thế UUID này bằng một 'id' người dùng THỰC TẾ
        # đang có trong bảng 'profiles' của bạn để tránh lỗi khóa ngoại.
        test_user_id = "d983633e-2eb0-4d87-9a72-801f4fd92c14"
        print(f"--- Using Test User ID: {test_user_id} ---")

        # 1. Xóa ký ức cũ để đảm bảo test sạch
        print(f"\n[Step 1] Cleaning up old test memories for user: {test_user_id}...")
        # <<< SỬA ĐỔI: Sửa 'user_id' thành 'userid' >>>
        memory_service.supabase_client.table("memories").delete().eq("userid", test_user_id).execute()
        print("✅ Cleaned up old test memories.")

        # 2. Thêm ký ức mới
        print("\n[Step 2] Testing add_memory...")
        memory_service.add_memory(
            user_id=test_user_id,
            content="Người dùng này rất mạnh về các chủ đề Đại số cơ bản như giải phương trình.",
            metadata={"source": "test_script"},
            importance=0.9
        )
        memory_service.add_memory(
            user_id=test_user_id,
            content="Người dùng có xu hướng mắc lỗi cẩu thả ở các bài toán Hình học liên quan đến vector.",
            metadata={"source": "test_script"},
            importance=0.8
        )

        # 3. Truy xuất ký ức
        print("\n[Step 3] Testing retrieve_similar_memories...")
        retrieved_memories = memory_service.retrieve_similar_memories(
            user_id=test_user_id,
            query_text="Điểm yếu của người dùng này là gì?"
        )
        
        if retrieved_memories:
            print("\n--- Retrieved Memories ---")
            for i, mem in enumerate(retrieved_memories):
                print(f"Result #{i+1}:")
                print(f"  Content: {mem['content']}")
                print(f"  Similarity: {mem['similarity']:.4f}")
                print("-" * 20)
        else:
            print("\n--- No similar memories retrieved. ---")

        print("\n" + "="*50)
        print("--- TEST FINISHED SUCCESSFULLY ---")
        print("="*50 + "\n")

    except Exception as e:
        print("\n" + "!"*50)
        print(f"--- AN ERROR OCCURRED DURING THE TEST ---")
        print(f"Error: {e}")
        print("!"*50 + "\n")

# --- END OF FILE memory_service.py ---