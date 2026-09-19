# CogniLearn Memory MCP Server

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![MCP](https://img.shields.io/badge/MCP-streamable%20HTTP-6f42c1)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)
![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)

> **Status (09/2026):** reference implementation from the 2025 CogniLearn prototype, no longer
> maintained. The design (identity from the caller, typed memory facts, budgeted context packs)
> carried over into later work; the code is kept as-is for reading and for local experiments.

An [MCP](https://modelcontextprotocol.io) server that gives AI tutors **long-term memory about each
learner**. It was the memory layer of [CogniLearn](https://www.cognilearn.tech/), an intelligent
tutoring system; any MCP client — Claude, n8n, LangFlow, a custom agent — can read a learner's
history, strengths and weaknesses, and write new facts back after every interaction.

The repository also contains the **question-bank pipeline** used to bootstrap CogniLearn's
personalised practice: tagging 200 Vietnamese maths questions with an LLM, embedding them and
loading them into Supabase / pgvector.

---

## Table of contents

- [What the server does](#what-the-server-does)
- [Tools exposed over MCP](#tools-exposed-over-mcp)
- [Memory model](#memory-model)
- [How a request is handled](#how-a-request-is-handled)
- [Quick start](#quick-start)
- [Connecting a client](#connecting-a-client)
- [Deployment](#deployment)
- [Question-bank pipeline](#question-bank-pipeline)
- [Project layout](#project-layout)
- [Status and limitations](#status-and-limitations)

---

## What the server does

A tutoring agent is only as good as what it remembers about the student. This server stores
short, normalised facts per learner (`"struggles with geometric proofs"`, `"goal: 8.0 in the
national exam"`, `"answered Q-042 correctly"`) and turns them back into something an LLM can use:
ranked search results, per-topic performance statistics and a compact **context pack** that fits
in a prompt budget.

Design choices:

- **MCP first.** The six tools below are the only interface; there is no bespoke REST API for
  memory. This is what lets the same memory sit behind Claude Desktop, an n8n workflow and the
  CogniLearn web app at once.
- **Stateless streamable HTTP.** `FastMCP(stateless_http=True)` mounted on a FastAPI app, so it
  runs behind ordinary load balancers and scales horizontally. The MCP endpoint is
  **`/mcp/mcp`** (the sub-app is mounted at `/mcp` and FastMCP serves its default `/mcp` path
  inside it).
- **Learner identity comes from the caller, never from the model.** Middleware resolves
  `user_id` from the `X-User-Id` header (or the request body for MCP calls) and validates it as a
  UUID; tools refuse to write without one.
- **Pluggable store.** Supabase (Postgres) when `SUPABASE_URL` is set, an in-process list
  otherwise — the same code path, so you can develop and run MCP Inspector with no credentials.

## Tools exposed over MCP

| Tool | Purpose | Reads / writes |
| --- | --- | --- |
| `search_memories` | Ranked search over a learner's memories with filters (`types`, `topics`, `since`, `until`, `min_importance`) and field projection / truncation. | read |
| `build_context_pack` | A structured, budgeted summary of the learner — sections `weaknesses`, `topic_stats`, `recent_errors`, `profile`, each with memory-id citations — for a given question. The tool an agent calls before answering anything non-trivial. | read |
| `summarize_performance` | Per-topic accuracy and attempt counts over a time window, plus the weakest topics (≥ 3 attempts). | read |
| `propose_question_specs` | Turns weaknesses into *specifications* for new practice questions (topic, difficulty mix, skills) — it does not generate questions itself, so a separate generator agent stays in control of content. | read |
| `add_memory_normalized` | Store one short, objective fact with typed metadata. This is the main write path. | write |
| `record_practice_result` | Record the outcome of one practice question (`question_id`, `topic`, `correct`, `score`, note); feeds the statistics above. | write |

All tool descriptions are written in Vietnamese because the tutoring product is Vietnamese;
the parameter names and JSON shapes are language-neutral.

## Memory model

Each memory is one row:

```json
{
  "id": "6f1a…",                      "userid": "<learner uuid>",
  "content": "Nhầm dấu khi chuyển vế trong phương trình bậc nhất",
  "metadata": { "type": "error", "topic": "phuong-trinh", "question_id": "Q-042", "source": "chat" },
  "importance": 0.6,
  "created_at": "2025-09-12T08:41:03"
}
```

`metadata.type` is an enum: `skill`, `goal`, `preference`, `constraint`, `performance`, `error`,
`deep_dive`, `topic_stat`, `certificate`, `project`, `practice_result`, `recommendation`, `note`.
Invalid types and non-UUID learner ids are rejected at the tool boundary.

Ranking in `search_memories` is a cheap, explainable score — no embedding round-trip in the
request path:

```text
score = 0.5 · lexical overlap(query, content)
      + 0.2 · recency          (exp(-age_days / 120), floor 0.1)
      + 0.2 · importance
      + 0.1 · topic match
```

An embedding-based variant (`src/core/memory_service.py`, Gemini `text-embedding-004` +
Supabase `match_memories` RPC) exists for the web app and can replace the heuristic when recall
matters more than latency.

## How a request is handled

```text
MCP client ─POST /mcp/mcp─► FastAPI
                          ├─ log middleware
                          ├─ identity middleware: X-User-Id | body.user_id | DEFAULT_USER_ID
                          └─ FastMCP (streamable HTTP, stateless)
                               └─ tool ──► Repo ──► Supabase table `memories`
                                                 └─► in-memory list (no credentials)
```

Health endpoints: `GET /` and `GET /healthz` on the main app, `GET /mcp/_ping` on the MCP sub-app.

## Quick start

```powershell
git clone https://github.com/ducduong12123/cognilearn-mcp-server.git
cd cognilearn-mcp-server
uv sync                                   # or: pip install -r requirements.txt
Copy-Item .env.example .env               # leave SUPABASE_* empty to use the in-memory store

uv run uvicorn src.memory_mcp_server:app --port 8002 --reload
# → http://127.0.0.1:8002/healthz   and   MCP endpoint http://127.0.0.1:8002/mcp/mcp
```

Try it with the official inspector:

```powershell
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP · URL: http://127.0.0.1:8002/mcp/mcp
# Add header  X-User-Id: 11111111-1111-4111-8111-111111111111   then call add_memory_normalized / search_memories
```

### Supabase setup

Create a table with at least these columns (the server only needs PostgREST):

```sql
create table memories (
  id          uuid primary key,
  userid      uuid not null,
  content     text not null,
  metadata    jsonb not null default '{}',
  importance  real not null default 0.5,
  created_at  timestamptz not null default now()
);
create index on memories (userid, created_at desc);
```

Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (service role — the server is meant to run
behind your own gateway, not be exposed to browsers).

## Connecting a client

**Claude Desktop / Claude Code** (via `mcp-remote` for HTTP servers):

```json
{
  "mcpServers": {
    "cognilearn-memory": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://127.0.0.1:8002/mcp/mcp",
               "--header", "X-User-Id: 11111111-1111-4111-8111-111111111111"]
    }
  }
}
```

**n8n** — *MCP Client* node, endpoint `https://<host>/mcp/mcp`, transport *HTTP Streamable*; pass the
learner id as a header from the workflow. CORS is open on `/mcp` and `Mcp-*` headers are exposed
for this use.

**LangFlow** — `src/custom_components/memory_tool.py` is a custom component
(`CogniLearn Unified Memory`) wrapping the embedding-based service for flows that run inside
LangFlow.

## Deployment

The `Dockerfile` builds a `python:3.12-slim` image and starts Gunicorn with Uvicorn workers,
honouring `$PORT` (Render / Railway style) with a `/healthz` health check:

```powershell
docker build -t cognilearn-mcp .
docker run --rm -p 8002:8002 --env-file .env cognilearn-mcp
```

`WORKERS`, `TIMEOUT` and `KEEPALIVE` can be overridden through the environment.

## Question-bank pipeline

`src/script/` and `data/` hold the offline pipeline that produced CogniLearn's first practice
bank. It is kept in this repository because the memory tools (`propose_question_specs`,
`record_practice_result`) are designed around the same tags.

| Step | Script | What it does |
| --- | --- | --- |
| 1. Spec | `data/raw/200 câu hỏi.pdf`, `data/raw/questions.json` | Brief and raw set of 200 Vietnamese maths questions with a fixed tag schema (`grade_level`, `domain`, `topic`, `sub_topic`, `question_type`, `cognitive_skills`, …). |
| 2. Tagging | `src/script/tag_questions.py` | LLM-based tagging with structured prompts built on LangExtract (see `THIRD_PARTY_NOTICES.md`). |
| 3. Embedding | `src/script/prepare_vectors.py` | Embeds questions through the Hugging Face inference API (a maths-domain BERT) — outputs in `data/processed/`. Gemini-embedded variants are there too. |
| 4. Load | `src/script/load_to_supabase.py` | Inserts questions + vectors into the Supabase `questions` table. |
| 5. Serve | `src/script/query/find_similar.py` | FastAPI endpoint `POST /tests/generate` that returns similar-question ids through the `match_similar_questions` pgvector RPC. |
| Analysis | `src/script/ai_engine/llm_based_analyzer.py`, `api.py` | LLM-based analysis of a learner's answers, writing results back through `MemoryService`. |

`data/raw/finetune_triplets.json` and `data/processed/final_vector_database_finetuned.json` are
the artefacts of a small fine-tuning experiment on the embedding model.

## Project layout

```text
src/
  memory_mcp_server.py      FastAPI app + FastMCP server (the deployable unit)
  core/memory_service.py    embedding-based memory (Gemini + Supabase RPC), used by the web app
  custom_components/        LangFlow component
  script/                   question-bank pipeline (tagging, embedding, loading, similarity API)
  langextract/              vendored Google LangExtract (Apache-2.0) — see THIRD_PARTY_NOTICES.md
data/                       raw and processed question-bank artefacts (~19 MB)
examples/                   memory_playground*.py — DuckDB + sentence-transformers experiments
scripts/dev/                environment and import diagnostics, manual test scripts
Dockerfile · pyproject.toml · uv.lock · requirements.txt · .env.example
```

## Status and limitations

- Built in 09/2025 for the CogniLearn prototype and not developed since; the ranking is
  deliberately simple.
- `_decode_jwt_sub` is a stub: bearer tokens are accepted but not verified. Put the server behind
  a gateway that authenticates the caller and sets `X-User-Id`.
- Supabase filtering on `metadata->>type` / `topic` uses PostgREST `or` chains; fine for
  per-learner volumes (hundreds of rows), not designed for cross-learner analytics.
- Code comments and tool descriptions are in Vietnamese.
- Git history before this README contains a committed virtualenv and a test database; they have
  been removed from the tree but not rewritten out of history.

## License

MIT — see [LICENSE](LICENSE). Third-party code: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
