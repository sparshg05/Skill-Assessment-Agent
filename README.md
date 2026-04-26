# SkillProbe — AI-Powered Skill Assessment & Personalised Learning Plan Agent

> *A resume tells you what someone claims to know — not how well they actually know it.*

SkillProbe is a production-grade AI agent that takes a **Job Description** and a **candidate's resume**, conducts a real conversational assessment of each required skill through adaptive multi-turn questioning, identifies genuine proficiency gaps, and generates a **personalised, prioritised learning roadmap** with curated resources and time estimates.

---

## Table of Contents

1. [What This Agent Does](#1-what-this-agent-does)
2. [How It Works — The Assessment Flow](#2-how-it-works--the-assessment-flow)
3. [System Architecture](#3-system-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Design Patterns & SOLID Principles](#6-design-patterns--solid-principles)
7. [Prerequisites](#7-prerequisites)
8. [Installation & Setup](#8-installation--setup)
9. [Running the Application](#9-running-the-application)
10. [Step-by-Step Testing Guide](#10-step-by-step-testing-guide)
11. [API Reference](#11-api-reference)
12. [Configuration Reference](#12-configuration-reference)
13. [Key Design Decisions & Tradeoffs](#13-key-design-decisions--tradeoffs)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. What This Agent Does

### The Problem

Traditional hiring relies on resumes that list skills without verifying depth. A candidate who used Docker once lists it alongside a candidate who has architected multi-cloud Kubernetes clusters. Both say "Docker". The resume cannot tell the difference.

### The Solution

SkillProbe closes this gap through **five orchestrated stages**:

| Stage | What Happens |
|-------|-------------|
| **Parsing** | Extracts structured skills from the JD (required vs nice-to-have) and resume (with claimed proficiency levels) |
| **Gap Mapping** | Aligns JD requirements against resume claims to build a prioritised assessment queue |
| **Adaptive Assessment** | Conducts a real multi-turn conversation — questions adapt based on each answer, drilling deeper on shallow responses and escalating on strong ones |
| **Gap Analysis** | Post-assessment: compares actual assessed scores against requirements to find real gaps |
| **Learning Plan** | Generates a personalised, sequenced roadmap with real resources, time estimates, and weekly milestones |

### What Makes It Different

- **Not a quiz** — the AI adapts to every answer. A shallow response triggers a clarifying follow-up. A confident answer gets a harder edge-case question.
- **Contradiction detection** — the assessor tracks evidence across turns and flags inconsistencies (e.g., claiming deep Docker experience but unable to explain multi-stage builds).
- **Confidence-gated progression** — the agent only moves to the next skill when it has sufficient confidence in its score (configurable threshold), not after a fixed number of questions.
- **Adjacent skill prioritisation** — the learning plan focuses on skills the candidate can realistically acquire given their existing knowledge, not just listing every gap.
- **Resumable sessions** — candidates can drop off mid-assessment and resume later. State persists in Redis with a configurable TTL.

---

## 2. How It Works — The Assessment Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ASSESSMENT LIFECYCLE                            │
└─────────────────────────────────────────────────────────────────────────┘

  POST /sessions              POST /sessions/{id}/respond (×N)
  ┌──────────┐                ┌────────────────────────────────────────┐
  │JD + Resume│               │         ASSESSMENT LOOP                │
  └────┬─────┘                │                                        │
       │                      │  ┌─────────────────────────────────┐   │
       ▼                      │  │  For each skill in priority order│   │
  ┌──────────┐                │  │                                  │   │
  │  PARSER  │ ──────────────►│  │  1. Generate adaptive question   │   │
  │  NODE    │                │  │  2. Wait for human response      │   │
  └──────────┘                │  │  3. Evaluate answer (score 1-5)  │   │
       │                      │  │  4. Update confidence + notes    │   │
       │ parsed skills        │  │  5. If confident → finalise skill│   │
       ▼                      │  │     Else → generate next question│   │
  ┌──────────┐                │  └─────────────────────────────────┘   │
  │ OPENING  │                │                                        │
  │ MESSAGE  │                │  Confidence threshold: 0.85            │
  └──────────┘                │  Max questions per skill: 4            │
       │                      └────────────────────────────────────────┘
       │ welcome msg                          │
       ▼                                      │ all skills done
  [CANDIDATE READY]                           ▼
                                    ┌──────────────────┐
                                    │  GAP ANALYSIS    │
                                    │  NODE            │
                                    │                  │
                                    │  assessed vs     │
                                    │  required levels │
                                    │  adjacency check │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │  LEARNING PLAN   │
                                    │  NODE            │
                                    │                  │
                                    │  • Sequencing    │
                                    │  • Resources     │
                                    │  • Milestones    │
                                    │  • Time estimates│
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    GET /sessions/{id}/report
```

### The Adaptive Questioning Engine

The assessment node maintains a `SkillAssessmentState` per skill that accumulates evidence across turns:

```
Round 1: Mid-level conceptual question
  → Shallow answer → Round 2: Simpler clarifying question
  → Strong answer  → Round 2: Harder edge-case / design question

Round 2: Based on R1 answer
  → Contradiction with R1? → Probe it naturally
  → Consistent + deep?     → Confidence rises, may stop early

Stopping conditions (whichever comes first):
  - confidence >= 0.85 (configurable)
  - questions_asked >= 4 (configurable)
```

### Proficiency Scale

| Score | Level | Description |
|-------|-------|-------------|
| 1 | No Knowledge | Wrong answers, contradicts basics, guessing |
| 2 | Surface Awareness | Knows buzzwords, no depth or application |
| 3 | Working Knowledge | Can apply with some guidance, understands core concepts |
| 4 | Proficient | Works independently, understands nuances and tradeoffs |
| 5 | Expert | Can teach it, design systems with it, handles edge cases |

---

## 3. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│                                                                 │
│   React + Vite (port 5173)                                      │
│   Zustand state │ Framer Motion animations │ Lucide icons       │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / SSE
┌──────────────────────────────▼──────────────────────────────────┐
│                          API LAYER                              │
│                                                                 │
│   FastAPI (port 8000)                                           │
│   POST /api/v1/assessment/sessions          (start session)     │
│   POST /api/v1/assessment/sessions/{id}/respond  (chat turn)    │
│   GET  /api/v1/assessment/sessions/{id}/report   (final report) │
│   POST /api/v1/assessment/sessions/upload   (file upload)       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                        AGENT LAYER                              │
│                                                                 │
│   AgentRunner (session lifecycle manager)                       │
│        │                                                        │
│        ├──► LangGraph Orchestrator (state machine)              │
│        │         │                                              │
│        │    ┌────┴──────────────────────────────────┐          │
│        │    │           NODE PIPELINE                │          │
│        │    │                                        │          │
│        │    │  parser_node                           │          │
│        │    │      ↓                                 │          │
│        │    │  assessment_node ◄─── (loop) ──────────│◄─ human  │
│        │    │      ↓ (complete)                      │          │
│        │    │  gap_analysis_node                     │          │
│        │    │      ↓                                 │          │
│        │    │  learning_plan_node                    │          │
│        │    └────────────────────────────────────────┘          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      SERVICE LAYER                              │
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   LLM Factory   │  │  Session Store   │  │  Resource     │  │
│  │                 │  │                  │  │  Discovery    │  │
│  │  OpenAI GPT-4o  │  │  Redis           │  │               │  │
│  │  Anthropic      │  │  (session state) │  │  Tavily API   │  │
│  │  (pluggable)    │  │                  │  │  + Curated DB │  │
│  └─────────────────┘  └──────────────────┘  └───────────────┘  │
│  ┌─────────────────┐                                            │
│  │ Document Parser │                                            │
│  │  PyMuPDF (PDF)  │                                            │
│  │  python-docx    │                                            │
└──┴─────────────────┴────────────────────────────────────────────┘
```

### State Machine Phases

```
INITIALISED
    │
    ▼
PARSING  ─────────────────────────────────────────────► ERROR
    │
    ▼
ASSESSING ◄──────────────────────────────┐
    │  awaiting_human_input=True          │
    │  (interrupt here, resume on respond)│
    │  [human submits answer]             │
    └─────────────────────────────────────┘
    │  all skills done
    ▼
ANALYSING ────────────────────────────────────────────► ERROR
    │
    ▼
PLANNING ─────────────────────────────────────────────► ERROR
    │
    ▼
COMPLETE
```

### Data Flow Per Request

```
Candidate message
    │
    ▼
api/routes.py                           ← validates request shape
    │
    ▼
agents/runner.py :: respond()           ← loads state from Redis
    │
    ├─► appends human message to conversation_history
    │
    ├─► nodes/assessment_node.py        ← evaluates answer + generates next Q
    │       │
    │       ├─► services/llm_factory.py :: call_llm_json()   (answer eval)
    │       └─► services/llm_factory.py :: call_llm_json()   (question gen)
    │
    ├─► (if phase==ANALYSING)
    │   └─► nodes/gap_analysis_node.py  ← computes gaps
    │
    ├─► (if phase==PLANNING)
    │   └─► nodes/learning_plan_node.py ← builds roadmap
    │           └─► services/resource_discovery.py  (concurrent fetches)
    │
    ├─► saves updated state to Redis
    │
    └─► returns RespondResponse to API
```

---

## 4. Tech Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Web Framework | **FastAPI** | 0.115.0 | Async API, SSE streaming, OpenAPI docs |
| ASGI Server | **Uvicorn** | 0.30.6 | Production-grade async server |
| Agent Orchestration | **LangGraph** | 0.2.28 | Stateful graph-based agent loop |
| LLM Integration | **LangChain** | 0.3.1 | Provider-agnostic LLM abstraction |
| LLM — Assessment | **llama-3.1-8b-instant** | — | Deep reasoning, adaptive questioning |
| LLM — Parsing | **llama-3.1-8b-instant** | — | Fast structured extraction (cost-optimised) |
| LLM — Planning | **llama-3.1-8b-instant** | — | Nuanced roadmap generation |
| Session State | **Redis** | 5.1.0 | Resumable sessions, TTL-based expiry |
| Data Validation | **Pydantic v2** | 2.9.2 | Type-safe domain models |
| PDF Parsing | **PyMuPDF** | 1.24.10 | Fast, accurate PDF text extraction |
| DOCX Parsing | **python-docx** | 1.1.2 | Word document parsing |
| Resource Search | **Tavily** | 0.4.0 | Live web search for learning resources |
| Retry Logic | **Tenacity** | 9.0.0 | Exponential backoff on LLM failures |
| Logging | **Structlog** | 24.4.0 | Structured JSON logging |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | **React** | 18.3.1 | Component-based UI |
| Build Tool | **Vite** | 5.4.8 | Fast HMR dev server + optimised builds |
| State Management | **Zustand** | 5.0.0 | Lightweight global state |
| Animations | **Framer Motion** | 11.11.0 | Page transitions, message animations |
| Icons | **Lucide React** | 0.453.0 | Clean, consistent icon set |
| Fonts | **Instrument Serif + Geist** | — | Editorial serif + clean sans pairing |

### Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| Session Store | **Redis** | Dockerised for local dev |
| Database | **PostgreSQL** | Optional — for persistent result storage |
| API Proxy | **Vite dev proxy** | Forwards `/api/*` to FastAPI in dev |

---

## 5. Project Structure

```
skillprobe/
│
├── backend/                          # FastAPI + LangGraph agent
│   ├── main.py                       # App entry point, lifespan, CORS, middleware
│   ├── config.py                     # Pydantic settings (env vars, all config)
│   ├── requirements.txt              # Pinned Python dependencies
│   ├── .env.example                  # Environment variable template
│   ├── .env                          # Your local secrets (gitignored)
│   │
│   ├── models/
│   │   └── domain.py                 # ALL Pydantic models: GraphState, Skills,
│   │                                 #   LearningPlan, API schemas, enums
│   │
│   ├── prompts/
│   │   └── templates.py              # Every LLM prompt template, centralised
│   │                                 #   Easy to A/B test and version
│   │
│   ├── services/
│   │   ├── llm_factory.py            # Provider-agnostic LLM factory
│   │   │                             #   get_parser_llm() / get_assessor_llm()
│   │   ├── session_store.py          # Redis repository (save/load/delete)
│   │   ├── document_parser.py        # PDF + DOCX → plain text
│   │   └── resource_discovery.py     # Tavily search + curated fallback DB
│   │
│   ├── nodes/                        # LangGraph node functions
│   │   ├── parser_node.py            # JD + resume → structured skill map
│   │   ├── assessment_node.py        # Adaptive Q&A: question gen + answer eval
│   │   ├── gap_analysis_node.py      # Assessed vs required → SkillGap objects
│   │   └── learning_plan_node.py     # Gaps → personalised roadmap + resources
│   │
│   ├── agents/
│   │   ├── orchestrator.py           # LangGraph graph: nodes + edges + routing
│   │   └── runner.py                 # Session lifecycle: start / respond / report
│   │
│   ├── api/
│   │   └── routes.py                 # FastAPI routes (JSON + SSE streaming)
│   │
│   └── utils/
│       └── logging.py                # Structlog setup (JSON prod / pretty dev)
│
└── frontend/                         # React + Vite app
    ├── index.html                     # HTML entry point
    ├── vite.config.js                 # Vite config + API proxy
    ├── package.json                   # Dependencies
    └── src/
        ├── main.jsx                   # ReactDOM render
        ├── App.jsx                    # AnimatePresence view router
        ├── index.css                  # Design tokens as CSS variables
        │
        ├── services/
        │   └── api.js                 # Fetch wrapper for all API calls
        │
        ├── store/
        │   └── index.js               # Zustand global store
        │
        └── components/
            ├── ui/
            │   └── index.jsx          # Button, Badge, ScoreBar, ProgressRing, etc.
            ├── setup/
            │   └── SetupPage.jsx      # Landing page + JD/resume form
            ├── assessment/
            │   └── ChatPage.jsx       # Chat UI + skill sidebar + progress ring
            └── report/
                └── ReportPage.jsx     # Full report: stats, skill cards, learning paths
```

---

## 6. Design Patterns & SOLID Principles

### SOLID Principles Applied

| Principle | Where | How |
|-----------|-------|-----|
| **Single Responsibility** | Every module | `session_store.py` only stores sessions. `document_parser.py` only parses files. `assessment_node.py` only runs Q&A. One reason to change each. |
| **Open / Closed** | `llm_factory.py`, `resource_discovery.py` | Add new LLM providers or resource sources by *extending*, never modifying existing code |
| **Liskov Substitution** | `BaseChatModel` | Any `ChatOpenAI`, `ChatAnthropic`, or future model can replace any other without breaking assessment logic |
| **Interface Segregation** | `get_parser_llm()` / `get_assessor_llm()` / `get_planner_llm()` | Each node depends only on the LLM interface it needs — cheaper models for simpler tasks |
| **Dependency Inversion** | `AgentRunner` → nodes → services | High-level orchestration depends on node abstractions; concrete LLM bindings happen at the lowest layer |

### Design Patterns Applied

| Pattern | Location | Why |
|---------|----------|-----|
| **Factory** | `services/llm_factory.py` | Centralises LLM creation; swap provider via `.env` with zero code changes |
| **State Machine** | `agents/orchestrator.py` | Explicit phase transitions (PARSING → ASSESSING → ANALYSING → PLANNING → COMPLETE); state is serialisable and resumable |
| **Strategy** | `services/resource_discovery.py` | Two interchangeable resource strategies (Tavily live search + curated fallback); graceful degradation if Tavily is down |
| **Facade** | `agents/runner.py` | Three-method interface (`start_session`, `respond`, `get_report`) hides entire LangGraph + Redis + multi-LLM complexity |
| **Singleton** | `config.py`, `session_store.py`, `runner.py` | One Redis pool, one settings parse, one runner instance per process |

---

## 7. Prerequisites

Before running SkillProbe, ensure you have:

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | 3.12 recommended |
| **Node.js** | 18+ | For the React frontend |
| **Redis** | 6+ | For session state. Easiest via Docker |
| **Groq API Key** | — | GPT-4o access required |
| **Tavily API Key** | — | Optional but recommended for live resource search |

### Get your API keys

- **Groq:** https://console.groq.com/keys
- **OpenAI (alternative):** https://platform.openai.com/api-keys
- **Anthropic (alternative):** https://console.anthropic.com/settings/keys
- **Tavily (optional):** https://app.tavily.com — free tier available

---

## 8. Installation & Setup

### Step 1 — Clone and navigate

```bash
git clone https://github.com/your-org/skillprobe.git
cd skillprobe
```

### Step 2 — Start Redis

The easiest way is Docker:

```bash
docker run -d --name skillprobe-redis -p 6379:6379 redis:alpine
```

Verify it's running:

```bash
docker exec skillprobe-redis redis-cli ping
# → PONG
```

### Step 3 — Configure the backend

```bash
cd backend
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
# Required — choose one provider
OPENAI_API_KEY=sk-proj-...your-key-here...
LLM_PROVIDER=openai

# Optional but recommended
TAVILY_API_KEY=tvly-...your-key-here...

# Redis (default works if using Docker above)
REDIS_URL=redis://localhost:6379/0
```

### Step 4 — Install backend dependencies

```bash
# From the backend/ directory
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Step 5 — Install frontend dependencies

```bash
cd ../frontend
npm install
```

---

## 9. Running the Application

### Start the backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

API documentation is available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Start the frontend

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v5.4.8  ready in 312ms

  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser.

---

## 10. Step-by-Step Testing Guide

### Method A — Using the Web UI (Recommended)

#### Step 1 — Open the app

Navigate to http://localhost:5173

You'll see the SkillProbe landing page with two text areas.

#### Step 2 — Load the sample data

Click **"load sample"** in the top-right corner. This populates a realistic Senior Backend Engineer JD and a candidate resume with intentional gaps.

Alternatively, paste your own JD and resume into the two fields.

#### Step 3 — Configure commitment

Select how many hours per week the candidate can commit to learning (used for the learning plan time estimates). Default is 10h/week.

#### Step 4 — Start the assessment

Click **"Start Assessment"**. The system will:
1. Parse both documents (takes 5–10 seconds)
2. Build the skill map
3. Generate a personalised opening message

The chat interface opens with the AI's greeting.

#### Step 5 — Complete the assessment

Respond to each question naturally. The AI will:
- Ask 2–4 questions per skill
- Adapt based on your answers (deeper on strong answers, simpler on weak ones)
- Transition naturally between skills

**Tips for realistic testing:**
- Give shallow answers to some skills (e.g., "I've used it a bit") to see follow-up questions
- Give confident, detailed answers to others to see the AI escalate difficulty
- Try giving contradictory answers across two turns for the same skill

The progress ring and sidebar track your progress in real time.

#### Step 6 — View the report

Once all skills are assessed, click **"View Report"** to see:
- Overall match percentage
- Per-skill scores with proficiency levels
- Executive summary
- Skill gaps with priority
- Full learning plan with sequenced paths, milestones, and curated resources

---

### Method B — Using the REST API directly (curl)

#### Step 1 — Start a session

```bash
curl -s -X POST http://localhost:8000/api/v1/assessment/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "jd_text": "Senior Python Engineer. Required: Python 4+ years, FastAPI, PostgreSQL, Docker, Redis, AWS. Nice to have: Kubernetes, system design experience.",
    "resume_text": "Jane Doe, Software Engineer, 3 years. Skills: Python (Django, some FastAPI), MySQL, basic Docker. Used AWS S3 once. No Kubernetes experience.",
    "commitment_hours_per_week": 10
  }' | python3 -m json.tool
```

**Expected response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Hi Jane! Welcome to your skill assessment for the Senior Python Engineer role...",
  "phase": "assessing",
  "candidate_name": "Jane Doe",
  "skills_to_assess": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "AWS"]
}
```

Save the `session_id` for subsequent calls.

#### Step 2 — Respond to the first question

```bash
SESSION_ID="550e8400-e29b-41d4-a716-446655440000"

curl -s -X POST http://localhost:8000/api/v1/assessment/sessions/$SESSION_ID/respond \
  -H "Content-Type: application/json" \
  -d '{"message": "I have been using Python for about 3 years, mainly with Django for web applications. I understand decorators, context managers, and async basics but haven'\''t dug too deep into the internals."}' \
  | python3 -m json.tool
```

**Expected response:**
```json
{
  "session_id": "550e8400-...",
  "bot_message": "Good. You mentioned async basics — can you walk me through a specific situation where you chose asyncio over threading, and what tradeoffs you considered?",
  "phase": "assessing",
  "progress": {
    "total_skills": 6,
    "completed_skills": 0,
    "current_skill": "Python",
    "percent_complete": 0,
    "phase": "assessing"
  },
  "is_complete": false
}
```

#### Step 3 — Continue responding

Keep calling the `/respond` endpoint with answers until `is_complete: true` is returned.

```bash
# Keep responding until you see "is_complete": true
curl -s -X POST http://localhost:8000/api/v1/assessment/sessions/$SESSION_ID/respond \
  -H "Content-Type: application/json" \
  -d '{"message": "I used asyncio for an API that needed to call three external services concurrently. With threading we had GIL issues for CPU-bound parts, so I used asyncio for the IO-bound calls and multiprocessing for the heavy computation."}' \
  | python3 -m json.tool
```

#### Step 4 — Retrieve the report

Once `is_complete: true`:

```bash
curl -s http://localhost:8000/api/v1/assessment/sessions/$SESSION_ID/report \
  | python3 -m json.tool
```

**Expected response structure:**
```json
{
  "session_id": "...",
  "candidate_name": "Jane Doe",
  "job_title": "Senior Python Engineer",
  "phase": "complete",
  "overall_match_percent": 62.0,
  "assessed_skills": [
    {
      "skill": "Python",
      "claimed_level": 4,
      "assessed_score": 3,
      "level": "working_knowledge",
      "tier": "must_have",
      "questions_asked": 3,
      "evidence": "Solid understanding of async patterns and concurrency tradeoffs..."
    }
  ],
  "skill_gaps": [
    {
      "skill_name": "Kubernetes",
      "required_level": 3,
      "assessed_level": 0,
      "gap_size": 3,
      "is_adjacent": true,
      "priority": 1
    }
  ],
  "learning_plan": {
    "total_estimated_hours": 47.0,
    "total_estimated_weeks": 4.7,
    "commitment_hours_per_week": 10,
    "executive_summary": "Jane has a strong Python foundation...",
    "recommended_sequence": ["Docker", "Kubernetes", "AWS", "FastAPI"],
    "quick_wins": ["FastAPI"],
    "skill_paths": [...]
  }
}
```

---

### Method C — Using the Swagger UI

1. Navigate to http://localhost:8000/docs
2. Use the interactive interface to call each endpoint
3. Expand each endpoint, click "Try it out", fill in the request body, and execute

---

### Health Check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

```json
{
  "status": "healthy",
  "provider": "openai",
  "assessor_model": "gpt-4o"
}
```

---

## 11. API Reference

### Base URL
```
http://localhost:8000/api/v1/assessment
```

### Endpoints

#### `POST /sessions`
Start a new assessment session with raw text input.

**Request body:**
```json
{
  "jd_text": "string (min 50 chars)",
  "resume_text": "string (min 50 chars)",
  "commitment_hours_per_week": 10
}
```

**Response:** `StartSessionResponse`
```json
{
  "session_id": "uuid",
  "message": "string",
  "phase": "assessing",
  "candidate_name": "string",
  "skills_to_assess": ["skill1", "skill2"]
}
```

---

#### `POST /sessions/upload`
Start a session by uploading PDF or DOCX files.

**Form data:**
- `jd_file`: File (PDF/DOCX/TXT)
- `resume_file`: File (PDF/DOCX/TXT)
- `commitment_hours_per_week`: integer (default: 10)

---

#### `POST /sessions/{session_id}/respond`
Submit a candidate's answer. Returns the next question or completion message.

**Request body:**
```json
{
  "message": "string"
}
```

**Response:** `RespondResponse`
```json
{
  "session_id": "uuid",
  "bot_message": "string",
  "phase": "assessing | analysing | planning | complete",
  "progress": {
    "total_skills": 6,
    "completed_skills": 2,
    "current_skill": "Docker",
    "percent_complete": 33,
    "phase": "assessing"
  },
  "is_complete": false
}
```

---

#### `POST /sessions/{session_id}/respond/stream`
Same as above but streams the bot response as Server-Sent Events.

**SSE Events:**
- `status` — `{ "status": "thinking" }`
- `token` — `{ "token": "word " }` (streamed word by word)
- `complete` — `{ "message": "...", "phase": "...", "progress": {...}, "is_complete": false }`
- `error` — `{ "error": "message", "code": 500 }`

---

#### `GET /sessions/{session_id}/report`
Retrieve the full assessment report and learning plan.

**Response:** `SessionReportResponse` — see [Step 4 above](#step-4--retrieve-the-report) for full schema.

---

#### `GET /sessions/{session_id}/status`
Quick status check — phase, progress, whether awaiting input.

---

## 12. Configuration Reference

All configuration lives in `backend/.env`. Every value has a sensible default.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required if `LLM_PROVIDER=openai`) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required if `LLM_PROVIDER=anthropic`) |
| `GROQ_API_KEY` - | Groq API key (required if `LLM_PROVIDER=groq`) |
| `LLM_PROVIDER` | `groq` 
| `ASSESSOR_MODEL` | `llama-3.1-8b-instant` | Model for the assessment and planning nodes |
| `PARSER_MODEL` | `llama-3.1-8b-instant` | Model for the parsing node (cheaper, faster) |
| `PLANNER_MODEL` | `llama-3.1-8b-instant` | Model for gap analysis and learning plan |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL URL (optional) |
| `TAVILY_API_KEY` | — | Tavily API key for live resource search |
| `APP_ENV` | `development` | `development` (pretty logs) or `production` (JSON logs) |
| `APP_PORT` | `8000` | Port to run the FastAPI server on |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins |
| `SESSION_TTL_SECONDS` | `7200` | How long sessions persist in Redis (2 hours) |
| `MAX_QUESTIONS_PER_SKILL` | `4` | Maximum questions per skill before forcing finalisation |
| `CONFIDENCE_THRESHOLD` | `0.85` | Confidence required to stop early and finalise a skill |

### Switching to Anthropic

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...your-key...
```

No code changes required. All nodes use `get_assessor_llm()` which reads from config.

### Tuning Assessment Depth vs Speed

For a **faster** assessment (fewer questions):
```env
MAX_QUESTIONS_PER_SKILL=2
CONFIDENCE_THRESHOLD=0.70
```

For **deeper** assessment (more questions, higher confidence required):
```env
MAX_QUESTIONS_PER_SKILL=6
CONFIDENCE_THRESHOLD=0.92
```

---

## 13. Key Design Decisions & Tradeoffs

### Why LangGraph over CrewAI or AutoGen?

The assessment loop is fundamentally a **stateful graph** with conditional edges:
- Assessment can loop (multiple questions per skill)
- Each node decision depends on accumulated state (confidence, evidence)
- State must be serialisable for resumable sessions

LangGraph's explicit state machine model fits this perfectly. CrewAI's agent-first model would make the loop structure implicit and harder to control.

### Why Redis for state (not in-memory)?

**Horizontal scalability.** With in-memory state, a candidate's session is pinned to one server. With Redis, any server in a pool can handle any session. Run 50 workers behind a load balancer with no code changes.

### Why separate parser and assessor LLMs?

**Cost optimisation.** Parsing (extracting structured JSON from text) is a simpler task than adaptive assessment. `gpt-4o-mini` at ~10× lower cost handles parsing correctly. `gpt-4o` reasoning depth is only paid for where it matters: the Q&A loop and learning plan.

### Why centralise prompts in `templates.py`?

**Iterability.** Prompt engineering is an ongoing process. Centralising every prompt in one file means you can A/B test, version, and improve prompts without hunting through node files. It's also the first place to look when assessment quality degrades.

### Why Tavily + curated fallback for resources?

**Reliability.** Tavily provides fresh, relevant resources but can fail (rate limits, network issues). The curated database ensures the learning plan always has quality resources. The merge strategy (Tavily first, curated supplement) gives the best of both: freshness and reliability.

### Tradeoff: Assessment quality vs candidate experience

More questions per skill = better signal. But candidates get fatigued after 30+ minutes. The default of 4 questions max and 8 skills max (32 questions max) is calibrated for a ~20-minute session. Adjust `MAX_QUESTIONS_PER_SKILL` and the `MAX_SKILLS` constant in `parser_node.py` based on your use case.

---

## 14. Troubleshooting

### Redis connection error

```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```

Start Redis:
```bash
docker run -d -p 6379:6379 redis:alpine
```

Or verify it's running:
```bash
docker ps | grep redis
redis-cli ping   # should return PONG
```

---

### OpenAI API error — 401 Unauthorized

```
openai.AuthenticationError: Incorrect API key provided
```

Check your `.env`:
```bash
cat backend/.env | grep OPENAI
```

Ensure there are no extra spaces or quotes around the key value.

---

### "Session not found" on respond

Sessions expire after `SESSION_TTL_SECONDS` (default 2 hours). Start a new session, or increase the TTL in `.env`.

---

### LLM returns invalid JSON

The LLM occasionally returns malformed JSON. The system retries up to 3 times with exponential backoff via Tenacity. If it persists, the error will surface as a 500 with `"LLM returned invalid JSON"`. This is usually a transient issue; retry the request.

---

### Frontend shows "Network Error"

Ensure:
1. The backend is running on port 8000: `curl http://localhost:8000/health`
2. The Vite dev server is running on port 5173
3. The Vite proxy in `vite.config.js` is configured: `target: 'http://localhost:8000'`
4. CORS origins in `.env` include `http://localhost:5173`

---

### Slow first response

The first response of a session runs the parser (2 LLM calls in parallel) plus opening message generation. Expect 8–15 seconds on the first call. Subsequent turns (per-question) are 3–6 seconds.