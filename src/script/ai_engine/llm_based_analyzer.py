# --- START OF FILE llm_based_analyzer.py ---

import os
import json
import sys
from pathlib import Path
from uuid import UUID

import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client, Client

# ==============================================================================
# === XỬ LÝ ĐƯỜNG DẪN ĐỂ IMPORT =================================================
# ==============================================================================
# Thêm thư mục gốc của dự án ('src') vào sys.path để có thể import các module khác
project_root = Path(__file__).resolve().parent.parent.parent.parent
src_root = project_root / 'src'
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))
    print(f"Đã thêm '{src_root}' vào sys.path")

# Import MemoryService thực sự từ vị trí của nó
from core.memory_service import MemoryService

# ==============================================================================
# === TẢI BIẾN MÔI TRƯỜNG ======================================================
# ==============================================================================
load_dotenv(dotenv_path=project_root / '.env')

# ==============================================================================
# === LỚP LOGIC CHÍNH ==========================================================
# ==============================================================================
class LLMAnalyticsEngine:
    def __init__(self):
        # --- Khởi tạo kết nối cho riêng LLMAnalyticsEngine ---
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        supabase_url: str = os.getenv("SUPABASE_URL")
        supabase_key: str = os.getenv("SUPABASE_SERVICE_KEY")
        if not self.google_api_key or not supabase_url or not supabase_key:
            raise ValueError("Thiếu các biến môi trường cần thiết cho LLMAnalyticsEngine.")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        genai.configure(api_key=self.google_api_key)
        
        # --- Cấu hình model Gemini cho việc phân tích ---
        generation_config = {
            "temperature": 0.4,
            "max_output_tokens": 8192, # Tăng giới hạn token để tránh bị cắt cụt
        }
        # Cấu hình an toàn, có thể nới lỏng nếu gặp lỗi chặn
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite", 
            generation_config=generation_config, 
            safety_settings=safety_settings
        )
        
        # Khởi tạo MemoryService thực sự, nó sẽ tự quản lý các kết nối của riêng nó.
        self.memory_service = MemoryService()
        
        print("✅ LLMAnalyticsEngine đã được khởi tạo thành công.")

    def _get_submission_data(self, contest_result_id: str) -> dict | None:
        """Lấy dữ liệu bài làm (log, userId, tên bài thi) từ Supabase."""
        print(f"Đang lấy dữ liệu bài làm từ Supabase cho ID: {contest_result_id}...")
        try:
            response = self.supabase.table('contest_results').select('questions, userId, name').eq('id', contest_result_id).single().execute()
            if response.data and response.data.get('questions'):
                print("Lấy dữ liệu bài làm thành công.")
                return response.data
            return None
        except Exception as e:
            print(f"Lỗi khi truy vấn 'contest_results': {e}")
            return None

    def _get_user_profile(self, user_id: str) -> dict | None:
        """Lấy tên học sinh từ bảng 'profiles'."""
        if not user_id: return None
        print(f"Đang lấy profile cho userId: {user_id}...")
        try:
            response = self.supabase.table('profiles').select('name').eq('id', user_id).single().execute()
            if response.data:
                print(f"Tìm thấy tên học sinh: {response.data.get('name')}")
                return response.data
            return None
        except Exception as e:
            print(f"Lỗi khi truy vấn 'profiles': {e}")
            return None

    def _build_prompt(self, student_log: list, student_name: str) -> str:
        """Xây dựng prompt "Chuyên gia Vận dụng cao" chi tiết cho LLM."""
        print("Đang xây dựng prompt phân tích nhận thức sâu (phiên bản Chuyên gia Vận dụng cao)...")
        log_string = json.dumps(student_log, indent=2, ensure_ascii=False)
        
        return f"""
        **YÊU CẦU QUAN TRỌNG NHẤT:**
        Nhiệm vụ của bạn là trả về MỘT ĐỐI TƯỢNG JSON HỢP LỆ DUY NHẤT. TUYỆT ĐỐI KHÔNG được có bất kỳ văn bản giới thiệu, giải thích, hay lời chào nào nằm ngoài đối tượng JSON. Phản hồi của bạn phải bắt đầu bằng ký tự `{{` và kết thúc bằng ký tự `}}`.

        **VAI TRÒ:**
        Với vai trò là một chuyên gia phân tích giáo dục và tâm lý học nhận thức, hãy phân tích dữ liệu log dưới đây của học sinh "{student_name}".

        **DỮ LIỆU LOG LÀM BÀI:**
        ```json
        {log_string}
        ```

        **CẤU TRÚC JSON MONG MUỐN:**
        Đối tượng JSON mà bạn tạo ra phải chứa hai trường chính: `structured_data_report` và `human_readable_report`.

        ---
        **1. TRƯỜNG `structured_data_report` (Dành cho Dashboard của giáo viên):**
        Đây là báo cáo kỹ thuật, chi tiết. Hãy suy luận và điền vào các mục sau:
        
        - **`overallPerformance`**: Tóm tắt hiệu suất tổng thể (totalQuestions, correctAnswers, accuracyRate, averageTimePerQuestion).
        - **`topicPerformance`**: Phân tích hiệu suất theo từng `topic`, bao gồm tỷ lệ đúng và ghi chú ngắn gọn về điểm mạnh/yếu.
        - **`cognitiveStrengths`**: Liệt kê các chủ đề hoặc dạng bài (`sub_topic`) mà học sinh thể hiện sự nắm vững. Cung cấp bằng chứng cụ thể.
        - **`cognitiveWeaknesses`**:
          - **`knowledgeGaps`**: Liệt kê các `sub_topic` ở mức độ "Nhận biết" hoặc "Thông hiểu" mà học sinh bị sai.
          - **`behavioralPatterns`**: Phân tích và xác định các mẫu hình hành vi (Lỗi ẩu, Thiếu tự tin, Đoán mò, Kiệt sức).
          - **`misconceptions`**: Tìm kiếm và mô tả các quan niệm sai lầm cố hữu.
        - **`deepDiveAnalysis`**:
          - CHỈ THỰC HIỆN MỤC NÀY nếu trong log có câu hỏi với `difficulty_level` là "Vận dụng (3)" hoặc "Vận dụng cao (4)". Nếu không, hãy để mục này là một mảng rỗng `[]`.
          - Đây là một danh sách các đối tượng, mỗi đối tượng phân tích MỘT câu hỏi khó, bao gồm: `question_id`, `content`, `probableThoughtProcess`, `keySkillFailure`, và `errorClassification`.
        - **`actionableRecommendations`**: Đưa ra 2-3 gợi ý can thiệp cụ thể, mang tính "phẫu thuật" cho giáo viên.

        ---
        **2. TRƯỜNG `human_readable_report` (Dành cho Học sinh):**
        - Một chuỗi văn bản duy nhất, giọng văn thân thiện, động viên. Bao gồm: Chào hỏi, Điểm sáng, Khu vực mài giũa, Kế hoạch hành động, và lời khích lệ.

        **NHẮC LẠI YÊU CẦU CUỐI CÙNG:**
        Hãy chắc chắn rằng toàn bộ phản hồi của bạn là một khối JSON duy nhất, bắt đầu bằng `{{` và kết thúc bằng `}}`.
        """

    def analyze_submission(self, contest_result_id: str) -> dict | None:
        submission_data = self._get_submission_data(contest_result_id)
        if not submission_data:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy kết quả bài thi với ID: {contest_result_id}")

        student_log = submission_data.get("questions")
        if not student_log:
             raise HTTPException(status_code=404, detail=f"Không có log câu hỏi cho bài thi ID: {contest_result_id}")

        user_id = submission_data.get("userId")
        contest_name = submission_data.get("name", "Bài kiểm tra")
        profile = self._get_user_profile(user_id)
        student_name = profile.get('name', 'Học sinh') if profile else 'Học sinh'
        prompt = self._build_prompt(student_log, student_name)
        
        print("Đang gửi yêu cầu đến Gemini API...")
        response_text = ""
        try:
            response = self.model.generate_content(prompt)
            if not response.parts:
                print("LỖI: Phản hồi từ Gemini bị chặn hoàn toàn. Lý do (nếu có):", response.prompt_feedback)
                raise HTTPException(status_code=500, detail="Phản hồi từ LLM bị chặn bởi bộ lọc an toàn.")
            
            response_text = response.parts[0].text
            cleaned_json_string = response_text.strip().lstrip("```json").rstrip("```").strip()
            
            if not cleaned_json_string:
                raise HTTPException(status_code=500, detail="LLM trả về phản hồi rỗng.")

            analysis_result = json.loads(cleaned_json_string)
            print("✅ Phân tích LLM thành công!")
        
        except json.JSONDecodeError as e:
            print(f"LỖI: Không thể parse JSON. Lỗi: {e}\n--- Phản hồi gốc ---\n{response_text}\n--------------------")
            raise HTTPException(status_code=500, detail="LLM trả về định dạng JSON không hợp lệ.")
        except Exception as e:
            print(f"Lỗi không xác định trong quá trình phân tích LLM: {e}")
            raise HTTPException(status_code=500, detail=f"Lỗi khi phân tích bằng LLM: {str(e)}")

        if analysis_result:
            print(f"Đang cập nhật báo cáo vào contest_results ID: {contest_result_id}...")
            try:
                self.supabase.table('contest_results').update({'analysis_report': analysis_result}).eq('id', contest_result_id).execute()
                print("Cập nhật 'contest_results' thành công.")
            except Exception as e:
                print(f"CẢNH BÁO: Lỗi khi cập nhật 'contest_results': {e}")

            if user_id:
                structured_report = analysis_result.get("structured_data_report")
                if structured_report:
                    summary = structured_report.get("overallSummary", "Không có tóm tắt chi tiết.")
                    self.memory_service.add_memory(
                        user_id=str(user_id),
                        content=summary,
                        metadata=structured_report,
                        importance=0.9
                    )
            else:
                print("Cảnh báo: Không có userId, bỏ qua việc lưu vào memories.")
            
            final_output = {
                "student_name": student_name,
                "contest_name": contest_name,
                "analysis_result": analysis_result
            }
            return final_output
        
        return None

# ==============================================================================
# === KHỞI TẠO VÀ CHẠY API =====================================================
# ==============================================================================
try:
    analytics_engine = LLMAnalyticsEngine()
except Exception as e:
    print(f"LỖI NGHIÊM TRỌNG: Không thể khởi tạo LLMAnalyticsEngine. API sẽ không hoạt động. Lỗi: {e}")
    analytics_engine = None

app = FastAPI(
    title="CogniLearn - Cognitive Analytics Service",
    description="API chuyên dụng để tự động phân tích, lưu trữ và báo cáo kết quả bài làm.",
    version="3.0.0",
)

class AnalysisRequest(BaseModel):
    contest_result_id: UUID = Field(..., description="ID (UUID) của kết quả bài thi cần phân tích.")

@app.post("/analyze", tags=["Analysis"])
async def run_analysis(request: AnalysisRequest):
    if not analytics_engine:
        raise HTTPException(status_code=503, detail="Service Unavailable: Analytics Engine chưa sẵn sàng.")
    
    try:
        final_report = analytics_engine.analyze_submission(str(request.contest_result_id))
        if final_report:
            return final_report
        else:
            raise HTTPException(status_code=500, detail="Phân tích thất bại. Không có báo cáo nào được tạo.")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Lỗi không xác định trong endpoint /analyze: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ nội bộ không xác định: {str(e)}")

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "Cognitive Analytics Service is running"}

if __name__ == "__main__":
    print("Khởi động server API tại http://127.0.0.1:8003")
    uvicorn.run("llm_based_analyzer:app", host="127.0.0.1", port=8003, reload=True)
# --- END OF FILE llm_based_analyzer.py ---