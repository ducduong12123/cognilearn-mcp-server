# custom_components/memory_tool.py

from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# --- Xử lý import cho MemoryService ---
# Giả định thư mục custom_components nằm trong thư mục gốc của dự án, cùng cấp với src
# current_file_path -> .../CogniLearn_Project/custom_components/memory_tool.py
# .parents[1] -> .../CogniLearn_Project
# Sau đó ghép với 'src'
SRC_ROOT = Path(__file__).resolve().parents[1] / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

# Giờ có thể import an toàn
from core.memory_service import MemoryService
from langflow.interface.custom.component import Component
from langflow.schema.data import Data
from langflow.template.field.base import Input

class UnifiedMemoryTool(Component):
    """
    Một component tùy chỉnh cho LangFlow để tương tác với bộ nhớ dài hạn của CogniLearn.
    """
    display_name: str = "CogniLearn Unified Memory"
    description: str = "Đọc và ghi vào bộ nhớ dài hạn thống nhất của học sinh qua MemoryService."
    icon: str = "brain-circuit" # Icon từ thư viện lucide-react

    # LangFlow sẽ tự động tạo các trường input dựa trên chữ ký của hàm build()
    # Chúng ta có thể tùy chỉnh thêm bằng cách định nghĩa một list `inputs`
    inputs: list[Input] = [
        Input(name="user_id", display_name="User ID", info="ID duy nhất của học sinh.", required=True),
        Input(name="action", display_name="Action", field_type="dropdown", options=["Retrieve", "Add"], value="Retrieve"),
        Input(name="query_text", display_name="Query Text", info="Câu hỏi để truy xuất ký ức (cho action 'Retrieve')."),
        Input(name="content", display_name="Content", info="Nội dung ký ức cần thêm (cho action 'Add').", multiline=True),
        Input(name="metadata", display_name="Metadata", field_type="dict", info="Dữ liệu JSON đi kèm (cho action 'Add').", advanced=True),
        Input(name="importance", display_name="Importance", field_type="float", value=0.5, info="Độ quan trọng của ký ức (0.0-1.0, cho action 'Add').", advanced=True),
    ]
    
    def build(
        self,
        user_id: str,
        action: str,
        query_text: Optional[str] = "",
        content: Optional[str] = "",
        metadata: Optional[Dict] = None,
        importance: Optional[float] = 0.5
    ) -> Data:
        """
        Thực thi logic chính của component.
        """
        try:
            # Khởi tạo MemoryService
            # Lưu ý: Trong môi trường production, nên dùng singleton để tránh khởi tạo lại liên tục.
            memory_service = MemoryService()
            
            if not user_id:
                raise ValueError("User ID là bắt buộc.")

            if action == "Retrieve":
                if not query_text:
                    raise ValueError("Query Text là bắt buộc cho hành động 'Retrieve'.")
                
                retrieved_memories = memory_service.retrieve_similar_memories(user_id=user_id, query_text=query_text)
                
                # Định dạng kết quả thành một chuỗi văn bản duy nhất
                if not retrieved_memories:
                    context_text = "Không tìm thấy ký ức nào liên quan."
                else:
                    context_text = "Ngữ cảnh từ các ký ức liên quan:\n"
                    context_text += "\n".join([f"- {mem['content']}" for mem in retrieved_memories])
                
                self.status = f"Truy xuất {len(retrieved_memories)} ký ức."
                return Data(data=retrieved_memories, text=context_text)

            elif action == "Add":
                if not content:
                    raise ValueError("Content là bắt buộc cho hành động 'Add'.")

                memory_service.add_memory(
                    user_id=user_id, 
                    content=content, 
                    metadata=metadata or {}, 
                    importance=importance
                )
                success_message = f"Đã thêm thành công ký ức: '{content[:50]}...'"
                self.status = success_message
                return Data(data={"status": "success", "message": success_message}, text=success_message)
            
            else:
                raise ValueError(f"Hành động '{action}' không được hỗ trợ.")

        except Exception as e:
            error_message = f"Đã xảy ra lỗi: {e}"
            self.status = error_message
            # Trả về lỗi dưới dạng text để các component khác có thể xử lý
            return Data(data=None, text=error_message)