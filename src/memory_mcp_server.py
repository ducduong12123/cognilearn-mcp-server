
import os, json, time, math
import uuid               # để sinh id: uuid.uuid4()
from uuid import UUID  # để validate user_id
from typing import Any, Dict, List, Optional
import datetime as dt

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse          # THÊM DÒNG NÀY
from mcp.server.fastmcp import FastMCP

def _is_uuid(s: str) -> bool:
    try:
        UUID(str(s))
        return True
    except Exception:
        return False


# -----------------------------
# Config qua biến môi trường
# -----------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
MEMORY_TABLE = os.getenv("MEMORY_TABLE", "memories")
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "")   # optional fallback
APP_NAME = os.getenv("APP_NAME", "cognilearn-mcp")
PORT = int(os.getenv("PORT", "10000"))

# -----------------------------
# Optional: Supabase client
# -----------------------------
try:
    from supabase import create_client
except Exception:
    create_client = None

# -----------------------------
# FastAPI app + logging middleware
# -----------------------------
app = FastAPI(title=APP_NAME)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    resp: Response = await call_next(request)
    dur_ms = (time.time() - start) * 1000
    path = request.url.path
    try:
        print(f"[HTTP] {request.method} {path} -> {resp.status_code} in {dur_ms:.1f}ms")
    except Exception:
        pass
    return resp

# -----------------------------
# User ID extraction middleware
# -----------------------------
def _decode_jwt_sub(token: str) -> Optional[str]:
    # Nếu bạn dùng JWT thực sự, decode ở đây (HS256/RSA). Mặc định bỏ qua.
    return None

def _extract_user_id_from_headers(req: Request) -> Optional[str]:
    h = req.headers
    for k in ("x-user-id", "user-id", "userid", "userId", "userID"):
        v = h.get(k) or h.get(k.lower())
        if v: return v
    auth = h.get("authorization", "")
    if auth.startswith("Bearer "):
        sub = _decode_jwt_sub(auth.removeprefix("Bearer ").strip())
        if sub: return sub
    return None

async def _read_body_json(request: Request) -> Dict[str, Any]:
    body = await request.body()
    try:
        data = json.loads(body or b"{}")
    except Exception:
        data = {}
    # Re-inject body so downstream can read again
    async def receive():
        return {"type": "http.request", "body": body or b"", "more_body": False}
    request._receive = receive  # type: ignore
    return data

@app.middleware("http")
async def user_context(request: Request, call_next):
    uid = _extract_user_id_from_headers(request)

    if not uid and request.method == "POST" and request.url.path.startswith("/mcp"):
        data = await _read_body_json(request)
        # các vị trí phổ biến
        uid = (
            data.get("user_id")
            or data.get("userId")
            or (data.get("variables", {}) or {}).get("userId")
            or (data.get("userInfo", {}) or {}).get("id")
            or data.get("id")
        )

    # fallback cuối
    request.state.user_id = uid or DEFAULT_USER_ID or ""
    return await call_next(request)

# -----------------------------
# Kho lưu trữ (Supabase / In-memory)
# -----------------------------
def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat()

class Repo:
    def __init__(self):
        self.sb = None
        if create_client and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
            try:
                self.sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                print("[Repo] Using Supabase")
            except Exception as e:
                print(f"[Repo] Supabase init failed: {e}. Fallback to memory.")
                self.sb = None
        if not self.sb:
            self._mem: List[Dict[str, Any]] = []
            print("[Repo] Using in-memory store")

    def add(self, row: Dict[str, Any]) -> Dict[str, Any]:
        if self.sb:
            r = self.sb.table(MEMORY_TABLE).insert(row).execute()
            return (r.data or [row])[0]
        self._mem.append(row)
        return row

    def list_user(self, userid: str, limit: int = 100) -> List[Dict[str, Any]]:
        if self.sb:
            r = (self.sb.table(MEMORY_TABLE)
                 .select("*")
                 .eq("userid", userid)
                 .order("created_at", desc=True)
                 .limit(limit)
                 .execute())
            return r.data or []
        return sorted([x for x in self._mem if x.get("userid") == userid],
                      key=lambda x: x.get("created_at",""), reverse=True)[:limit]

    def search(self,
               userid: str,
               types: Optional[List[str]] = None,
               topics: Optional[List[str]] = None,
               since: Optional[str] = None,
               until: Optional[str] = None,
               min_importance: float = 0.0,
               limit: int = 100) -> List[Dict[str, Any]]:
        if self.sb:
            q = (self.sb.table(MEMORY_TABLE).select("*").eq("userid", userid))
            if since: q = q.gte("created_at", since)
            if until: q = q.lte("created_at", until)
            if min_importance: q = q.gte("importance", float(min_importance))
            # filter theo types/topics trong metadata
            # Supabase PostgREST không hỗ trợ IN dễ cho jsonb->>,
            # dùng OR chain đơn giản:
            if types:
                ors = ",".join([f"metadata->>type.eq.{t}" for t in types])
                q = q.or_(ors) if ors else q
            if topics:
                ors = ",".join([f"metadata->>topic.eq.{tp}" for tp in topics])
                q = q.or_(ors) if ors else q
            r = q.order("created_at", desc=True).limit(limit).execute()
            return r.data or []
        # in-memory
        rows = [x for x in self._mem if x.get("userid")==userid]
        if since:
            rows = [x for x in rows if x.get("created_at","") >= since]
        if until:
            rows = [x for x in rows if x.get("created_at","") <= until]
        if min_importance:
            rows = [x for x in rows if float(x.get("importance", 0.0)) >= float(min_importance)]
        if types:
            rows = [x for x in rows if (x.get("metadata",{}).get("type") in types)]
        if topics:
            rows = [x for x in rows if (x.get("metadata",{}).get("topic") in topics)]
        return sorted(rows, key=lambda x: x.get("created_at",""), reverse=True)[:limit]

repo = Repo()

# -----------------------------
# Xếp hạng & nén (heuristic rẻ)
# -----------------------------
def _sim(q: str, txt: str) -> float:
    if not q or not txt: return 0.0
    q = q.lower(); txt = txt.lower()
    tokens = set(q.split())
    hit = sum(1 for t in tokens if t in txt)
    return min(1.0, hit / max(4, len(tokens)))

def _recency_weight(iso: str) -> float:
    try:
        d = dt.datetime.fromisoformat(iso.replace("Z",""))
        days = (dt.datetime.utcnow() - d).days
        return max(0.1, math.exp(-days/120))
    except Exception:
        return 0.5

def _score(item: Dict[str,Any], query: str, topics: List[str]) -> float:
    s = 0.5*_sim(query, item.get("content",""))
    s += 0.2*_recency_weight(item.get("created_at",""))
    s += 0.2*float(item.get("importance", 0.0))
    if topics and item.get("metadata",{}).get("topic") in topics:
        s += 0.1
    return float(f"{s:.4f}")

def _truncate(text: str, n: int) -> str:
    return text if len(text)<=n else (text[:max(0,n-1)]+"…")

# -----------------------------
# MCP server
# -----------------------------
mcp = FastMCP(
    name=APP_NAME,
    stateless_http=True,        # dùng stateless để tránh phải quản lý session
    # json_response=True          # trả JSON thuần (dễ test bằng curl/Postman)
)

# -----------------------------
# Tool cũ (compat)
# -----------------------------
# @mcp.tool()
# def add_memory(
#     user_id: str = "",
#     content: str = "",
#     metadata: Dict[str, Any] = {},
#     importance: float = 0.5
# ) -> Dict[str, Any]:
#     """
#     Thêm 1 memory (tương thích phiên bản cũ).
#     """
#     uid = user_id or getattr(app.state, "user_id", "") or ""
#     if not uid:
#         return {"status": "error", "message": "missing user_id"}
#     if not _is_uuid(uid):
#         return {"status": "error", "message": "invalid user_id (expect UUID)"}

#     row = {
#         "id": str(uuid.uuid4()),                        # sinh UUID v4 ở app
#         "userid": uid,                                  # FK → profiles.id
#         "content": (content or "").strip(),             # dùng biến hàm, không dùng params
#         "metadata": metadata or {},
#         "importance": float(importance or 0.5),
#         "created_at": _now_iso(),                       # dùng đúng _now_iso()
#     }
#     saved = repo.add(row)
#     # trả id (ưu tiên id DB trả về nếu có)
#     return {"status": "success", "id": saved.get("id", row["id"])}
# @mcp.tool()
# def retrieve_similar_memories(
#     user_id: str = "",
#     query_text: str = "",
#     top_k: int = 5
# ) -> Dict[str, Any]:
#     """
#     Lấy top_k memory liên quan (compat cũ) – dùng heuristic nhanh.
#     """
#     uid = user_id or getattr(app.state, "user_id", "") or ""
#     if not uid:
#         return {"memories": [], "context_text": "", "note": "missing user_id"}
#     rows = repo.list_user(uid, limit=max(50, top_k*5))
#     ranked = sorted(rows, key=lambda r: _score(r, query_text, []), reverse=True)[:max(1, top_k)]
#     context = "\n".join([_truncate(r.get("content",""), 160) for r in ranked])
#     return {
#         "memories": [{
#             "id": r.get("id"),
#             "content": r.get("content",""),
#             "metadata": r.get("metadata", {}),
#             "similarity": _score(r, query_text, [])
#         } for r in ranked],
#         "context_text": context
#     }

# -----------------------------
# Tool mới: lấy sạch–gọn cho Agent
# -----------------------------
@mcp.tool()
def search_memories(
    user_id: str = "",
    query_text: str = "",
    filter: Dict[str, Any] = {},
    limit: int = 10,
    fields: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """
    Công cụ tìm kiếm chính để truy xuất thông tin từ bộ nhớ dài hạn của học sinh.
    Hãy sử dụng công cụ này khi người dùng hỏi về lịch sử, tiến độ, điểm mạnh, điểm yếu hoặc bất kỳ thông tin nào đã được lưu trữ trước đó.

    Args:
        user_id (str): Mã định danh duy nhất của học sinh. BẮT BUỘC.
        query_text (str): Một câu hỏi hoặc mô tả rõ ràng về thông tin cần tìm. Ví dụ: "khó khăn của học sinh với môn hình học".
        filter (dict, optional): Một đối tượng JSON để lọc kết quả. Các key hợp lệ là: "types" (danh sách các loại ký ức), "topics" (danh sách các chủ đề), "since" (ngày bắt đầu, định dạng ISO), "until" (ngày kết thúc, định dạng ISO), "min_importance" (số từ 0.0 đến 1.0).
        limit (int, optional): Số lượng kết quả tối đa cần trả về. Mặc định là 10.
        fields (dict, optional): Một đối tượng JSON để chỉ định các trường thông tin cần trả về. Các key hợp lệ là: "include" (danh sách các trường, ví dụ ["id", "content"]), "truncate_chars" (số ký tự tối đa cho mỗi nội dung).
    """
    uid = user_id or getattr(app.state, "user_id", "") or ""
    if not uid:
        return {"items": [], "used_filters": filter, "note": "missing user_id"}
    f = {"types": [], "topics": [], "since":"", "until":"", "min_importance":0.0} | (filter or {})
    proj = {"include":["id","content","metadata"], "truncate_chars": 220} | (fields or {})
    rows = repo.search(
        userid=uid,
        types=f.get("types") or None,
        topics=f.get("topics") or None,
        since=f.get("since") or None,
        until=f.get("until") or None,
        min_importance=float(f.get("min_importance", 0.0)),
        limit=int(max(limit, 1))*3
    )
    ranked = sorted(rows, key=lambda r: _score(r, query_text, f.get("topics") or []), reverse=True)[:int(limit)]
    items = []
    for r in ranked:
        item: Dict[str, Any] = {}
        if "id" in proj["include"]: item["id"] = r.get("id")
        if "content" in proj["include"]: item["content"] = _truncate(r.get("content",""), int(proj["truncate_chars"]))
        if "metadata" in proj["include"]: item["metadata"] = r.get("metadata", {})
        item["score"] = _score(r, query_text, f.get("topics") or [])
        items.append(item)
    return {"items": items, "used_filters": f}

@mcp.tool()
def build_context_pack(
    user_id: str = "",
    question: str = "",
    need: Dict[str, Any] = {},
    budget: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """
    Tạo một "gói ngữ cảnh" (context pack) được tóm tắt và cấu trúc hóa về hiệu năng của học sinh.
    Công cụ này rất mạnh mẽ. Hãy sử dụng khi cần một cái nhìn tổng quan, đa chiều về học sinh để trả lời các câu hỏi phức tạp.

    Args:
        user_id (str): Mã định danh duy nhất của học sinh. BẮT BUỘC.
        question (str): Câu hỏi hoặc chủ đề chính cần phân tích. Ví dụ: "đánh giá tổng quan năng lực học toán".
        need (dict, optional): Chỉ định các phần thông tin cần có trong báo cáo. Các key hợp lệ là: "sections" (danh sách các mục, ví dụ ["weaknesses", "topic_stats"]), "topics" (lọc theo chủ đề), "horizon_days" (xem xét dữ liệu trong bao nhiêu ngày qua).
        budget (dict, optional): Giới hạn về độ dài của kết quả. Các key hợp lệ là: "max_items", "max_chars_per_item".
    """
    uid = user_id or getattr(app.state, "user_id", "") or ""
    if not uid:
        return {"sections": {}, "citations": [], "note": "missing user_id"}

    need = {"sections":["weaknesses","topic_stats","recent_errors","profile"], "topics":[], "horizon_days":120} | (need or {})
    budget = {"max_items":12, "max_chars_per_item":160, "max_sections":4} | (budget or {})
    since = (dt.datetime.utcnow() - dt.timedelta(days=int(need["horizon_days"]))).isoformat()

    sections: Dict[str, Any] = {}
    citations: List[Dict[str,str]] = []

    # weaknesses & recent_errors (type=deep_dive/error)
    if "weaknesses" in need["sections"] or "recent_errors" in need["sections"]:
        items = repo.search(uid, types=["deep_dive","error"], since=since, limit=64)
        ranked = sorted(items, key=lambda r: _score(r, question, need.get("topics") or []), reverse=True)
        take = ranked[: max(1, budget["max_items"]//2)]
        if "weaknesses" in need["sections"]:
            sections["weaknesses"] = [_truncate(r.get("content",""), budget["max_chars_per_item"]) for r in take]
            citations += [{"section":"weaknesses","memory_id": r.get("id","") } for r in take]
        if "recent_errors" in need["sections"]:
            recent = [{
                "question_id": r.get("metadata",{}).get("question_id",""),
                "note": _truncate(r.get("content",""), budget["max_chars_per_item"])
            } for r in take]
            sections["recent_errors"] = recent

    # topic_stats
    if "topic_stats" in need["sections"]:
        stats = repo.search(uid, types=["topic_stat"], since=since, limit=100)
        simplified = []
        for s in stats:
            md = s.get("metadata",{})
            simplified.append({
                "topic": md.get("topic",""),
                "accuracy": float(md.get("accuracy", md.get("accuracyRate", 0.0))),
                "total": int(md.get("total", md.get("totalAnswers", 0)))
            })
        simplified = sorted(simplified, key=lambda x: (x["accuracy"], -x["total"]))[: min(10, budget["max_items"])]
        sections["topic_stats"] = simplified

    # profile (skill/goal/preference/constraint/certificate/project)
    if "profile" in need["sections"]:
        prof = repo.search(uid, types=["skill","goal","preference","constraint","certificate","project"], limit=60)
        grp = {"skill":[],"goal":[],"preference":[],"constraint":[]}
        for r in prof:
            t = (r.get("metadata",{}).get("type") or "").lower()
            if t in grp and len(grp[t]) < 3:
                grp[t].append(_truncate(r.get("content",""), budget["max_chars_per_item"]))
        sections["profile"] = grp

    return {"sections": sections, "citations": citations, "note": f"question='{_truncate(question,64)}'"}

@mcp.tool()
def summarize_performance(
    user_id: str = "",
    topics: List[str] = [],
    timeframe_days: int = 180
) -> Dict[str, Any]:
    """
    Tổng hợp và thống kê hiệu năng học tập của học sinh theo từng chủ đề.
    Sử dụng công cụ này khi người dùng muốn biết họ giỏi hay yếu ở những chủ đề nào, hoặc khi cần dữ liệu thống kê cụ thể.

    Args:
        user_id (str): Mã định danh duy nhất của học sinh. BẮT BUỘC.
        topics (list, optional): Một danh sách các chủ đề cụ thể cần thống kê. Nếu bỏ trống, sẽ thống kê tất cả các chủ đề.
        timeframe_days (int, optional): Khoảng thời gian (số ngày) nhìn về quá khứ để lấy dữ liệu. Mặc định là 180 ngày.
    """
    uid = user_id or getattr(app.state, "user_id", "") or ""
    if not uid:
        return {"by_topic": [], "weakest": []}
    since = (dt.datetime.utcnow() - dt.timedelta(days=int(timeframe_days))).isoformat()
    stats = repo.search(uid, types=["topic_stat"], since=since, limit=300)
    rows: List[Dict[str, Any]] = []
    for s in stats:
        md = s.get("metadata",{})
        topic = md.get("topic","")
        if topics and topic not in topics: 
            continue
        acc = float(md.get("accuracy", md.get("accuracyRate", 0.0)))
        total = int(md.get("total", md.get("totalAnswers", 0)))
        rows.append({"topic": topic, "accuracy": acc, "total": total})
    rows = sorted(rows, key=lambda x: (x["accuracy"], -x["total"]))
    weak = [r for r in rows if r["total"]>=3][:5]
    return {"by_topic": rows[:20], "weakest": weak}

@mcp.tool()
def propose_question_specs(
    user_id: str = "",
    count: int = 8,
    focus_topics: List[str] = [],
    difficulty_profile: Dict[str, float] = {}
) -> Dict[str, Any]:
    """
    Phân tích điểm yếu của học sinh và đề xuất cấu trúc (specifications) cho các câu hỏi luyện tập mới.
    Công cụ này KHÔNG tạo ra câu hỏi, mà chỉ đưa ra kế hoạch/yêu cầu để một agent khác có thể tạo câu hỏi.
    Hãy sử dụng khi người dùng muốn có bài tập luyện tập được cá nhân hóa.

    Args:
        user_id (str): Mã định danh duy nhất của học sinh. BẮT BUỘC.
        count (int, optional): Số lượng câu hỏi cần đề xuất cấu trúc. Mặc định là 8.
        focus_topics (list, optional): Các chủ đề cụ thể cần tập trung vào. Nếu bỏ trống, công cụ sẽ tự động xác định từ các điểm yếu.
        difficulty_profile (dict, optional): Phân bổ độ khó. Ví dụ: {"easy": 0.2, "medium": 0.6, "hard": 0.2}.
    """
    perf = summarize_performance(user_id=user_id, topics=focus_topics or [], timeframe_days=180)
    targets = [t["topic"] for t in (perf.get("weakest") or [])] or (focus_topics or [])
    if not targets:
        targets = [t["topic"] for t in (perf.get("by_topic") or [])[:3]]

    dp = {"easy":0.2, "medium":0.6, "hard":0.2} | (difficulty_profile or {})
    n_easy = max(1, round(count*dp["easy"]))
    n_hard = max(1, round(count*dp["hard"]))
    n_med  = max(0, int(count - n_easy - n_hard))

    def mk_spec(topic: str, dif: str, idx: int) -> Dict[str, Any]:
        return {
            "id": f"spec_{topic}_{dif}_{idx}",
            "topic": topic,
            "sub_skills": [],
            "difficulty": dif,  # easy|medium|hard
            "format": "mcq_or_free",
            "constraints": {
                "steps_required": dif!="easy",
                "avoid_trick": True,
                "numeric_range": "small_integers"
            },
            "rubric": {
                "full_mark": "kết luận đúng + lập luận chặt chẽ",
                "partial": "đúng hướng nhưng thiếu điều kiện"
            }
        }

    specs: List[Dict[str, Any]] = []
    ring = targets or ["Tổng hợp"]
    i = 0
    for _ in range(n_easy):
        specs.append(mk_spec(ring[i % len(ring)], "easy", i)); i+=1
    for _ in range(n_med):
        specs.append(mk_spec(ring[i % len(ring)], "medium", i)); i+=1
    for _ in range(n_hard):
        specs.append(mk_spec(ring[i % len(ring)], "hard", i)); i+=1

    return {"targets": targets, "count": int(count), "specs": specs}

@mcp.tool()
def add_memory_normalized(
    user_id: str = "",
    content: str = "",
    meta: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """
    Lưu một thông tin (fact) ngắn gọn, đã được chuẩn hóa vào bộ nhớ dài hạn của học sinh.
    Đây là công cụ chính để GHI nhớ. Sử dụng sau mỗi tương tác quan trọng hoặc khi người dùng cung cấp thông tin mới.

    Args:
        user_id (str): Mã định danh của học sinh. BẮT BUỘC.
        content (str): Nội dung ký ức, phải là một câu ngắn gọn, khách quan. BẮT BUỘC.
        meta (dict): Metadata có cấu trúc. BẮT BUỘC phải chứa một key "type" hợp lệ. Các loại (type) hợp lệ bao gồm: "skill", "goal", "preference", "performance", "error", "deep_dive", "note".
    """
    uid = user_id or getattr(app.state, "user_id", "") or ""
    if not uid:
        return {"status": "error", "message": "missing user_id"}
    if not _is_uuid(uid):
        return {"status": "error", "message": "invalid user_id (expect UUID)"}

    allowed = {
        "skill","goal","preference","constraint","performance","error",
        "deep_dive","topic_stat","certificate","project","practice_result",
        "recommendation","note"
    }
    t = (meta.get("type") or "note").lower().strip()
    if t not in allowed:
        return {"status": "error", "message": f"metadata.type='{t}' không hợp lệ"}

    content = (content or "").strip()
    if not content:
        return {"status": "error", "message": "content trống"}

    row = {
        "id": str(uuid.uuid4()),
        "userid": uid,
        "content": content,
        "metadata": {
            "type": t,
            "topic": meta.get("topic", ""),
            "question_id": meta.get("question_id", ""),
            "source": meta.get("source", "chat"),
        },
        "importance": float(meta.get("importance") or 0.5),
        "created_at": _now_iso(),
    }
    saved = repo.add(row)
    return {"status": "success", "id": saved.get("id", row["id"])}
@mcp.tool()
def record_practice_result(
    user_id: str = "",
    question_id: str = "",
    topic: str = "",
    correct: bool = True,
    note: str = "",
    score: float = 1.0
) -> Dict[str, Any]:
    """
    Ghi lại kết quả sau khi học sinh làm một bài tập luyện tập.
    Công cụ này rất quan trọng để cập nhật và nuôi dưỡng dữ liệu thống kê về hiệu năng học tập.

    Args:
        user_id (str): Mã định danh của học sinh. BẮT BUỘC.
        question_id (str): Mã của câu hỏi đã làm.
        topic (str): Chủ đề của câu hỏi.
        correct (bool): Học sinh trả lời đúng hay sai.
        note (str, optional): Ghi chú thêm về câu trả lời của học sinh.
        score (float, optional): Điểm số cho câu trả lời (từ 0.0 đến 1.0).
    """
    uid = user_id or getattr(app.state, "user_id", "") or ""
    if not uid:
        return {"status": "error", "message": "missing user_id"}
    if not _is_uuid(uid):
        return {"status": "error", "message": "invalid user_id (expect UUID)"}

    row = {
        "id": str(uuid.uuid4()),
        "userid": uid,
        "content": f"Kết quả luyện tập: {'đúng' if correct else 'sai'} – {topic} – {note}".strip(),
        "metadata": {
            "type": "practice_result",
            "topic": topic,
            "question_id": question_id,
            "score": float(score) if score is not None else None,
            "correct": bool(correct),
        },
        "importance": 0.6,
        "created_at": _now_iso(),
    }
    saved = repo.add(row)
    return {"status": "success", "id": saved.get("id", row["id"])}


# -----------------------------
# Healthcheck
# -----------------------------
# 1) Tạo ASGI sub-app cho MCP (HTTP Streamable)
mcp_subapp = mcp.streamable_http_app()

# 1a) CORS cho MCP sub-app
mcp_subapp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 1b) Log riêng cho MCP (decorator middleware của Starlette dùng được)
@mcp_subapp.middleware("http")
async def log_mcp_requests(request: Request, call_next):
    start = time.time()
    resp = await call_next(request)
    dur = (time.time() - start) * 1000
    print(f"[MCP] {request.method} {request.url.path} -> {resp.status_code} in {dur:.1f}ms")
    return resp

# 1c) PING cho MCP sub-app (DÙNG add_route, KHÔNG DÙNG @mcp_subapp.get)
async def mcp_ping(request: Request):
    return JSONResponse({"ok": True, "scope": "mcp"})

mcp_subapp.add_route("/_ping", mcp_ping, methods=["GET"])

# 2) App chính: dùng lifespan của MCP sub-app để MCP init/cleanup đúng cách
app = FastAPI(title=APP_NAME, lifespan=mcp_subapp.router.lifespan_context)

# 2a) CORS cho app chính
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                 # hoặc whitelist domain n8n của bạn
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],                 # để client gửi Mcp-* headers
    expose_headers=["*"],                # để n8n đọc Mcp-Session-Id, v.v.
)

# 3) Mount MCP sub-app tại /mcp (n8n Endpoint = https://.../mcp)
app.mount("/mcp", mcp_subapp, name="mcp")

# 4) Healthcheck & root
@app.get("/")
async def root_ok():
    return {"ok": True, "service": APP_NAME, "ts": int(time.time())}

@app.get("/healthz")
async def healthz():
    return {"ok": True}

# 5) (Tùy chọn) log request của app chính
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    resp = await call_next(request)
    dur = (time.time() - start) * 1000
    print(f"[HTTP] {request.method} {request.url.path} -> {resp.status_code} in {dur:.1f}ms")
    return resp

# -----------------------------
# Gunicorn cmd (ví dụ Dockerfile)
# -----------------------------
# CMD ["bash", "-lc", "gunicorn -k uvicorn.workers.UvicornWorker memory_mcp_server:app --bind 0.0.0.0:${PORT:-10000} --timeout ${TIMEOUT:-0} --workers ${WORKERS:-2}"]
