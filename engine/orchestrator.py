import uuid
import logging
from typing import Optional, Dict, Any, List
from .models import (
    CandidateState,
    InterviewPlan,
    EvaluationResult,
    AdaptationAction,
    QuestionItem,
    InterviewReport,
    DecisionLogEntry
)
from .planner import InterviewPlanner
from .evaluator import EvaluationAgent
from .adaptation_engine import AdaptiveDecisionEngine
from .question_generator import InterviewerAgent
from .anti_repetition import AntiRepetitionEngine
from .state_manager import CandidateStateManager
from .report_generator import InterviewReportGenerator
from .candidate_memory import CandidateMemoryManager
from .llm_client import get_llm_client, LLMClient
from .code_executor import CodeExecutor
from .coding_bank import get_coding_question_by_id

logger = logging.getLogger("adaptive_engine.orchestrator")


class InterviewOrchestrator:
    def __init__(
        self,
        supabase_client=None,
        llm_client: Optional[LLMClient] = None
    ):
        self.llm = llm_client or get_llm_client()
        self.anti_repetition = AntiRepetitionEngine()
        self.planner = InterviewPlanner(self.llm)
        self.evaluator = EvaluationAgent(self.llm)
        self.decision_engine = AdaptiveDecisionEngine(self.llm)
        self.question_generator = InterviewerAgent(self.llm, self.anti_repetition)
        self.state_manager = CandidateStateManager(supabase_client)
        self.report_generator = InterviewReportGenerator(self.llm)
        self.memory_manager = CandidateMemoryManager(supabase_client)
        self.code_executor = CodeExecutor()


    def create_interview(
        self,
        role: str = "Software Engineer",
        job_description: Optional[str] = None,
        resume_text: Optional[str] = None,
        resume_structured: Optional[Dict[str, Any]] = None,
        duration_minutes: int = 30,
        interview_type: str = "Full Technical & Behavioral",
        user_id: Optional[str] = None
    ) -> CandidateState:
        """Creates an interview session, generates the interview plan, and initializes state."""
        interview_id = str(uuid.uuid4())

        # Pull long-term candidate memory from past interview scorecards (None for first-timers)
        candidate_memory = self.memory_manager.get_candidate_memory(
            user_id=user_id,
            current_role=role
        )

        plan = self.planner.create_plan(
            role=role,
            job_description=job_description,
            resume_text=resume_text,
            resume_structured=resume_structured,
            duration_minutes=duration_minutes,
            interview_type=interview_type,
            candidate_memory=candidate_memory
        )

        state = self.state_manager.create_initial_state(
            interview_id=interview_id,
            role=role,
            plan=plan,
            job_description=job_description,
            resume_summary=resume_structured,
            user_id=user_id,
            interview_type=interview_type,
            candidate_memory=candidate_memory
        )

        return state

    def start_interview(self, interview_id: str) -> Dict[str, Any]:
        """Generates Question 1 for the interview session."""
        state = self.state_manager.get_state(interview_id)
        if not state:
            raise ValueError(f"Interview {interview_id} not found")

        # Initial decision
        decision = self.decision_engine.decide_next_action(state, latest_eval=None)
        
        # Generate Question 1
        q1 = self.question_generator.generate_question(state, decision)
        
        # Record question in state
        state.current_question = q1
        self.state_manager.save_state(state)

        return {
            "interview_id": interview_id,
            "question": q1,
            "current_difficulty": state.current_difficulty,
            "current_stage": state.current_stage,
            "questions_remaining": state.questions_remaining,
            "time_remaining_seconds": state.time_remaining_seconds,
            "plan_summary": {
                "role": state.role,
                "stages": state.interview_plan.stages if state.interview_plan else [],
                "skills": [s.model_dump() for s in (state.interview_plan.skills if state.interview_plan else [])],
                "strategy": state.interview_plan.strategy_summary if state.interview_plan else ""
            }
        }

    def process_candidate_answer(
        self,
        interview_id: str,
        candidate_answer: str,
        code_submission: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Core Turn Pipeline:
        1. Evaluate candidate response
        2. Decide next adaptation action
        3. Check termination (if end, generate final report)
        4. If continuing, generate next question
        5. Update candidate state and persist
        """
        state = self.state_manager.get_state(interview_id)
        if not state:
            raise ValueError(f"Interview {interview_id} not found")

        if state.is_completed:
            report = self.report_generator.generate_report(state)
            return {
                "interview_id": interview_id,
                "is_completed": True,
                "report": report
            }

        current_q = state.current_question or QuestionItem(
                    question="Tell me about your technical background.",
                    category="Technical Fundamentals",
                    skill="Core Programming",
                    difficulty=state.current_difficulty
                )

        execution_result = None
        if current_q.requires_code and current_q.coding_question_id and code_submission:
            bank_q = get_coding_question_by_id(current_q.coding_question_id)
            if bank_q:
                execution_result = self.code_executor.run(code_submission, bank_q)
        '''

        current_q = state.current_question or QuestionItem(
            question="Tell me about your technical background.",
            category="Technical Fundamentals",
            skill="Core Programming",
            difficulty=state.current_difficulty
        )

        '''

        # Step 1: Evaluate
        evaluation = self.evaluator.evaluate(
            question=current_q,
            candidate_answer=candidate_answer,
            role=state.role,
            code_submission=code_submission,
            execution_result=execution_result
        )

        # Step 2: Decide next action
        decision = self.decision_engine.decide_next_action(state, latest_eval=evaluation)
        action_taken = decision.get("action", AdaptationAction.SWITCH_SKILL)

        # Step 3: Check termination
        if action_taken == AdaptationAction.END_INTERVIEW or state.questions_remaining <= 1:
            # Finalize state
            self.state_manager.update_after_turn(
                state=state,
                candidate_answer=candidate_answer,
                evaluation=evaluation,
                decision=decision,
                next_question=None
            )
            state.is_completed = True
            self.state_manager.save_state(state)

            report = self.report_generator.generate_report(state)
            return {
                "interview_id": interview_id,
                "is_completed": True,
                "evaluation": evaluation,
                "action_taken": action_taken,
                "decision_reason": decision.get("internal_reasoning", "Interview completed."),
                "why_this_question": decision.get("why_this_question", "Interview completed."),
                "next_question": None,
                "current_difficulty": state.current_difficulty,
                "current_stage": state.current_stage,
                "questions_asked": state.questions_asked,
                "questions_remaining": 0,
                "skill_scores": state.skill_scores,
                "report": report,
                "execution_result": execution_result
            }

        # Step 4: Generate next question
        next_q = self.question_generator.generate_question(state, decision)

        # Step 5: Update state
        self.state_manager.update_after_turn(
            state=state,
            candidate_answer=candidate_answer,
            evaluation=evaluation,
            decision=decision,
            next_question=next_q
        )

        return {
            "interview_id": interview_id,
            "is_completed": False,
            "evaluation": evaluation,
            "action_taken": action_taken,
            "decision_reason": decision.get("internal_reasoning", ""),
            "why_this_question": decision.get("why_this_question", next_q.why_this_question),
            "next_question": next_q,
            "current_difficulty": state.current_difficulty,
            "current_stage": state.current_stage,
            "questions_asked": state.questions_asked,
            "questions_remaining": state.questions_remaining,
            "skill_scores": state.skill_scores,
            "report": None
        }

    def get_state(self, interview_id: str) -> Optional[CandidateState]:
        return self.state_manager.get_state(interview_id)

    def get_decision_logs(self, interview_id: str) -> List[DecisionLogEntry]:
        state = self.state_manager.get_state(interview_id)
        if not state:
            return []
        return state.decision_logs

    def get_report(self, interview_id: str) -> InterviewReport:
        state = self.state_manager.get_state(interview_id)
        if not state:
            raise ValueError(f"Interview {interview_id} not found")
        return self.report_generator.generate_report(state)


_default_orchestrator = None

def get_orchestrator(supabase_client=None) -> InterviewOrchestrator:
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = InterviewOrchestrator(supabase_client)
    return _default_orchestrator
