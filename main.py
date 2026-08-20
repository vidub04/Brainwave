import os
import re
import json
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # load .env BEFORE importing auth

from auth import get_current_user, supabase
from resume import extract_raw_text, structure_resume
from engine import (
    get_orchestrator,
    CreateInterviewRequest,
    SubmitAnswerRequest,
    QuestionItem,
    CandidateState
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adaptive_interview")

app = FastAPI(title="RoleReady Adaptive Interview Engine", version="2.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize the global adaptive orchestrator
orchestrator = get_orchestrator(supabase_client=supabase)


# ============================================================
# Page Routes
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def login_window(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/app", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/config")
async def get_config():
    return {
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY")
    }


# ============================================================
# Authentication API Endpoints (Auto-confirmed / Rate-limit Proof)
# ============================================================

class AuthRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/signup")
async def api_auth_signup(data: AuthRequest):
    """
    Creates and auto-confirms user via Supabase admin service to bypass SMTP rate limits.
    """
    email = data.email.strip().lower()
    password = data.password.strip()

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if not supabase:
        raise HTTPException(status_code=500, detail="Authentication service unavailable.")

    try:
        res = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        return {
            "status": "ok",
            "message": "Account created and verified! Logging you in...",
            "user_id": res.user.id
        }
    except Exception as e:
        err_msg = str(e)
        if "already registered" in err_msg.lower() or "unique" in err_msg.lower():
            return {
                "status": "exists",
                "message": "This email is already registered. Logging you in..."
            }
        logger.warning(f"Error during admin user creation: {e}")
        raise HTTPException(status_code=400, detail=err_msg)


@app.post("/api/auth/demo-login")
async def api_auth_demo():
    """
    Provides instant 1-click candidate demo credentials for evaluations and hackathon judging.
    """
    demo_email = "candidate_demo@roleready.ai"
    demo_password = "RoleReadyDemo2026!"

    if supabase:
        try:
            # Ensure demo user exists
            supabase.auth.admin.create_user({
                "email": demo_email,
                "password": demo_password,
                "email_confirm": True
            })
        except Exception:
            pass

    return {
        "email": demo_email,
        "password": demo_password
    }


# ============================================================
# Production Adaptive Interview Engine API Endpoints
# ============================================================

@app.post("/api/interview/create")
async def api_create_interview(
    data: CreateInterviewRequest,
    user=Depends(get_current_user)
):
    """
    Analyzes resume + target JD to create a customized interview plan and candidate state.
    """
    try:
        user_id = getattr(user, "id", None)
        state = orchestrator.create_interview(
            role=data.role,
            job_description=data.job_description,
            resume_text=data.resume_text,
            resume_structured=data.resume_structured,
            duration_minutes=data.duration_minutes,
            interview_type=data.interview_type,
            user_id=user_id
        )

        # Also register in Supabase conversations if active
        if supabase and user_id:
            try:
                supabase.table("conversations").insert({
                    "id": state.interview_id,
                    "user_id": user_id,
                    "title": f"{data.role} ({data.interview_type})",
                    "target_role": data.role
                }).execute()
            except Exception as e:
                logger.warning(f"Supabase conversation insert skipped: {e}")

        return {
            "interview_id": state.interview_id,
            "role": state.role,
            "interview_plan": state.interview_plan,
            "total_questions": state.interview_plan.total_target_questions if state.interview_plan else 8,
            "target_duration_minutes": state.target_duration_minutes,
            "candidate_memory": state.candidate_memory
        }
    except Exception as e:
        logger.error(f"Error in api_create_interview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/{interview_id}/start")
async def api_start_interview(
    interview_id: str,
    user=Depends(get_current_user)
):
    """
    Initiates interview Question 1 tailored to the candidate's initial baseline.
    """
    try:
        start_payload = orchestrator.start_interview(interview_id)
        
        # Save Question 1 to Supabase messages
        if supabase:
            try:
                user_id = getattr(user, "id", None)
                q1 = start_payload["question"]
                meta_tag = f"[SPEAKER:{q1.speaker}][DIFFICULTY:{'steady' if q1.difficulty == 2 else 'rising'}][CODE:{'true' if q1.requires_code else 'false'}]"
                supabase.table("messages").insert({
                    "conversation_id": interview_id,
                    "user_id": user_id,
                    "role": "bot",
                    "content": f"{meta_tag} {q1.question}"
                }).execute()
            except Exception:
                pass

        return start_payload
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in api_start_interview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/{interview_id}/answer")
async def api_submit_answer(
    interview_id: str,
    data: SubmitAnswerRequest,
    user=Depends(get_current_user)
):
    """
    Evaluates candidate response, runs the Adaptive Decision Engine,
    updates candidate state & skill graph, and produces the next question or final report.
    """
    try:
        user_id = getattr(user, "id", None)

        # Save user answer to Supabase
        if supabase and user_id:
            try:
                user_msg_content = data.answer
                if data.code:
                    user_msg_content += f"\n```\n{data.code}\n```"
                supabase.table("messages").insert({
                    "conversation_id": interview_id,
                    "user_id": user_id,
                    "role": "user",
                    "content": user_msg_content
                }).execute()
            except Exception:
                pass

        result = orchestrator.process_candidate_answer(
            interview_id=interview_id,
            candidate_answer=data.answer,
            code_submission=data.code
        )

        # Save next bot question or report to Supabase
        if supabase and user_id:
            try:
                if result.get("is_completed") and result.get("report"):
                    rep = result["report"]
                    # Record final message
                    supabase.table("messages").insert({
                        "conversation_id": interview_id,
                        "user_id": user_id,
                        "role": "bot",
                        "content": f"[SPEAKER:Alex][DIFFICULTY:final][CODE:false] That concludes our interview! Here is your final evaluation summary.\n\n```json\n{rep.model_dump_json()}\n```"
                    }).execute()
                    
                    # Record scorecard
                    supabase.table("scorecards").insert({
                        "user_id": user_id,
                        "conversation_id": interview_id,
                        "target_role": rep.candidate_role,
                        "technical_knowledge": int(min(10, max(1, rep.overall_score / 10.0))),
                        "problem_solving": int(rep.category_scores.get("Problem Solving", 7.0)),
                        "core_cs_fundamentals": int(rep.category_scores.get("Technical Fundamentals", 7.0)),
                        "project_knowledge": int(rep.category_scores.get("Applied Domain Knowledge", 7.0)),
                        "communication": int(rep.category_scores.get("Communication", 8.0)),
                        "confidence": 8,
                        "leadership": 8,
                        "behavioral_skills": int(rep.category_scores.get("Behavioral", 7.0)),
                        "strengths": rep.strengths,
                        "areas_for_improvement": rep.weaknesses,
                        "study_topics": rep.preparation_plan.day_7_focus,
                        "recommendation": rep.score_grade
                    }).execute()
                elif result.get("next_question"):
                    nq = result["next_question"]
                    diff_tag = "rising" if nq.difficulty >= 4 else ("easing" if nq.difficulty <= 2 else "steady")
                    meta_tag = f"[SPEAKER:{nq.speaker}][DIFFICULTY:{diff_tag}][CODE:{'true' if nq.requires_code else 'false'}]"
                    supabase.table("messages").insert({
                        "conversation_id": interview_id,
                        "user_id": user_id,
                        "role": "bot",
                        "content": f"{meta_tag} {nq.question}"
                    }).execute()
            except Exception as e:
                logger.warning(f"Error persisting to Supabase messages/scorecards: {e}")

        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in api_submit_answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interview/{interview_id}/state")
async def api_get_interview_state(
    interview_id: str,
    user=Depends(get_current_user)
):
    """Returns the complete persistent candidate state for live sync / refresh."""
    state = orchestrator.get_state(interview_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview not found")
    return state


@app.get("/api/interview/{interview_id}/decision-log")
async def api_get_decision_log(
    interview_id: str,
    user=Depends(get_current_user)
):
    """Returns real-time developer / hackathon judge agent decision trajectory."""
    logs = orchestrator.get_decision_logs(interview_id)
    return {
        "interview_id": interview_id,
        "logs": logs
    }


@app.get("/api/interview/{interview_id}/report")
async def api_get_interview_report(
    interview_id: str,
    user=Depends(get_current_user)
):
    """Returns the evidence-backed final interview report with 7/14/30 day study roadmap."""
    try:
        report = orchestrator.get_report(interview_id)
        return report
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in api_get_interview_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/{interview_id}/resume")
async def api_resume_interview(
    interview_id: str,
    user=Depends(get_current_user)
):
    """Resumes an in-progress interview session."""
    state = orchestrator.get_state(interview_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview not found")
    return {
        "interview_id": state.interview_id,
        "role": state.role,
        "current_difficulty": state.current_difficulty,
        "current_stage": state.current_stage,
        "questions_asked": state.questions_asked,
        "questions_remaining": state.questions_remaining,
        "current_question": state.current_question,
        "skill_scores": state.skill_scores,
        "is_completed": state.is_completed
    }


# ============================================================
# Compatibility Legacy Routes & Resume Management
# ============================================================

class PromptRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None
    target_role: Optional[str] = None

class ConversationRequest(BaseModel):
    role: Optional[str] = "Interview"


@app.post("/app/generate")
async def generate_legacy(data: PromptRequest, user=Depends(get_current_user)):
    """
    Seamless bridge: passes prompt through Adaptive Interview Orchestrator,
    updating candidate state, adaptation decisions, and difficulty automatically.
    """
    conversation_id = data.conversation_id
    target_role = data.target_role or "Software Engineer"

    # Create interview session if not existing
    state = orchestrator.get_state(conversation_id) if conversation_id else None
    if not state:
        state = orchestrator.create_interview(
            role=target_role,
            user_id=user.id
        )
        conversation_id = state.interview_id
        start_data = orchestrator.start_interview(conversation_id)
        q1 = start_data["question"]
        return {
            "response": f"[SPEAKER:{q1.speaker}][DIFFICULTY:steady][CODE:{'true' if q1.requires_code else 'false'}]\n\n{q1.question}",
            "conversation_id": conversation_id
        }

    # Process candidate answer through Adaptive Engine
    turn_res = orchestrator.process_candidate_answer(conversation_id, data.prompt)

    if turn_res.get("is_completed"):
        rep = turn_res["report"]
        scorecard_json = rep.model_dump_json() if hasattr(rep, 'model_dump_json') else json.dumps(rep)
        closing_msg = f"[SPEAKER:Alex][DIFFICULTY:final][CODE:false]\n\nThank you for completing the interview! Here is your final performance analysis:\n\n```json\n{scorecard_json}\n```"
        return {
            "response": closing_msg,
            "conversation_id": conversation_id
        }

    next_q = turn_res["next_question"]
    diff_tag = "rising" if next_q.difficulty >= 4 else ("easing" if next_q.difficulty <= 2 else "steady")
    bot_reply = f"[SPEAKER:{next_q.speaker}][DIFFICULTY:{diff_tag}][CODE:{'true' if next_q.requires_code else 'false'}]\n\n{next_q.question}"

    return {
        "response": bot_reply,
        "conversation_id": conversation_id,
        "evaluation": turn_res["evaluation"],
        "action_taken": turn_res["action_taken"],
        "why_this_question": turn_res["why_this_question"]
    }


@app.post("/app/conversations")
async def create_conversation(data: ConversationRequest, user=Depends(get_current_user)):
    role = data.role or "Software Engineer"
    state = orchestrator.create_interview(role=role, user_id=user.id)
    if supabase:
        try:
            supabase.table("conversations").insert({
                "id": state.interview_id,
                "user_id": user.id,
                "title": role,
                "target_role": role
            }).execute()
        except Exception:
            pass
    return {"conversation_id": state.interview_id}


@app.get("/app/conversations")
async def list_conversations(user=Depends(get_current_user)):
    if supabase:
        try:
            rows = supabase.table("conversations") \
                .select("id, title, target_role, created_at") \
                .eq("user_id", user.id) \
                .order("created_at", desc=True) \
                .execute().data
            return {"conversations": rows}
        except Exception:
            pass
    return {"conversations": []}


@app.get("/app/history/{conversation_id}")
async def get_history(conversation_id: str, user=Depends(get_current_user)):
    if supabase:
        try:
            rows = supabase.table("messages") \
                .select("role, content, created_at") \
                .eq("conversation_id", conversation_id) \
                .eq("user_id", user.id) \
                .order("created_at") \
                .execute().data
            return {"messages": rows}
        except Exception:
            pass

    # Fallback to local memory / SQLite history
    state = orchestrator.get_state(conversation_id)
    if not state:
        return {"messages": []}

    msgs = []
    for h in state.interview_history:
        q = h.question
        msgs.append({"role": "bot", "content": f"[SPEAKER:{q.speaker}][DIFFICULTY:steady][CODE:{'true' if q.requires_code else 'false'}] {q.question}"})
        msgs.append({"role": "user", "content": h.candidate_answer})
    return {"messages": msgs}


@app.get("/app/progress")
async def get_progress(user=Depends(get_current_user)):
    """Returns the candidate's past scorecards (for the dashboard trend chart)
    plus their long-term candidate memory summary (recurring strengths/weaknesses
    across sessions)."""
    scorecards = []
    if supabase:
        try:
            scorecards = supabase.table("scorecards") \
                .select("*") \
                .eq("user_id", user.id) \
                .order("created_at") \
                .execute().data or []
        except Exception as e:
            logger.warning(f"Could not fetch scorecards for progress dashboard: {e}")

    memory = orchestrator.memory_manager.get_candidate_memory(user_id=user.id)

    return {
        "scorecards": scorecards,
        "candidate_memory": memory
    }


@app.post("/app/resume/upload")
async def upload_resume(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only .pdf or .docx files are supported")

    file_bytes = await file.read()

    try:
        raw_text = extract_raw_text(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Couldn't extract any text from that file")

    structured = structure_resume(orchestrator.llm, raw_text)

    if supabase:
        try:
            supabase.table("resumes").insert({
                "user_id": user.id,
                "filename": file.filename,
                "raw_text": raw_text,
                "structured": structured,
            }).execute()
        except Exception as e:
            logger.warning(f"Error persisting resume to Supabase: {e}")

    return {"structured": structured, "raw_text": raw_text[:2000]}
