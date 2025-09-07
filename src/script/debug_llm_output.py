# File: src/script/debug_llm_output.py (ĐÃ SỬA LỖI)

# --- PHẦN 1: THIẾT LẬP MÔI TRƯỜNG ---
import os
from dotenv import load_dotenv
import json

# Tải biến môi trường
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=DOTENV_PATH)

# --- PHẦN 2: IMPORT CÁC THƯ VIỆN CẦN THIẾT ---
# Import các thành phần của langextract chỉ để xây dựng prompt
import langextract as lx
from langextract.prompting import PromptTemplateStructured, QAPromptGenerator

# Import thư viện gốc của Google
import google.generativeai as genai

# Sao chép y hệt hàm build_prompt_and_examples từ script chính
def build_prompt_and_examples() -> (str, list[lx.data.ExampleData]):
    prompt_description = """
Bạn là một chuyên gia phân tích chương trình giáo dục. Nhiệm vụ của bạn là phân tích văn bản câu hỏi và trích xuất các metadata liên quan.
Hãy trả về kết quả dưới dạng cấu trúc YAML được bọc trong ```yaml ... ```.

Các trường cần trích xuất bao gồm:
- subject: Môn học (ví dụ: Toán học, Vật lý, Lập trình).
- domain: Lĩnh vực kiến thức (ví dụ: Đại số, Cơ học, Thuật toán).
- topic: Chủ đề cụ thể (ví dụ: Phương trình Bậc hai, Rơi tự do, Sắp xếp chuỗi).
- sub_topic: Chủ đề phụ, chi tiết hơn (nếu có).
- question_type: Phân loại dạng bài (ví dụ: Bài toán có lời văn, Chứng minh, Viết hàm).
- difficulty: Độ khó từ 1 (rất dễ) đến 5 (rất khó).
- required_concepts: Danh sách các khái niệm hoặc công thức cốt lõi cần để giải bài.
"""
    examples = [
        lx.data.ExampleData(
            text="Một mảnh vườn hình chữ nhật có chu vi là 140 mét và diện tích là 1200 mét vuông. Tính chiều dài và chiều rộng của mảnh vườn.",
            extractions=[
                lx.data.Extraction(extraction_class="subject", extraction_text="Toán học"),
                lx.data.Extraction(extraction_class="domain", extraction_text="Đại số"),
                lx.data.Extraction(extraction_class="topic", extraction_text="Hệ Phương trình"),
                lx.data.Extraction(extraction_class="sub_topic", extraction_text="Ứng dụng định lý Vi-et"),
                lx.data.Extraction(extraction_class="question_type", extraction_text="Bài toán có lời văn"),
                lx.data.Extraction(extraction_class="difficulty", extraction_text="3"),
                lx.data.Extraction(
                    extraction_class="required_concepts", 
                    extraction_text="",
                    attributes={"concepts": ["Công thức chu vi hình chữ nhật", "Công thức diện tích hình chữ nhật", "Định lý Vi-et đảo"]}
                )
            ]
        ),
        lx.data.ExampleData(
            text="Một con lắc đơn có chiều dài 98 cm dao động tại nơi có gia tốc trọng trường g = 9.8 m/s². Tính chu kỳ dao động của con lắc.",
            extractions=[
                lx.data.Extraction(extraction_class="subject", extraction_text="Vật lý"),
                lx.data.Extraction(extraction_class="domain", extraction_text="Dao động cơ"),
                lx.data.Extraction(extraction_class="topic", extraction_text="Con lắc đơn"),
                lx.data.Extraction(extraction_class="question_type", extraction_text="Tính toán đại lượng vật lý"),
                lx.data.Extraction(extraction_class="difficulty", extraction_text="2"),
                lx.data.Extraction(
                    extraction_class="required_concepts",
                    extraction_text="",
                    attributes={"concepts": ["Công thức tính chu kỳ con lắc đơn", "Đổi đơn vị (cm sang m)"]}
                )
            ]
        )
    ]
    return prompt_description, examples

def debug_single_question():
    """
    Hàm để debug một câu hỏi duy nhất và in ra kết quả thô từ LLM.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("LỖI: Không tìm thấy GEMINI_API_KEY. Dừng lại.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')

    question_text = "Một mảnh vườn hình chữ nhật có chu vi là 140 mét và diện tích là 1200 mét vuông. Tính chiều dài và chiều rộng của mảnh vườn."
    
    prompt_desc, examples = build_prompt_and_examples()
    prompt_template = PromptTemplateStructured(description=prompt_desc, examples=examples)
    
    # === SỬA LỖI Ở ĐÂY ===
    # Thay thế 'resolver_params' bằng tham số đúng là 'attribute_suffix'
    prompt_generator = QAPromptGenerator(
        template=prompt_template,
        format_type=lx.data.FormatType.YAML,
        fence_output=True,
        attribute_suffix="" # <--- THAY ĐỔI QUAN TRỌNG
    )
    # =====================

    final_prompt_string = prompt_generator.render(question=question_text)

    print("--- PROMPT SẼ ĐƯỢC GỬI ĐẾN GEMINI ---")
    print(final_prompt_string)
    print("------------------------------------")
    
    print("\n... Đang gửi yêu cầu đến Gemini, vui lòng chờ ...\n")

    try:
        response = model.generate_content(final_prompt_string)
        
        print("--- KẾT QUẢ THÔ TỪ GEMINI ---")
        print(response.text)
        print("-------------------------------")
    except Exception as e:
        print(f"Đã xảy ra lỗi khi gọi API Gemini: {e}")

if __name__ == "__main__":
    debug_single_question()