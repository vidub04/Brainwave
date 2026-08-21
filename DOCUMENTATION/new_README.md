# RoleReady

**RoleReady** is an AI-powered adaptive mock interview platform. It simulates realistic technical and behavioral interviews through two AI interviewer personas, adjusts question difficulty and topic in real time based on how you're performing, and produces an evidence-backed final report with a personalized study plan.

---

## ✨ Features

- **Dual AI Interviewers** — Alex (Senior Software Engineer, technical) and Ricky (HR Manager, behavioral)
- **Adaptive Difficulty Engine** — a rule-based guardrail layer + AI refinement decides whether to go harder, easier, follow up, or switch topics after every answer
- **Resume-Aware Questions** — upload a PDF/DOCX resume; it's parsed and blended into question generation
- **Role & JD Targeting** — pick a target role and paste a job description to calibrate the interview plan
- **Candidate Memory** — the engine remembers your past interviews (recurring weak/strong skills, score trend) and builds new sessions around them
- **Anti-Repetition Engine** — prevents the AI from asking near-duplicate questions within a session
- **Voice Input/Output** — browser-native speech-to-text for answering, text-to-speech for hearing the interviewer
- **Live "Judge Decision Log"** — a transparent, real-time view into why the engine made each adaptation decision
- **Evidence-Backed Final Report** — score breakdown, strengths/weaknesses tied to exact Q&A turns, and a 7/14/30-day prep roadmap
- **Progress Dashboard** — score trends across sessions, charted per skill category
- **Secure Per-User Data** — Supabase Auth + Row Level Security

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| AI Model | Google Gemini API (`google-genai` / REST) |
| Auth & Database | Supabase (PostgreSQL + Auth) |
| Local Cache | SQLite (interview state cache) |
| Frontend | HTML, CSS, vanilla JavaScript |
| Templating | Jinja2 |
| Resume Parsing | `pdfplumber` (PDF), `python-docx` (DOCX) |

---

## 📁 Project Structure

```text
RoleReady/
├── main.py                        # FastAPI app: pages, API routes, resume upload, legacy routes
├── auth.py                        # Supabase auth dependency + service-role client
├── resume.py                      # Resume text extraction & AI structuring
├── requirements.txt
│
├── engine/                        # The adaptive interview pipeline
│   ├── models.py                  # Shared Pydantic data models
│   ├── llm_client.py              # Gemini API wrapper (JSON mode, retries, fallbacks)
│   ├── planner.py                 # Builds the initial interview plan
│   ├── question_generator.py      # Generates the next question
│   ├── anti_repetition.py         # Duplicate-question detector
│   ├── evaluator.py               # Grades candidate answers
│   ├── adaptation_engine.py       # Decides the next adaptation action
│   ├── state_manager.py           # Persists interview state (memory/SQLite/Supabase)
│   ├── report_generator.py        # Builds the final report + study plan
│   ├── candidate_memory.py        # Aggregates past scorecards into candidate memory
│   ├── orchestrator.py            # Coordinates the full turn-by-turn pipeline
│   └── __init__.py
│
├── supabase_schema.sql            # Initial schema: conversations, messages, resumes
├── add_target_role_migration.sql  # Adds `target_role` column to conversations
├── add_scorecards_table.sql       # Adds the scorecards table
│
├── templates/
│   ├── login.html
│   ├── index.html
│   └── dashboard.html
│
└── static/
    ├── style.css
    ├── script.js                  # Interview chat UI, voice I/O, API calls
    ├── dashboard.js                # Progress dashboard rendering
    └── auth.js                    # Supabase auth (sign up/in/out, session handling)
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project
- A [Google Gemini API key](https://ai.google.dev/)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up the database

In the Supabase SQL Editor, run in order:

1. `supabase_schema.sql` — creates `conversations`, `messages`, `resumes` + RLS policies
2. `add_target_role_migration.sql` — adds the `target_role` column
3. `add_scorecards_table.sql` — creates the `scorecards` table used by the dashboard

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

Create `static/config.js` (gitignored — used by the frontend to talk to Supabase Auth directly):

```js
const SUPABASE_URL = "your_supabase_project_url";
const SUPABASE_ANON_KEY = "your_supabase_anon_key";
```

### 5. Run the app

```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000` to sign up or log in, then you'll be redirected to `/app` to start an interview.

---

## 🗄️ Database Schema

| Table | Purpose |
|---|---|
| `conversations` | One row per interview session (role, title, owner) |
| `messages` | Every chat turn exchanged during an interview |
| `resumes` | Uploaded resumes + AI-structured skills/experience/education |
| `scorecards` | Final results of each completed interview (8 category scores, strengths/weaknesses, recommendation) — used to power the progress dashboard and candidate memory |

All tables have Row Level Security enabled (`auth.uid() = user_id`). The backend uses Supabase's service-role key for trusted server-side reads/writes.

---

## 🔄 How an Interview Works

1. **Create** — role + resume + JD are analyzed by the `InterviewPlanner`, producing a skill list, difficulty baseline, and stage plan (optionally informed by memory of the candidate's past interviews).
2. **Start** — the `AdaptiveDecisionEngine` picks the top-priority skill and difficulty; the `InterviewerAgent` writes Question 1.
3. **Each turn** — the `EvaluationAgent` scores the answer → the `AdaptiveDecisionEngine` applies guardrail rules (refined by AI, capped at ±1 difficulty per turn) to decide what happens next → the `InterviewerAgent` generates the next question (checked for repetition) → state is saved.
4. **End** — once the target question count is reached (or the engine ends early), the `InterviewReportGenerator` produces a full scorecard with evidence-backed weaknesses and a 7/14/30-day study plan, which is saved to `scorecards`.
5. **Dashboard** — past scorecards are aggregated into score trends and a "candidate memory" summary, both shown on `/dashboard`.

---

## 🔮 Future Additions

- Native coding round with a curated question bank and real code execution/grading
- Video-based interviews
- Company-specific interview modes
- Multi-language code execution (JS, Java, C++)
- AI coach / feedback with improved model answers

---

## 🎯 Project Goal

RoleReady aims to make interview preparation more interactive and personalized by simulating realistic, adaptive conversations rather than presenting a fixed list of questions — helping candidates build both technical depth and communication skill through practice that responds to how they're actually doing.