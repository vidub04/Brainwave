# RoleReady

RoleReady is an AI-powered mock interview application that simulates realistic technical and HR interviews through two unique AI interviewer personalities.

Whether you're preparing for internships, placements, or software engineering roles, the application conducts an interactive interview by asking role-specific questions, adapting to your responses, and personalizing questions using your resume.

---

## ✨ Features

* 🤖 **Dual AI Interviewers**

  * **Alex** – Senior Software Engineer who focuses on technical assessment.
  * **Ricky** – HR Manager who evaluates communication, personality, and behavioral skills.

* 🔐 **User Accounts (Supabase Auth)**

  * Email/password sign-up and login.
  * Each user's interviews, messages, and resumes are private to their account.

* 💬 **Conversational Interview Experience**

  * Maintains conversation context throughout the interview.
  * Asks one question at a time.
  * Generates follow-up questions based on previous answers.
  * Interview wraps up automatically after ~10 candidate answers.
  * Increasing difficulty on basis of performance
  * Weak topic suggestion

* 🎯 **Role-Based Interviewing**

  * Candidate selects a target role at the start of the interview.
  * Tailors both Alex's technical questions and Ricky's behavioral questions to that role.
  * The selected role is remembered for the rest of that conversation.
  * Coding section

* 📄 **Resume Upload & Personalization**

  * Upload a `.pdf` or `.docx` resume.
  * Text is extracted and structured (skills, education, projects, experience) using Gemini.
  * The AI blends resume details into interview questions.

* 💻 **Technical Assessment**

  * Data Structures & Algorithms
  * Object-Oriented Programming
  * DBMS
  * Operating Systems
  * Computer Networks
  * AI/ML concepts
  * Resume Projects
  * Problem Solving

* 👥 **HR Assessment**

  * Self Introduction
  * Behavioral Questions
  * Leadership
  * Teamwork
  * Conflict Resolution
  * Workplace Scenarios
  * Career Goals

* 📜 **Conversation History**

  * Past interview sessions are listed and can be resumed at any time.

* 🖥️ **Chatbot-Style Interface**

  * Clean conversational UI inspired by modern AI chat applications.
    

---

## 🛠️ Tech Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** FastAPI (Python)
* **AI Model:** Google Gemini API (`google-genai`)
* **Auth & Database:** Supabase (PostgreSQL + Auth)
* **Templating:** Jinja2
* **Resume Parsing:** `pdfplumber` (PDF), `python-docx` (DOCX)

---

## 📁 Project Structure

```text
Brainwave-main/
├── main.py                        # FastAPI app: pages, chat, history, resume upload
├── auth.py                        # Supabase auth dependency + service-role client
├── resume.py                      # Resume text extraction & structuring
├── requirements.txt
├── supabase_schema.sql            # Initial database schema (tables, indexes, RLS)
├── add_target_role_migration.sql  # Adds `target_role` column to conversations
├── feature_addition_guide.md      # Notes on extending the app with new features
├── templates/
│   ├── login.html                 # Login / sign-up page
│   └── index.html                 # Main chat interface
└── static/
    ├── style.css
    ├── script.js                  # Chat UI, role selector, resume upload logic
    └── auth.js                    # Supabase auth (sign up/in/out, session handling)
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

In the Supabase SQL Editor, run:

1. `supabase_schema.sql` — creates the `conversations`, `messages`, and `resumes` tables, indexes, and Row Level Security policies.
2. `add_target_role_migration.sql` — adds the `target_role` column used by the role-selector feature.

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

Visit `http://localhost:8000` to log in or sign up, then you'll be redirected to `/app` to start an interview.

---

# 🗄️ Database Schema

RoleReady uses **Supabase (PostgreSQL)** to persist user interviews, chat history, and resume information. The database is designed so each user has isolated data while allowing conversations to be resumed and personalized.

---

## 📋 Tables

### 1. `conversations`

Stores information about each interview session.

| Column        | Type      | Description                                                            |
| ------------- | --------- | ------------------------------------------------------------------------ |
| `id`          | UUID      | Unique identifier for each interview session. Generated automatically. |
| `user_id`     | UUID      | References the authenticated user who owns the interview.              |
| `title`       | Text      | Title of the conversation (defaults to **Interview**).                 |
| `target_role` | Text      | The role the candidate selected for this interview (e.g. "Backend Engineer"). |
| `created_at`  | Timestamp | Time when the interview was created.                                   |

#### Purpose

* Creates a new interview session.
* Groups all chat messages belonging to one interview.
* Remembers the selected target role so it stays consistent across turns.
* Allows users to have multiple interview sessions.

---

### 2. `messages`

Stores every message exchanged during an interview.

| Column            | Type      | Description                                                  |
| ----------------- | --------- | -------------------------------------------------------------- |
| `id`              | UUID      | Unique message identifier.                                   |
| `conversation_id` | UUID      | Links the message to a conversation.                         |
| `user_id`         | UUID      | Owner of the message.                                        |
| `role`            | Text      | Indicates whether the sender is the **user** or the **bot**. |
| `content`         | Text      | Message content.                                             |
| `created_at`      | Timestamp | Time the message was sent.                                   |

#### Purpose

* Preserves complete interview history.
* Enables the AI to reconstruct previous context.
* Supports resuming interrupted interviews.

---

### 3. `resumes`

Stores uploaded resumes and extracted information.

| Column       | Type      | Description                                                             |
| ------------ | --------- | --------------------------------------------------------------------------- |
| `id`         | UUID      | Resume identifier.                                                      |
| `user_id`    | UUID      | Owner of the resume.                                                    |
| `filename`   | Text      | Original uploaded filename.                                             |
| `raw_text`   | Text      | Complete extracted text from the resume.                                |
| `structured` | JSONB     | Parsed resume data such as skills, education, projects, and experience. |
| `created_at` | Timestamp | Upload timestamp.                                                       |

#### Purpose

The AI uses this information to generate personalized interview questions based on the candidate's background.

Example structure:

```json
{
  "name": "Jane Doe",
  "skills": ["Python", "FastAPI", "Machine Learning"],
  "education": "...",
  "projects": [
    {
      "title": "RoleReady",
      "technologies": ["FastAPI", "Gemini", "Supabase"]
    }
  ]
}
```

---

# 🔗 Relationships

```text
auth.users
     │
     │ 1
     ▼
conversations
     │
     │ 1
     ▼
messages

auth.users
     │
     ▼
resumes
```

* One user can have multiple interview sessions.
* One interview session contains multiple chat messages.
* One user can upload one or more resumes.

---

# ⚡ Database Indexes

Indexes improve query performance by allowing PostgreSQL to locate records efficiently.

### `idx_conversations_user`

Optimizes retrieval of all interview sessions belonging to a user.

### `idx_messages_conversation`

Speeds up loading the chat history for a conversation.

### `idx_messages_user`

Improves queries involving all messages created by a user.

### `idx_resumes_user`

Optimizes fetching the latest uploaded resume.

---

# 🔒 Row Level Security (RLS)

Row Level Security is enabled on every table.

This ensures users can only access their own data when queries are made using authenticated user credentials.

Policies enforce:

* Users can only view their own interviews.
* Users can only modify their own messages.
* Users can only access their own resumes.

Although the FastAPI backend typically uses the **Supabase Service Role Key**, which bypasses RLS, enabling these policies provides an additional layer of protection if client-side database access is introduced in the future.

---

# 📂 Typical Interview Flow

1. A user logs in or signs up via `/` (Supabase Auth).
2. On `/app`, the user picks a target role and starts a new interview.
3. A record is created in the **conversations** table, storing the `target_role`.
4. Every user response and AI reply is stored in **messages**.
5. If the user uploads a resume, it's parsed and stored in **resumes**.
6. The AI combines the resume, target role, and conversation history to generate personalized interview questions from both Alex and Ricky.
7. After about 10 candidate answers, the AI wraps up the interview.
8. When the user returns later, past interviews are listed and can be resumed from the saved conversation history.

---

# ✅ Design Benefits

* Persistent interview history
* Secure, per-user authentication via Supabase Auth
* Resume upload and automatic resume-aware interviews
* Role-aware questioning that stays consistent across a session
* Efficient retrieval through indexing
* Secure user isolation with Row Level Security
* Scalable architecture supporting multiple interview sessions per user

---

## 🔮 Future Additions

* Voice-based interview with speech-to-text
* AI voice responses using text-to-speech
* Support for more roles, domains, and engineering branches
* Company-specific interview modes
* Communication & English analysis
* Video-based interviews
* AI coach
* Feedback with improved answers
* System design section
* Recommended questions & resources
* Generate study plan

---

## 🎯 Project Goal

RoleReady aims to make interview preparation more interactive and personalized by simulating realistic conversations rather than presenting a fixed list of questions. The application adapts to the candidate's responses, encouraging critical thinking while helping users improve both technical knowledge and communication skills.
