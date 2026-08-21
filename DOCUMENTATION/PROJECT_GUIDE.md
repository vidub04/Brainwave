# RoleReady — Complete Project Guide

This guide explains **everything except the template/HTML files**: the database schema, every backend Python file, every frontend JS file, and how they all connect into one working system.

---

## 1. What This Project Does (in plain words)

RoleReady is a mock interview website. A user logs in, picks a job role (and optionally uploads a resume + pastes a job description), and then has a conversation with an AI interviewer. After every answer, the AI:

1. Grades the answer
2. Decides what to do next (ask a follow-up, get harder, get easier, switch topic, or end the interview)
3. Asks the next question

At the end, it produces a full report card (scores, strengths, weaknesses, evidence, and a study plan), and saves it so the user can track their progress over multiple interviews on a dashboard.

Everything "smart" is done by calling Google's Gemini AI model. Everything is designed to **still work even if the AI call fails** — every AI call has a hardcoded fallback so the app never crashes just because the AI didn't respond well.

---

## 2. Database Schema (Supabase / PostgreSQL)

Supabase is used for two things: **Auth** (login/signup) and a **Postgres database** (all app data). There are 4 tables.

### `conversations`
One row = one interview session.

| Column | Type | Meaning |
|---|---|---|
| `id` | uuid | Interview ID (also used as the primary key everywhere else) |
| `user_id` | uuid | Which logged-in user owns this interview |
| `title` | text | Display name, defaults to "Interview" |
| `target_role` | text | The role chosen for this interview (added later via a migration file) |
| `created_at` | timestamptz | When it was created |

### `messages`
One row = one chat bubble (either the AI's question or the candidate's answer).

| Column | Meaning |
|---|---|
| `conversation_id` | Which interview this message belongs to |
| `role` | `"user"` or `"bot"` |
| `content` | The actual text (bot messages are prefixed with a hidden tag like `[SPEAKER:Alex][DIFFICULTY:rising][CODE:false]` so the frontend can parse who's "speaking" and re-render it later) |

### `resumes`
One row = one uploaded resume.

| Column | Meaning |
|---|---|
| `raw_text` | The plain extracted text from the PDF/DOCX |
| `structured` | JSON version: name, skills, years of experience, past roles, education, summary — produced by the AI |

### `scorecards`
One row = one **completed** interview's final results. This is a separate table from `messages` on purpose — so past performance can be charted and averaged, instead of digging through chat text every time.

| Column | Meaning |
|---|---|
| `technical_knowledge`, `problem_solving`, `core_cs_fundamentals`, `project_knowledge`, `communication`, `confidence`, `leadership`, `behavioral_skills` | 8 category scores (0–10 each) |
| `strengths`, `areas_for_improvement`, `study_topics` | jsonb arrays |
| `recommendation` | e.g. "Hire", "Strong Hire", "Borderline", "Needs Work" |
| `target_role` | Role tested, so the dashboard can group/filter by role |

**Relationships:**
```
auth.users → conversations → messages
auth.users → resumes
auth.users → scorecards → conversations (each scorecard points back to the interview it came from)
```

**Row Level Security (RLS)** is turned on for all 4 tables, with policies like:
```sql
using (auth.uid() = user_id)
```
This means: *if* someone ever queries the database directly from the browser (not through your FastAPI backend), Postgres will only let them see their own rows. In practice the backend uses the **service role key**, which bypasses RLS entirely — RLS here is a safety net for the future, not the main security mechanism today.

---

## 3. Backend Files — What Each One Does

### `auth.py` — Who is this user?

```python
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
```
Creates one shared Supabase client using the **service role key** (full database access, bypasses RLS). This is imported by every other backend file that needs to talk to the database.

```python
async def get_current_user(authorization: str = Header(None)):
```
This is a **FastAPI dependency** — you'll see it as `user=Depends(get_current_user)` on almost every API route in `main.py`. It:
1. Reads the `Authorization: Bearer <token>` header sent by the frontend
2. Asks Supabase "is this token valid, and who does it belong to?" via `supabase.auth.get_user(token)`
3. Returns the user object (`.id`, `.email`) if valid, or throws a `401` error if not

This is the **entire login-protection system** for the API — nothing else checks permissions, it all funnels through this one function.

---

### `resume.py` — Turning a PDF/DOCX into structured data

```python
def extract_text_from_pdf(file_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
```
Uses `pdfplumber` to pull raw text out of a PDF, page by page.

```python
def extract_text_from_docx(file_bytes: bytes) -> str:
    document = docx.Document(BytesIO(file_bytes))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())
```
Same idea but for Word docs, using `python-docx`.

```python
def structure_resume(llm_or_gemini_client, raw_text: str) -> dict:
```
This is the important one. It sends the raw resume text to the AI with a very specific instruction: *"return ONLY JSON matching this exact shape"* (name, current_role, years_experience, skills, past_roles, education, summary). If the AI response isn't valid JSON or the call fails, it falls back to a `default_structure` dict built directly from the raw text — so the app never breaks just because resume parsing failed.

Notice this function is written to work with **two different kinds of clients** (your custom `LLMClient` or a raw `google.genai` client) — it checks `hasattr(llm_or_gemini_client, "generate_json")` to decide which path to take.

---

### `main.py` — The FastAPI app / the "front door"

This file wires the whole backend together. Key parts:

**Startup:**
```python
orchestrator = get_orchestrator(supabase_client=supabase)
```
One global `InterviewOrchestrator` instance is created when the server starts, and reused across all requests (not recreated per-request).

**Auth endpoints:**
```python
@app.post("/api/auth/signup")
```
Uses `supabase.auth.admin.create_user(..., email_confirm=True)` — this **auto-confirms** the email so users don't need to click a verification link (good for demos, worth reconsidering for production).

```python
@app.post("/api/auth/demo-login")
```
Returns a hardcoded demo email/password pair (creating the account if it doesn't exist yet) — a "1-click try it out" button.

**The core interview endpoints** (this is the main flow):

```python
@app.post("/api/interview/create")
```
Calls `orchestrator.create_interview(...)`, then separately inserts a row into `conversations` in Supabase. Note: the interview *state* lives in the orchestrator (memory + SQLite), while Supabase's `conversations` table is more of a lightweight index/listing.

```python
@app.post("/api/interview/{interview_id}/start")
```
Calls `orchestrator.start_interview(...)` to get Question 1, then saves it to `messages` with a hidden metadata tag:
```python
meta_tag = f"[SPEAKER:{q1.speaker}][DIFFICULTY:...][CODE:{'true' if q1.requires_code else 'false'}]"
```

```python
@app.post("/api/interview/{interview_id}/answer")
```
The busiest endpoint. It:
1. Saves the candidate's raw answer to `messages`
2. Calls `orchestrator.process_candidate_answer(...)` — this runs the entire evaluate → decide → generate-next-question pipeline (explained in the Engine section below)
3. If the interview just finished, it saves both a closing message **and** a new row in `scorecards` — notice the score mapping is a bit lossy:
```python
"technical_knowledge": int(min(10, max(1, rep.overall_score / 10.0))),
```
This converts the 0–100 report score down to roughly a 0–10 scale for that one column, while other columns pull from `rep.category_scores` with fallback defaults like `communication: 8.0` if the AI didn't return a matching category.

**Legacy/compatibility routes** (`/app/generate`, `/app/conversations`, `/app/history/{id}`, `/app/progress`, `/app/resume/upload`) exist mostly for the dashboard and for older frontend code paths that talk to the orchestrator a slightly different way.

```python
@app.get("/app/progress")
```
This is what powers the dashboard: fetches all `scorecards` for the user, **plus** calls `orchestrator.memory_manager.get_candidate_memory(user_id=...)` to compute the "what we remember about you" trend summary, and returns both together.

---

## 4. The `engine/` Folder — The AI Pipeline

Think of this folder as a small team of specialist AI "agents," each with one job, coordinated by a manager (`orchestrator.py`).

### `models.py` — the shared vocabulary

Every other file imports its data shapes from here. The most important one is `CandidateState`, which holds the **entire live state of one interview**: current difficulty, current stage, skill scores, asked questions, full turn-by-turn history, decision logs, etc. Nothing about an interview exists outside this object.

```python
class AdaptationAction(str, Enum):
    FOLLOW_UP = "FOLLOW_UP"
    INCREASE_DIFFICULTY = "INCREASE_DIFFICULTY"
    ...
    END_INTERVIEW = "END_INTERVIEW"
```
This enum is the **vocabulary of decisions** the adaptive engine is allowed to make — every "what happens next" decision boils down to one of these values.

### `llm_client.py` — the one place that talks to Gemini

```python
ACTIVE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.6-flash",
]
```
A prioritized list of models to try. Every AI call loops through these models (and retries), so if one model is rate-limited (`429`) it just moves to the next.

```python
def clean_json_string(self, raw_text: str) -> str:
```
AI models often wrap JSON in ```` ```json ... ``` ```` fences or add extra commentary. This function strips that out and grabs just the `{...}` or `[...]` portion before parsing — this single function is what keeps the whole app from crashing on "almost valid" JSON.

```python
def generate_json(self, prompt, system_instruction=None, default_data=None, retries=2):
```
This is called by nearly every other engine file. If the API key is missing, or every retry fails, it just returns `default_data` — **the app degrades gracefully to rule-based fallbacks instead of crashing.**

### `planner.py` — builds the game plan before the interview starts

```python
def create_plan(self, role, job_description, resume_text, resume_structured, duration_minutes, interview_type, candidate_memory):
```
Combines the role, JD, resume, and any memory of past interviews into one prompt, and asks the AI to return: which skills to test (with priority weights 0–1), how many questions, starting difficulty, and how time should be split across stages (Fundamentals / Applied / Problem Solving / System Design / Behavioral).

```python
def _get_default_skills_for_role(self, role: str):
```
A hardcoded fallback skill list per role category (ML, frontend, backend, data science, generic) — used if the AI call fails, so the interview can still start with something sensible.

Notice how candidate memory changes the plan **without needing the AI at all**, as a safety-net adjustment:
```python
if candidate_memory.avg_overall_score >= 7.5 or candidate_memory.trend_direction == "improving":
    fallback_difficulty = 3
```

### `question_generator.py` — writes the actual next question

```python
def generate_question(self, state, decision, max_regeneration_attempts=3):
```
Takes the decision from the adaptation engine (target skill, target difficulty, action) and asks the AI to write one specific question. It picks a persona:
```python
speaker = "Ricky" if is_behavioral_stage else "Alex"
```
Then it checks the question against `anti_repetition.py` — if it's too similar to something already asked, it **regenerates up to 3 times** before giving up and returning a generic fallback question.

### `anti_repetition.py` — pure math, no AI

Uses **Jaccard similarity** (word overlap) on both single words and word-pairs (bigrams) to catch questions that are reworded duplicates:
```python
jaccard_uni = len(set1_uni & set2_uni) / max(1, len(set1_uni | set2_uni))
```
Bigram overlap is weighted higher (60%) than single-word overlap (40%) because matching *phrases* is a stronger signal of "this is basically the same question" than matching individual words.

### `evaluator.py` — grades one answer

```python
def evaluate(self, question, candidate_answer, role, code_submission=None):
```
Sends the question + answer to the AI and asks for 5 separate scores (technical, reasoning, relevance, communication, completeness) plus an overall score, missing concepts, strengths, weaknesses, and whether a follow-up is needed.

```python
if len(trimmed) < 10 and not code_submission:
    return EvaluationResult(technical_score=1.0, ..., overall_score=1.4, ...)
```
Short-circuits with an automatic low score if the answer is basically empty — no need to waste an AI call on "idk."

### `adaptation_engine.py` — the "brain" that decides what happens next

This is the most important file for the "adaptive" part of "adaptive interview engine." It works in **two layers**:

**Layer 1 — hardcoded guardrail rules** (always computed first, cannot be skipped):
```python
if latest_eval.needs_followup and missing and len(missing) > 0 and latest_eval.relevance_score >= 4.0:
    guardrail_action = AdaptationAction.FOLLOW_UP
elif overall >= 8.0:
    guardrail_action = AdaptationAction.INCREASE_DIFFICULTY
elif overall <= 5.0:
    guardrail_action = AdaptationAction.DECREASE_DIFFICULTY / PROBE_WEAKNESS
else:
    guardrail_action = AdaptationAction.SWITCH_SKILL
```

**Layer 2 — the AI is asked to refine that guardrail decision**, but it's kept on a short leash:
```python
diff_step = max(-1, min(1, new_diff - current_diff))
final_diff = max(1, min(5, current_diff + diff_step))
```
No matter what the AI suggests, difficulty can only move **one level at a time**. This is the key design decision in this whole file: the AI chooses the *flavor* of the decision, but hard Python code enforces the *safety bounds*.

```python
def calculate_skill_scores_priority(self, state):
```
A scoring formula that decides which skill to test next: skills scored low get a "weakness bonus," skills never tested get a "coverage bonus," and skills already mastered (≥8.5) get penalized so the interview doesn't keep asking about the same thing the candidate is already great at.

### `state_manager.py` — keeps everything saved

```python
class SkillTracker:
    @staticmethod
    def update_skill_scores(state, tested_skill, evaluation, alpha: float = 0.65):
        new_score = round(alpha * turn_score + (1.0 - alpha) * prev, 1)
```
This is an **exponential moving average**: each new answer counts for 65% of the updated skill score, the previous score counts for 35%. This means recent answers matter more than old ones, but one lucky/unlucky answer doesn't swing the score wildly.

```python
class CandidateStateManager:
    def __init__(self, supabase_client=None):
        self._memory_store: Dict[str, CandidateState] = {}
        self._init_sqlite()
```
State is saved in **three places at once** on every turn: an in-memory Python dict (fastest, but lost on server restart), a local SQLite file (`interviews_cache.db`, survives restarts), and mirrored to Supabase (only the `target_role` field, for the conversations list). `get_state()` checks memory first, then falls back to SQLite if the server restarted.

### `report_generator.py` — the final scorecard

```python
def generate_report(self, state: CandidateState) -> InterviewReport:
```
Builds a full text "trajectory" of every question/answer/score in the interview, sends the whole thing to the AI, and asks for: overall score, grade, a summary, a skill-by-skill percentage breakdown, evidence-backed weaknesses (must cite the actual question+answer that revealed the gap), and a 7/14/30-day study plan.

```python
scaled_score = round(min(100.0, max(0.0, avg_overall * 10.0)), 1)
```
The fallback overall score is calculated deterministically from the actual average of all per-turn scores (not just AI-invented) — so even if the AI call totally fails, the score is still mathematically grounded in real performance.

### `candidate_memory.py` — remembers the candidate across interviews

```python
def get_candidate_memory(self, user_id, current_role=None) -> Optional[CandidateMemory]:
```
Pulls the last 5 `scorecards` rows for this user, averages the 8 category scores, and classifies skills as "recurring weak" (<6.0 average) or "recurring strong" (≥7.5 average).

```python
if second_half_avg - first_half_avg >= 0.5:
    trend_direction = "improving"
elif first_half_avg - second_half_avg >= 0.5:
    trend_direction = "declining"
```
Trend is computed by comparing the first half vs. second half of past scores — simple but effective. This whole object then feeds back into `planner.py` (to raise priority on weak skills) and `report_generator.py` (to comment on growth over time).

### `orchestrator.py` — the manager that calls everyone else in order

```python
class InterviewOrchestrator:
    def __init__(self, supabase_client=None, llm_client=None):
        self.planner = InterviewPlanner(self.llm)
        self.evaluator = EvaluationAgent(self.llm)
        self.decision_engine = AdaptiveDecisionEngine(self.llm)
        self.question_generator = InterviewerAgent(self.llm, self.anti_repetition)
        self.state_manager = CandidateStateManager(supabase_client)
        self.report_generator = InterviewReportGenerator(self.llm)
        self.memory_manager = CandidateMemoryManager(supabase_client)
```
All the specialist agents get created once here, sharing the **same** `llm_client` instance (so they all use the same Gemini connection/retry logic).

```python
def process_candidate_answer(self, interview_id, candidate_answer, code_submission=None):
```
This is the exact 5-step pipeline described in the workflow section below — evaluate → decide → check if done → generate next question → save state.

---

## 5. Frontend JS Files

### `static/auth.js` — Supabase login/session handling

```javascript
async function create_client() {
    const res = await fetch("/config");
    const data = await res.json();
    supabaseClient = window.supabase.createClient(data.supabase_url, data.supabase_anon_key);
}
const supabaseReady = create_client();
```
Instead of hardcoding Supabase keys directly in JS (which would need a build step to keep secret-ish config out of source control), it fetches them from the backend's `/config` route at page load. `supabaseReady` is a promise that other scripts `await` before touching `supabaseClient`.

```javascript
async function requireSession() {
    const { data: { session } } = await supabaseClient.auth.getSession();
    if (!session) { window.location.href = "/"; return null; }
    return session.access_token;
}
```
This runs at the top of every protected page. If there's no valid session, it bounces the user back to the login page. Otherwise it returns the access token, which every subsequent `fetch()` call attaches as `Authorization: Bearer <token>`.

### `static/script.js` — the actual interview UI logic

This is the biggest frontend file. Key functions:

```javascript
async function startAdaptiveInterviewSession() {
    const createRes = await fetch("/api/interview/create", { ... });
    const createData = await createRes.json();
    interviewId = createData.interview_id;

    const startRes = await fetch(`/api/interview/${interviewId}/start`, { method: "POST", ... });
```
Two sequential API calls: first create the plan, then start (get question 1). `interviewId` is stored as a global JS variable and reused for every subsequent call in the session.

```javascript
async function sendPrompt() {
    ...
    appendUserMessage(fullUserDisplay);
    showEvalLoading(true);
    const res = await fetch(`/api/interview/${interviewId}/answer`, { method: "POST", body: JSON.stringify({ answer, code }) });
    ...
```
This is the main "submit answer" loop. Note it appends the user's message to the chat **immediately** (optimistic UI), then shows a rotating loading message (`showEvalLoading`) while waiting for the backend's evaluate→decide→next-question pipeline to finish.

```javascript
function showEvalLoading(show) {
    const steps = ["Analyzing candidate answer...", "Evaluating technical depth...", ...];
    window._evalInterval = setInterval(() => { ... }, 1200);
}
```
This is purely cosmetic — it cycles through fake "status" text every 1.2 seconds to make the wait feel more transparent, even though the backend is really just doing one sequential pipeline, not literally reporting these steps in real time.

```javascript
function setupSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    speechRecognizer = new SpeechRec();
    speechRecognizer.continuous = true;
    speechRecognizer.interimResults = true;
```
Uses the **browser's built-in** Web Speech API for voice-to-text (no server round-trip, no AI transcription cost) — meaning it only works in Chromium-based browsers that support it.

```javascript
function speakText(text, speaker) {
    if (!voiceOutputEnabled || !window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(clean);
    if (speaker === "Ricky") { utterance.pitch = 1.25; utterance.rate = 1.05; }
    else { utterance.pitch = 0.9; utterance.rate = 0.98; }
```
Also entirely client-side (browser Text-to-Speech), giving the two interviewer personas slightly different pitch/rate so they sound distinct.

```javascript
function appendDecisionLogEntry(turnData) {
    list.insertAdjacentHTML("afterbegin", entryHtml);
```
Every turn's decision (scores, action taken, reasoning) gets pushed into the "Judge Decision Log" drawer — `insertAdjacentHTML("afterbegin", ...)` means newest entries appear at the **top** of the list.

```javascript
async function resumePastSession(id) { ... }
async function loadLegacyHistory(id) {
    const text = m.content.replace(/^\[SPEAKER:[^\]]+\]\[DIFFICULTY:[^\]]+\](?:\[CODE:[^\]]+\])?\s*/, "");
```
When reloading an old conversation, this regex strips off the hidden `[SPEAKER:...][DIFFICULTY:...][CODE:...]` metadata tag that was saved into the raw `messages.content` string, leaving just the readable question text.

### `static/dashboard.js` — the analytics page

```javascript
function overallScore(sc) {
    const keys = Object.keys(CATEGORY_LABELS);
    const values = keys.map(k => Number(sc[k]) || 0);
    return values.reduce((a, b) => a + b, 0) / keys.length;
}
```
Every scorecard row has 8 separate category columns; this just averages them into one "overall" number for display, computed client-side (the raw scorecard rows are sent as-is from `/app/progress`, not pre-averaged by the backend).

```javascript
function renderChart(scorecards) {
    if (scorecards.length < 2) return;
    ...
    Object.keys(CATEGORY_LABELS).forEach(key => {
        const points = scorecards.map((sc, i) => { ... });
        svgContent += `<polyline points="${points.join(" ")}" ... />`;
    });
    svg.innerHTML = svgContent;
```
The trend chart is **hand-built raw SVG** — no charting library. It draws one `<polyline>` per skill category, manually calculating x/y pixel coordinates from the 0–10 score scale. Needs at least 2 past interviews to draw a meaningful line, hence the early return.

```javascript
function renderMemoryPanel(memory) {
    if (!memory || !memory.total_past_interviews) return;
```
Renders the "What We Remember About You" card — but only if `candidate_memory` came back non-null from the backend, which only happens for a user with at least one *completed* past interview.

---

## 6. Complete Workflow

### A. Sign up / Log in
1. User visits `/` → `login.html` loads, `auth.js` initializes the Supabase client via `/config`.
2. `signUp()` or `signIn()` calls Supabase Auth directly from the browser (not through the FastAPI backend at all — this is the one part of the app that talks to Supabase client-side).
3. On success, redirect to `/app`. Every page after this calls `requireSession()` first and stores the access token.

### B. Starting an interview
1. User fills out the landing form (role, duration, focus track, optional resume, optional JD).
2. **If a resume is uploaded** → `POST /app/resume/upload` → `resume.py` extracts text → `structure_resume()` asks the AI to structure it → saved to `resumes` table → structured data + skills pills shown in the UI.
3. User clicks "Begin Adaptive Interview" → `POST /api/interview/create`:
   - `orchestrator.create_interview()` → pulls `candidate_memory` (past scorecards, if any) → `planner.create_plan()` builds the `InterviewPlan` → `state_manager.create_initial_state()` builds and saves the `CandidateState`.
   - A row is inserted into `conversations`.
4. `POST /api/interview/{id}/start`:
   - `decision_engine.decide_next_action(state, latest_eval=None)` returns a "start with the top-priority skill at baseline difficulty" directive.
   - `question_generator.generate_question()` produces Question 1.
   - Saved to `messages`, shown in the chat UI.

### C. Every answer submitted (the core loop)
`POST /api/interview/{id}/answer` → `orchestrator.process_candidate_answer()`:

```
1. EVALUATE   → evaluator.evaluate(question, answer) → scores + missing concepts
2. DECIDE     → adaptation_engine.decide_next_action(state, evaluation)
                 → guardrail rule picks a base action
                 → AI refines it within ±1 difficulty
3. CHECK END  → if action == END_INTERVIEW or no questions left:
                 → report_generator.generate_report(state)
                 → save scorecard row → return report
4. NEXT Q     → question_generator.generate_question(state, decision)
                 → checked against anti_repetition, regenerated if too similar
5. SAVE STATE → state_manager.update_after_turn(...)
                 → skill scores updated (exponential moving average)
                 → turn history + decision log appended
                 → saved to memory + SQLite + Supabase
```
Every step of this returns data that flows straight back to `script.js`, which renders the next question, updates the difficulty/stage badges, and logs the decision reasoning into the drawer.

### D. Ending the interview
When `questions_remaining` hits 0 (or the AI decides `END_INTERVIEW` early), the report is generated, `main.py` writes it into `scorecards`, and the frontend shows the final report modal with skill bars, evidence cards, and the 7/14/30-day study plan.

### E. Viewing the dashboard
`GET /app/progress` → returns all past `scorecards` + `candidate_memory` (recomputed live from those same scorecards) → `dashboard.js` renders the memory panel, summary stats, hand-drawn SVG trend chart, and the session history table.

---

## 7. One-Sentence Summary of Every File

| File | One-line summary |
|---|---|
| `auth.py` | Verifies who's making the request via Supabase Auth tokens |
| `resume.py` | Extracts text from PDF/DOCX and turns it into structured JSON via AI |
| `main.py` | The FastAPI app — all HTTP routes live here |
| `engine/models.py` | All the shared data shapes (Pydantic models) |
| `engine/llm_client.py` | The one place that calls Gemini, with retries + JSON cleanup |
| `engine/planner.py` | Builds the interview plan before it starts |
| `engine/question_generator.py` | Writes the next question text |
| `engine/anti_repetition.py` | Math-only duplicate question detector |
| `engine/evaluator.py` | Grades one candidate answer |
| `engine/adaptation_engine.py` | Decides what happens next (the "adaptive" brain) |
| `engine/state_manager.py` | Saves/loads interview state (memory + SQLite + Supabase) |
| `engine/report_generator.py` | Builds the final scorecard + study plan |
| `engine/candidate_memory.py` | Aggregates a user's past scorecards into a memory profile |
| `engine/orchestrator.py` | Runs all the above agents in the right order |
| `static/auth.js` | Handles Supabase login/session on the frontend |
| `static/script.js` | The interview chat UI, voice I/O, and API calls |
| `static/dashboard.js` | Renders the analytics/progress dashboard |
