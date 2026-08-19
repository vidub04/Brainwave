import os
import json
import sqlite3
import time
import logging
from typing import Optional, Dict, Any, List
from .models import (
    CandidateState,
    InterviewPlan,
    EvaluationResult,
    AdaptationAction,
    QuestionItem,
    DecisionLogEntry,
    InterviewHistoryTurn
)

logger = logging.getLogger("adaptive_engine.state_manager")

DB_PATH = os.path.join(os.path.dirname(__file__), "interviews_cache.db")


class SkillTracker:
    """Manages skill scores, running averages, and strong/weak skill classifications."""
    
    @staticmethod
    def update_skill_scores(
        state: CandidateState,
        tested_skill: str,
        evaluation: EvaluationResult,
        alpha: float = 0.65
    ) -> None:
        turn_score = evaluation.overall_score
        
        # Update or initialize skill score
        if tested_skill in state.skill_scores:
            prev = state.skill_scores[tested_skill]
            new_score = round(alpha * turn_score + (1.0 - alpha) * prev, 1)
        else:
            new_score = round(turn_score, 1)

        state.skill_scores[tested_skill] = new_score

        # Update weak and strong classifications
        weak = []
        strong = []
        for s, score in state.skill_scores.items():
            if score >= 7.5:
                strong.append(s)
            elif score < 6.0:
                weak.append(s)

        state.weak_skills = weak
        state.strong_skills = strong

        # Track covered concepts
        if state.current_question and state.current_question.expected_concepts:
            for c in state.current_question.expected_concepts:
                if c not in state.covered_concepts:
                    state.covered_concepts.append(c)

        # Track missing concepts
        if evaluation.missing_concepts:
            for m in evaluation.missing_concepts:
                if m not in state.missing_concepts:
                    state.missing_concepts.append(m)


class CandidateStateManager:
    """Handles interview state updates, history logging, and database persistence."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self._memory_store: Dict[str, CandidateState] = {}
        self._init_sqlite()

    def _init_sqlite(self):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS interview_sessions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        role TEXT,
                        state_json TEXT,
                        updated_at REAL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite state cache: {e}")

    def create_initial_state(
        self,
        interview_id: str,
        role: str,
        plan: InterviewPlan,
        job_description: Optional[str] = None,
        resume_summary: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        interview_type: str = "Standard"
    ) -> CandidateState:
        """Initializes state from an InterviewPlan."""
        total_q = plan.total_target_questions or 8
        duration_sec = (plan.target_duration_minutes or 30) * 60

        skill_priorities = {s.name: s.priority for s in plan.skills}

        state = CandidateState(
            interview_id=interview_id,
            user_id=user_id,
            role=role,
            interview_type=interview_type,
            target_duration_minutes=plan.target_duration_minutes,
            start_time=time.time(),
            current_stage=plan.stages[0] if plan.stages else "Technical Fundamentals",
            current_difficulty=plan.initial_difficulty,
            questions_asked=0,
            questions_remaining=total_q,
            time_remaining_seconds=duration_sec,
            is_completed=False,
            skill_scores={},
            skill_priorities=skill_priorities,
            weak_skills=[],
            strong_skills=[],
            asked_questions=[],
            covered_concepts=[],
            missing_concepts=[],
            recent_performance=[],
            interview_history=[],
            decision_logs=[],
            interview_plan=plan,
            resume_summary=resume_summary,
            job_description=job_description
        )

        self.save_state(state)
        return state

    def update_after_turn(
        self,
        state: CandidateState,
        candidate_answer: str,
        evaluation: EvaluationResult,
        decision: Dict[str, Any],
        next_question: Optional[QuestionItem] = None
    ) -> CandidateState:
        """Updates candidate state following answer evaluation and adaptation decision."""
        current_q = state.current_question
        if current_q:
            tested_skill = current_q.skill
            SkillTracker.update_skill_scores(state, tested_skill, evaluation)
            
            # Record in asked questions
            if current_q.question not in state.asked_questions:
                state.asked_questions.append(current_q.question)

            # Record turn history
            turn_number = state.questions_asked + 1
            action_taken = decision.get("action", AdaptationAction.SWITCH_SKILL)
            reason = decision.get("internal_reasoning", "")
            
            turn_entry = InterviewHistoryTurn(
                turn_number=turn_number,
                question=current_q,
                candidate_answer=candidate_answer,
                evaluation=evaluation,
                decision=action_taken,
                decision_reason=reason,
                timestamp=time.time()
            )
            state.interview_history.append(turn_entry)

            # Record Decision Log for judges/evaluators
            diff_before = state.current_difficulty
            diff_after = int(decision.get("new_difficulty", diff_before))
            
            log_entry = DecisionLogEntry(
                turn_index=turn_number,
                question_text=current_q.question,
                skill=tested_skill,
                category=current_q.category,
                difficulty_before=diff_before,
                difficulty_after=diff_after,
                evaluation=evaluation,
                action_taken=action_taken,
                decision_reasoning=reason,
                candidate_answer_preview=candidate_answer[:120] + ("..." if len(candidate_answer) > 120 else ""),
                timestamp=time.time()
            )
            state.decision_logs.append(log_entry)

            state.recent_performance.append(evaluation.overall_score)
            state.questions_asked += 1
            state.questions_remaining = max(0, state.questions_remaining - 1)

        # Update difficulty & stage for next turn
        state.current_difficulty = int(decision.get("new_difficulty", state.current_difficulty))
        state.current_stage = str(decision.get("target_stage", state.current_stage))
        state.current_question = next_question

        # Update elapsed time
        elapsed = int(time.time() - state.start_time)
        total_time = state.target_duration_minutes * 60
        state.time_remaining_seconds = max(0, total_time - elapsed)

        if decision.get("action") == AdaptationAction.END_INTERVIEW or state.questions_remaining <= 0:
            state.is_completed = True

        self.save_state(state)
        return state

    def save_state(self, state: CandidateState) -> None:
        """Persists state to in-memory store, SQLite, and Supabase."""
        self._memory_store[state.interview_id] = state

        # Save to SQLite
        try:
            state_json = state.model_dump_json()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO interview_sessions (id, user_id, role, state_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (state.interview_id, state.user_id, state.role, state_json, time.time()))
                conn.commit()
        except Exception as ex:
            logger.error(f"Failed to persist state to SQLite: {ex}")

        # Mirror to Supabase if available
        if self.supabase:
            try:
                self.supabase.table("conversations").update({
                    "target_role": state.role,
                }).eq("id", state.interview_id).execute()
            except Exception:
                pass

    def get_state(self, interview_id: str) -> Optional[CandidateState]:
        """Loads state by interview_id."""
        if interview_id in self._memory_store:
            return self._memory_store[interview_id]

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT state_json FROM interview_sessions WHERE id = ?", (interview_id,))
                row = cursor.fetchone()
                if row:
                    state_dict = json.loads(row[0])
                    state = CandidateState(**state_dict)
                    self._memory_store[interview_id] = state
                    return state
        except Exception as ex:
            logger.error(f"Error loading state from SQLite for {interview_id}: {ex}")

        return None
