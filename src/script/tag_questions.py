# File: src/script/tag_questions.py (PHIÊN BẢN CUỐI CÙNG, ĐÃ SỬA LỖI IMPORT)

# --- PHẦN 1: THIẾT LẬP MÔI TRƯỜNG ---
import os
import sys
import time
import yaml
from dotenv import load_dotenv

# THÊM THƯ MỤC GỐC VÀO PATH ĐỂ IMPORT DỄ DÀNG HƠN
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT) # Đảm bảo Python tìm thấy package 'src'

DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=DOTENV_PATH)

# --- PHẦN 2: IMPORT CÁC THƯ VIỆN CẦN THIẾT ---
import dataclasses
import json
from typing import List, Dict, Any

from tqdm import tqdm

# Cách import đúng khi đã thêm project root vào path
from src.langextract.prompting import PromptTemplateStructured, QAPromptGenerator
from src.langextract.factory import create_model, ModelConfig
from src.langextract import data as lx_data

# --- PHẦN 3: LOGIC CHÍNH (GIỮ NGUYÊN) ---

@dataclasses.dataclass
class QuestionMetadata:
    subject: str = "Không xác định"
    domain: str = "Không xác định"
    topic: str = "Không xác định"
    sub_topic: str = ""
    question_type: str = "Không xác định"
    difficulty: int = 0
    required_concepts: List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuestionMetadata":
        if not isinstance(data, dict):
            return cls()
        return cls(
            subject=data.get("subject", cls.subject),
            domain=data.get("domain", cls.domain),
            topic=data.get("topic", cls.topic),
            sub_topic=data.get("sub_topic", cls.sub_topic),
            question_type=data.get("question_type", cls.question_type),
            difficulty=int(data.get("difficulty", cls.difficulty)),
            required_concepts=data.get("required_concepts", cls.required_concepts)
        )

def build_prompt_and_examples() -> (str, List[lx_data.ExampleData]):
    prompt_description = """
Bạn là một chuyên gia phân tích chương trình giáo dục. Nhiệm vụ của bạn là phân tích văn bản câu hỏi và trích xuất các metadata liên quan.
Hãy trả về KẾT QUẢ DUY NHẤT là một khối YAML, KHÔNG có bất kỳ giải thích hay văn bản nào khác.

Các trường cần trích xuất bao gồm:
- subject: Môn học
- domain: Lĩnh vực kiến thức
- topic: Chủ đề cụ thể
- sub_topic: Chủ đề phụ (nếu có, nếu không thì bỏ qua)
- question_type: Phân loại dạng bài
- difficulty: Độ khó từ 1 đến 5
- required_concepts: Danh sách các khái niệm/công thức cốt lõi.
"""
    examples = [
        lx_data.ExampleData(
            text="Một mảnh vườn hình chữ nhật có chu vi là 140 mét và diện tích là 1200 mét vuông. Tính chiều dài và chiều rộng của mảnh vườn.",
            extractions=[
                lx_data.Extraction(
                    extraction_class="metadata",
                    extraction_text="""subject: Toán học
domain: Đại số
topic: Hệ Phương trình
sub_topic: Ứng dụng định lý Vi-et
question_type: Bài toán có lời văn
difficulty: 3
required_concepts:
  - Công thức chu vi hình chữ nhật
  - Công thức diện tích hình chữ nhật
  - Định lý Vi-et đảo
"""
                )
            ]
        ),
    ]
    return prompt_description, examples

def extract_metadata_from_question(prompt_generator: QAPromptGenerator, model, question_text: str) -> QuestionMetadata:
    if not question_text:
        return QuestionMetadata()
    try:
        final_prompt = prompt_generator.render(question=question_text)
        response_iterator = model.infer(batch_prompts=[final_prompt])
        scored_outputs = next(response_iterator)

        if not scored_outputs:
            raise ValueError("Mô hình không trả về kết quả.")

        raw_output_text = scored_outputs.output
        
        if "```yaml" in raw_output_text:
            start_index = raw_output_text.find("```yaml") + 7
            end_index = raw_output_text.rfind("```")
            yaml_string = raw_output_text[start_index:end_index].strip()
        else:
            yaml_string = raw_output_text.strip()

        metadata_dict = yaml.safe_load(yaml_string)
        return QuestionMetadata.from_dict(metadata_dict)
    except Exception as e:
        print(f"\nLỗi chi tiết khi xử lý câu hỏi '{question_text[:50]}...': {e}")
        return QuestionMetadata()

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Lỗi: Không tìm thấy GEMINI_API_KEY.")
        return

    INPUT_FILE = os.path.join(PROJECT_ROOT, "data", "raw", "questions.json")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "questions_with_metadata.json")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    prompt_desc, examples = build_prompt_and_examples()
    prompt_template = PromptTemplateStructured(description=prompt_desc, examples=examples)
    prompt_generator = QAPromptGenerator(
        template=prompt_template, 
        format_type=lx_data.FormatType.YAML, 
        fence_output=False
    )
    model = create_model(ModelConfig(
        model_id="gemini-1.5-pro",
        provider_kwargs={"api_key": api_key, "temperature": 0.1}
    ))

    processed_questions = []
    print(f"Bắt đầu xử lý {len(questions)} câu hỏi...")

    for question in tqdm(questions, desc="Đang trích xuất metadata"):
        content = question.get("content", "")
        metadata = extract_metadata_from_question(prompt_generator, model, content)
        output_question = question.copy()
        output_question['metadata'] = dataclasses.asdict(metadata)
        processed_questions.append(output_question)
        time.sleep(15)

    print(f"\nĐang lưu kết quả vào '{OUTPUT_FILE}'...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(processed_questions, f, indent=4, ensure_ascii=False)
    print("Hoàn thành! Quá trình trích xuất metadata đã xong.")

if __name__ == "__main__":
    main()