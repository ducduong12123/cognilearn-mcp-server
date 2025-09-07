# api.py

# ==============================================================================
# <<< PHẦN THÊM MỚI - GIẢI QUYẾT VẤN ĐỀ MODULE NOT FOUND >>>
# Đoạn code này phải được đặt ở trên cùng, trước tất cả các lệnh import khác.
import sys
from pathlib import Path

# Xác định đường dẫn tuyệt đối đến thư mục gốc của dự án (CogniLearn_Project)
# Path(__file__) -> trỏ tới file api.py hiện tại
# .resolve() -> lấy đường dẫn tuyệt đối
# .parent.parent.parent.parent -> đi ngược lên 4 cấp để đến thư mục gốc
project_root = Path(__file__).resolve().parent.parent.parent.parent

# Thêm đường dẫn thư mục gốc vào danh sách tìm kiếm module của Python
# sys.path là nơi Python tìm kiếm các file để import.
# Bằng cách thêm vào, Python sẽ "nhìn thấy" được thư mục `src`.
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ==============================================================================


import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Bây giờ, lệnh import này sẽ hoạt động vì Python đã biết tìm `src` ở đâu
from src.script.ai_engine.llm_based_analyzer import LLMAnalyticsEngine


# --- KHỞI TẠO ỨNG DỤNG VÀ ENGINE ---

app = FastAPI(
    title="CogniLearn AI Analytics API",
    description="API để phân tích kết quả bài làm của học sinh.",
    version="1.0.0"
)

try:
    analytics_engine = LLMAnalyticsEngine()
except Exception as e:
    print(f"LỖI NGHIÊM TRỌNG: Không thể khởi tạo LLMAnalyticsEngine. API có thể không hoạt động. Lỗi: {e}")
    analytics_engine = None


# --- ĐỊNH NGHĨA CẤU TRÚC DỮ LIỆU ---

class AnalysisRequest(BaseModel):
    contest_result_id: str


# --- ĐỊNH NGHĨA CÁC ĐIỂM CUỐI (ENDPOINTS) CỦA API ---

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "Analytics API is running"}

@app.post("/analyze", tags=["Analysis"])
async def run_analysis(request: AnalysisRequest):
    if not analytics_engine:
        raise HTTPException(
            status_code=503, 
            detail="Service Unavailable: Analytics Engine is not initialized."
        )

    print(f"Nhận được yêu cầu phân tích cho id: {request.contest_result_id}")
    
    try:
        report = analytics_engine.analyze_submission_with_llm(request.contest_result_id)
        if report:
            return report
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Analysis failed or no data found for ID: {request.contest_result_id}"
            )
    except Exception as e:
        print(f"Lỗi không xác định trong quá trình phân tích: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"An internal server error occurred: {str(e)}"
        )


# --- CHẠY SERVER ĐỂ KIỂM THỬ ---

if __name__ == "__main__":
    # Lưu ý: Khi chạy trực tiếp file này, uvicorn sẽ dùng đường dẫn tương đối
    # nên có thể không cần đoạn code thêm sys.path ở trên.
    # Tuy nhiên, đoạn code đó là cần thiết khi chạy bằng lệnh `uvicorn` từ bên ngoài.
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)