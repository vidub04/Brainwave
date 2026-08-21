# RoleReady

RoleReady is a production-grade **adaptive AI mock interview engine**. Rather than reading off a fixed question list, it runs a real agentic pipeline: a planner builds a personalized interview blueprint from your resume and target role, an evaluator diagnoses every answer, and a decision engine adjusts difficulty and topic focus in real time — the same way a genuinely reactive human interviewer would.

Two AI personas conduct the interview, a live in-browser code editor handles the coding round with real test execution, and every session ends with an evidence-backed scorecard and a 7/14/30-day prep roadmap.

---

## ✨ Features

### 🧠 Adaptive Interview Engine (core differentiator)

* **Interview Planner** — analyzes the candidate's resume, job description, and target role to generate a structured interview plan (skills to probe, priority order, question mix).
* **Evaluation Agent** — scores every answer against a rigorous rubric and diagnoses *why* it was strong or weak, not just a number.
* **Adaptive Decision Engine** — decides in real time whether to go deeper, ease off, pivot topic, or move on, based on the evaluation — difficulty rises and falls with actual performance instead of following a script.
* **Deterministic backend turn/question counter** — question progress ("Question 6/8") is tracked authoritatively on the backend, not inferred by the LLM, so it never loses count even when follow-up questions are mixed in.
* **Anti-repetition engine** — uses n-gram similarity and concept-overlap checks to stop the interviewer from asking near-duplicate questions.
* **Long-term candidate memory** — tracks recurring strengths/weaknesses and score trends *across* past interviews, not just within one session, and feeds that context into future interview plans.
* **Judge Decision Log** — an inspectable, real-time log of every adaptation decision the engine made and why (difficulty change, topic pivot, etc.) — built for transparency during demos/judging.

### 🤖 Dual AI Interviewers

* **Alex** — Senior Software Engineer persona; technical depth, DSA, system design, OOP, DBMS, OS, networks, AI/ML, resume-project deep dives, coding round.
* **Ricky** — HR Manager persona; communication, behavioral, leadership, teamwork, conflict resolution, career goals.
* A hidden metadata protocol (`[SPEAKER:...][DIFFICULTY:...][CODE:...]`) is prefixed to every model response and parsed client-side to drive the correct avatar, difficulty badge, and code-editor toggle — a lightweight alternative to full multi-agent infrastructure.

### 💻 Live Coding Round

* In-chat code editor that opens automatically when the interviewer assigns a coding question.
* Backed by a structured coding-question bank (`coding_questions` table / `coding_bank.py`) tagged by skill, role, and difficulty.
* Submitted code is actually executed (sandboxed subprocess, timeout-protected) against the question's test cases — pass/fail results feed back into the evaluation, it isn't just "looks-right" LLM grading.

### 📄 Resume-Aware Personalization

* Upload a `.pdf` or `.docx` resume.
* Text is extracted (`pdfplumber` / `python-docx`) and structured into name, current role, years of experience, skills, past roles, education, and summary via Gemini.
* The interview planner and question generator blend this directly into what gets asked.

### 📊 Performance Analytics Dashboard (`/dashboard`)

* Score trend chart across all past sessions, per category (technical knowledge, problem solving, CS fundamentals, project knowledge, communication, confidence, leadership, behavioral skills).
* Summary stats: total interviews, average score, change since first session.
* "What We Remember About You" panel — recurring weak/strong skills and trend direction, powered by long-term candidate memory.
* Full session table with role, date, score, and hiring recommendation per past interview.

### 👤 User Profile (`/profile`)

* Account identity (name/email, avatar initials, member-since date).
* Quick stats: interviews completed, average score, last interview date.
* Résumé-on-file card showing the most recently parsed résumé, with an upload/replace action.

### 🔐 Accounts (Supabase Auth)

* Dedicated **Sign In** (`/`) and **Sign Up** (`/signup`) pages.
* Instant auto-verified sign-up (bypasses SMTP email confirmation, backed by the Supabase admin API) — optional full name is stored in user metadata.
* JWT verification + Row Level Security: every user's interviews, messages, résumés, and scorecards are private to their account.

### 📜 Conversation History & Resumability

* Past interview sessions are listed in a ChatGPT-style sidebar and can be revisited.
* In-progress interviews can be resumed from saved candidate state.

### 🗣️ Voice Output

* Optional spoken delivery of interviewer questions via the browser-native `speechSynthesis` API — toggle on/off from the interview header.

### 📈 Evidence-Backed Final Report

* On completion, a report generator produces an overall score, category breakdown, strengths/weaknesses with supporting evidence from the transcript, a hiring recommendation, and a **7/14/30-day preparation roadmap**.
* This report is what gets persisted to the `scorecards` table and rendered on the dashboard.

---

## 🛠️ Tech Stack

* **Frontend:** HTML, CSS, vanilla JavaScript (Jinja2-rendered templates)
* **Backend:** FastAPI (Python)
* **AI Model:** Google Gemini API (`google-genai`) — planner, evaluator, adaptation engine, question generator, and report generator each run as focused agent prompts
* **Auth & Database:** Supabase (PostgreSQL + Auth + Row Level Security)
* **Interview State:** SQLite-backed local state manager (`engine/state_manager.py`) for live session tracking, synced to Supabase for durable history
* **Code Execution:** Python subprocess sandbox with timeout enforcement
* **Resume Parsing:** `pdfplumber` (PDF), `python-docx` (DOCX)
* **Templating:** Jinja2

---

## 📁 Project Structure

```text
Brainwave-main/
├── main.py                              # FastAPI app: pages, auth, adaptive interview API, dashboard/profile APIs
├── auth.py                              # Supabase JWT verification dependency + service-role client
├── resume.py                            # Resume text extraction & structuring
├── requirements.txt
│
├── engine/                              # Adaptive Interview Engine
│   ├── orchestrator.py                  # Ties planner + evaluator + adaptation engine + state together
│   ├── planner.py                       # Builds the personalized interview plan from resume/JD/role
│   ├── evaluator.py                     # Scores & diagnoses each candidate answer
│   ├── adaptation_engine.py             # Decides difficulty/topic adaptation each turn
│   ├── question_generator.py            # Generates the next question given engine decisions
│   ├── anti_repetition.py               # Prevents near-duplicate questions
│   ├── candidate_memory.py              # Long-term, cross-session candidate memory
│   ├── coding_bank.py                   # Coding question bank (by skill/role/difficulty)
│   ├── code_executor.py                 # Sandboxed execution of candidate code vs. test cases
│   ├── report_generator.py              # Final evidence-backed report + 7/14/30-day prep plan
│   ├── state_manager.py                 # Persistent per-interview candidate state (SQLite)
│   └── models.py                        # Pydantic schemas shared across the engine
│
├── database_schemas/
│   ├── supabase_schema.sql              # conversations, messages, resumes (+ RLS)
│   ├── add_target_role_migration.sql    # target_role column on conversations
│   ├── add_scorecards_table.sql         # scorecards table (+ RLS) for the dashboard
│   └── add_coding_questions.sql         # coding_questions table (bank storage)
│
├── templates/
│   ├── login.html                       # Sign in
│   ├── signup.html                      # Sign up (separate from login)
│   ├── index.html                       # Main interview interface
│   ├── dashboard.html                   # Performance analytics
│   └── profile.html                     # User profile
│
└── static/
    ├── style.css
    ├── script.js                        # Interview UI, role selector, code editor, resume upload
    ├── auth.js                          # Supabase auth (sign in/out, session handling)
    ├── signup.js                        # Sign-up flow (auto-verify + auto sign-in)
    ├── dashboard.js                     # Chart rendering, summary stats, session table
    └── profile.js                       # Profile data + résumé upload
```

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.11+
* A [Supabase](https://supabase.com) project
* A [Google Gemini API key](https://ai.google.dev/)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up the database

In the Supabase SQL Editor, run these in order:

1. `database_schemas/supabase_schema.sql` — creates `conversations`, `messages`, `resumes`, indexes, and RLS policies.
2. `database_schemas/add_target_role_migration.sql` — adds the `target_role` column used by the role selector.
3. `database_schemas/add_scorecards_table.sql` — creates the `scorecards` table (+ RLS) that powers the dashboard and profile stats.
4. `database_schemas/add_coding_questions.sql` — creates the `coding_questions` table used by the coding round.
   * This table only defines empty structure — seed it with actual questions before relying on the coding round in production.
   * It has RLS enabled with no policies, which is intentional: the backend talks to Supabase with the service-role key (which bypasses RLS), so only your server can read/write it — the public anon key cannot.

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

Create `static/config.js` (used by the frontend to talk to Supabase Auth directly — this file is gitignored):

```js
const SUPABASE_URL = "your_supabase_project_url";
const SUPABASE_ANON_KEY = "your_supabase_anon_key";
```

### 5. Run the app

```bash
uvicorn main:app --reload
```

* `/` — sign in
* `/signup` — create an account
* `/app` — main interview interface (select role, upload résumé, start interview)
* `/dashboard` — performance analytics across past sessions
* `/profile` — account info, stats, résumé on file

---

## 🗄️ Database Schema

RoleReady uses **Supabase (PostgreSQL)** to persist accounts, interview sessions, chat history, résumés, and scorecards, isolated per user.

### `conversations`

One row per interview session.

| Column        | Type      | Description                                                       |
| ------------- | --------- | ------------------------------------------------------------------ |
| `id`          | UUID      | Interview/session id (shared with the engine's `interview_id`).   |
| `user_id`     | UUID      | Owning user.                                                       |
| `title`       | Text      | Session title (defaults to **Interview**).                        |
| `target_role` | Text      | Role selected for this interview.                                  |
| `created_at`  | Timestamp | Creation time.                                                      |

### `messages`

Every chat turn exchanged during an interview.

| Column            | Type      | Description                                              |
| ----------------- | --------- | ---------------------------------------------------------- |
| `id`              | UUID      | Message id.                                                |
| `conversation_id` | UUID      | Links to `conversations`.                                  |
| `user_id`         | UUID      | Owning user.                                                |
| `role`            | Text      | `user` or `bot`.                                            |
| `content`         | Text      | Message content (bot messages carry the hidden `[SPEAKER:][DIFFICULTY:][CODE:]` metadata prefix). |
| `created_at`      | Timestamp | Time sent.                                                  |

### `resumes`

Uploaded résumés and their structured, Gemini-parsed content.

| Column       | Type      | Description                                                  |
| ------------ | --------- | -------------------------------------------------------------- |
| `id`         | UUID      | Résumé id.                                                      |
| `user_id`    | UUID      | Owning user.                                                    |
| `filename`   | Text      | Original filename.                                              |
| `raw_text`   | Text      | Full extracted text.                                             |
| `structured` | JSONB     | `{ name, current_role, years_experience, skills, past_roles, education, summary }` |
| `created_at` | Timestamp | Upload time.                                                     |

### `scorecards`

One row per completed interview — the source of truth for the dashboard and profile stats.

| Column                             | Type      | Description                                    |
| ----------------------------------- | --------- | ------------------------------------------------ |
| `id`                                | UUID      | Scorecard id.                                    |
| `user_id`                           | UUID      | Owning user.                                     |
| `conversation_id`                   | UUID      | Links to `conversations`.                        |
| `target_role`                       | Text      | Role interviewed for.                            |
| `technical_knowledge`               | Int       | 0–10.                                            |
| `problem_solving`                   | Int       | 0–10.                                            |
| `core_cs_fundamentals`              | Int       | 0–10.                                            |
| `project_knowledge`                 | Int       | 0–10.                                            |
| `communication`                     | Int       | 0–10.                                            |
| `confidence`                        | Int       | 0–10.                                            |
| `leadership`                        | Int       | 0–10.                                            |
| `behavioral_skills`                 | Int       | 0–10.                                            |
| `strengths`                         | JSONB     | List of evidenced strengths.                     |
| `areas_for_improvement`             | JSONB     | List of evidenced weaknesses.                    |
| `study_topics`                      | JSONB     | Suggested focus topics (from the 7-day plan).    |
| `recommendation`                    | Text      | Hiring recommendation / grade.                   |
| `created_at`                        | Timestamp | Completion time.                                  |

### `coding_questions`

The coding-round question bank.

| Column               | Type      | Description                                              |
| -------------------- | --------- | ------------------------------------------------------------ |
| `id`                 | Text      | Primary key, e.g. `two_sum`.                                  |
| `skill`              | Text      | Skill tag, e.g. "Arrays & Hashing".                            |
| `role_tags`          | Text[]    | Roles this question is relevant for.                          |
| `difficulty`         | Int       | 1–5.                                                            |
| `title`              | Text      | Question title.                                                |
| `prompt`             | Text      | Full question prompt.                                          |
| `function_name`      | Text      | Function the candidate must implement.                        |
| `function_signature` | Text      | Expected signature.                                             |
| `starter_code`       | Text      | Pre-filled starter code shown in the editor.                   |
| `test_cases`         | JSONB     | List of `{ input_args, expected_output }` used by the sandboxed executor. |
| `expected_concepts`  | Text[]    | Concepts this question is meant to probe.                     |
| `created_at`         | Timestamp | Creation time.                                                |

---

## 🔗 Relationships

```text
auth.users
     │
     ├──► conversations ──► messages
     ├──► conversations ──► scorecards
     ├──► resumes

coding_questions   (standalone bank, not user-scoped)
```

* One user → many interview sessions (`conversations`).
* One interview session → many `messages`, and (on completion) one `scorecards` row.
* One user → many uploaded `resumes` (most recent one is used for personalization/profile).
* `coding_questions` is a shared, backend-managed bank — not scoped to a user.

---

## 🔒 Row Level Security (RLS)

RLS is enabled on every table.

* `conversations`, `messages`, `resumes`, `scorecards` — each has an explicit policy restricting access to `auth.uid() = user_id`, so a user can only ever see their own data if queried with their own credentials.
* `coding_questions` — RLS is enabled with **no policy**, which intentionally locks it to service-role access only (the backend), since it's shared question-bank content with no `user_id` to scope by.

The FastAPI backend authenticates every request via `auth.py` (`Authorization: Bearer <supabase_access_token>`, verified against Supabase Auth) and then reads/writes using the **service-role key**, which bypasses RLS. RLS is still enabled everywhere as defense-in-depth, in case client-side Supabase access is ever introduced.

---

## 📂 Typical Interview Flow

1. User signs up (`/signup`, instant auto-verify) or logs in (`/`).
2. On `/app`, the user picks a target role, optionally uploads a résumé and pastes a job description, and starts an interview.
3. The **planner** builds an interview plan from the résumé + JD + role + candidate memory; a `conversations` row is created.
4. The engine asks Question 1 (Alex or Ricky, tagged with hidden metadata). Coding questions open the in-chat code editor automatically.
5. Each answer is scored by the **evaluator**, the **adaptation engine** decides the next move (harder/easier/pivot/next), and the **anti-repetition engine** filters out near-duplicate questions. Every turn is logged to the Judge Decision Log.
6. All turns are persisted to `messages`; code submissions are executed against test cases via the sandboxed executor.
7. After the target number of questions, the **report generator** produces the final evidence-backed report + 7/14/30-day prep plan, which is saved to `scorecards`.
8. `/dashboard` shows the trend across all past scorecards and recurring memory; `/profile` shows account info, quick stats, and the résumé on file.

---

## ✅ Design Benefits

* Genuinely adaptive difficulty — driven by an evaluation+decision loop, not a static script.
* Deterministic question counting — immune to the LLM losing track mid-conversation.
* Real code execution for the coding round, not just LLM-judged "looks correct."
* Cross-session candidate memory that makes later interviews aware of earlier weaknesses.
* Secure, per-user isolation via Supabase Auth + RLS, with a fast, friction-free sign-up flow.
* Transparent, inspectable agent reasoning via the Judge Decision Log — useful both for candidates and for demoing the engineering to evaluators.

---

## 🔮 Future Additions

* Agentic `evaluate_code()` tool via Gemini function-calling for the coding round (in progress)
* Skill-gap analysis across the candidate's full history
* RAG over role-specific interview banks
* Integrity/behavioral anomaly detection
* Bias evaluation of generated questions
* Career-learning agent that recommends resources based on recurring weak areas
* Video-based interviews
* Company-specific interview modes
* System design deep-dive section

---

## 🎯 Project Goal

RoleReady aims to make interview preparation feel like a real interview, not a quiz. By running an actual planner → evaluator → adaptation loop instead of a fixed question list, it reacts to what the candidate actually knows, digs into weak spots, and produces a report backed by evidence from the transcript — not just a generic score.
