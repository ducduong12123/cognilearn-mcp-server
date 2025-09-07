# --- START OF FILE find_similar.py (Phiên bản 4.0 - Chỉ trả về ID) ---

import os
from pathlib import Path
from typing import List
from uuid import UUID

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, responses
from pydantic import BaseModel, Field
from supabase import create_client, Client, PostgrestAPIResponse

# ... (Phần cấu hình và khởi tạo giữ nguyên) ...
project_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=project_root / '.env')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Lỗi: Vui lòng thêm SUPABASE_URL và SUPABASE_SERVICE_KEY vào file .env.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="CogniLearn - Test Generation Service",
    description="API chuyên dụng để tạo bài kiểm tra từ các câu hỏi hạt giống. Chỉ trả về danh sách ID.",
    version="4.0.0",
)

class TestGenerationRequest(BaseModel):
    seed_question_ids: List[UUID] = Field(...)
    questions_per_topic: int = Field(3, gt=0)

@app.post("/tests/generate", tags=["Test Generation"], response_model=List[UUID])
async def generate_test(request: TestGenerationRequest):
    """
    Nhận vào danh sách ID hạt giống, tìm các câu hỏi tương đồng,
    và trả về một danh sách phẳng (flat list) chứa TẤT CẢ các ID câu hỏi (bao gồm cả hạt giống).
    """
    print(f"\n--- Bắt đầu yêu cầu tạo bài kiểm tra cho {len(request.seed_question_ids)} chủ đề ---")
    
    final_question_ids: List[UUID] = []
    match_count = request.questions_per_topic - 1

    for seed_id in request.seed_question_ids:
        try:
            print(f"\n[Bước 1] Đang xử lý hạt giống ID: {seed_id}")
            response: PostgrestAPIResponse = supabase.table('questions').select('id, vector').eq('id', str(seed_id)).single().execute()

            if response.data is None or response.data.get('vector') is None:
                raise HTTPException(status_code=404, detail=f"Seed question with ID {seed_id} not found or has no vector.")

            source_vector = response.data.get('vector')
            print(f"[Bước 1 Hoàn tất] Đã lấy được vector cho ID: {seed_id}")

            # <<< THAY ĐỔI QUAN TRỌNG: Thêm ID của câu hỏi hạt giống vào danh sách kết quả
            final_question_ids.append(seed_id)

            if match_count > 0:
                print(f"[Bước 2] Đang tìm {match_count} ID câu hỏi tương đồng...")
                rpc_params = {
                    'query_vector': source_vector,
                    'match_count': match_count,
                    'source_id': str(seed_id)
                }
                
                similar_response: PostgrestAPIResponse = supabase.rpc('match_similar_questions', rpc_params).execute()
                
                if similar_response.data:
                    # <<< THAY ĐỔI QUAN TRỌNG: Trích xuất chỉ ID từ kết quả RPC
                    similar_ids = [item['id'] for item in similar_response.data]
                    final_question_ids.extend(similar_ids)
                    print(f"[Bước 2 Hoàn tất] Đã tìm thấy {len(similar_ids)} ID tương đồng.")
                else:
                    print(f"[Bước 2 Hoàn tất] Cảnh báo: Không tìm thấy ID tương đồng nào cho {seed_id}")

        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            print(f"\n!!!!!! ĐÃ XẢY RA LỖI KHÔNG MONG MUỐN !!!!!!")
            print(f"Lỗi khi xử lý ID: {seed_id}, Chi tiết: {e}, Loại: {type(e)}")
            raise HTTPException(status_code=500, detail=f"An internal server error occurred while processing seed ID {seed_id}.")

    print(f"\n--- Hoàn tất! Trả về tổng số {len(final_question_ids)} ID câu hỏi. ---\n")
    # <<< THAY ĐỔI QUAN TRỌNG: Trả về danh sách các UUID
    return final_question_ids

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "Test Generation Service is running"}

if __name__ == "__main__":
    print("Khởi động server API tại http://127.0.0.1:8001")
    uvicorn.run("find_similar:app", host="127.0.0.1", port=8001, reload=True)
# --- END OF FILE find_similar.py ---