from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import time
import uuid


class DifficultyLevel(int, Enum):
    BEGINNER = 1
    EASY = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class AdaptationAction(str, Enum):
    FOLLOW_UP = "FOLLOW_UP"
    INCREASE_DIFFICULTY = "INCREASE_DIFFICULTY"
    DECREASE_DIFFICULTY = "DECREASE_DIFFICULTY"
    SWITCH_SKILL = "SWITCH_SKILL"
    SWITCH_CATEGORY = "SWITCH_CATEGORY"
    PROBE_WEAKNESS = "PROBE_WEAKNESS"
    MOVE_TO_NEW_TOPIC = "MOVE_TO_NEW_TOPIC"
    REVISIT_PREVIOUS_WEAKNESS = "REVISIT_PREVIOUS_WEAKNESS"
    END_INTERVIEW = "END_INTERVIEW"


class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"
    PROBLEM_SOLVING = "problem_solving"


class SkillPriority(BaseModel):
    name: str
    priority: float = Field(default=0.8, ge=0.0, le=1.0)
    current_score: Optional[float] = None
    questions_count: int = 0
    weakness_count: int = 0
    mastery_count: int = 0


class InterviewPlan(BaseModel):
    role: str
    skills: List[SkillPriority] = Field(default_factory=list)
    stages: List[str] = Field(default_factory=lambda: [
        "Technical Fundamentals",
        "Applied Domain Knowledge",
        "Problem Solving & Coding",
        "System Design",
        "Behavioral & Culture"
    ])
    initial_difficulty: int = 2
    total_target_questions: int = 8
    target_duration_minutes: int = 30
    stage_distribution: Dict[str, float] = Field(default_factory=dict)
    strategy_summary: str = "Assess core CS fundamentals and role-specific depth with dynamic difficulty progression."


class EvaluationResult(BaseModel):
    technical_score: float = Field(ge=0.0, le=10.0)
    reasoning_score: float = Field(ge=0.0, le=10.0)
    relevance_score: float = Field(ge=0.0, le=10.0)
    communication_score: float = Field(ge=0.0, le=10.0)
    completeness_score: float = Field(ge=0.0, le=10.0)
    overall_score: float = Field(ge=0.0, le=10.0)
    missing_concepts: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    needs_followup: bool = False
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class QuestionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    category: str
    skill: str
    difficulty: int = Field(default=3, ge=1, le=5)
    type: QuestionType = QuestionType.TECHNICAL
    expected_concepts: List[str] = Field(default_factory=list)
    reason: str = ""
    why_this_question: str = ""
    speaker: str = "Alex"
    requires_code: bool = False


class DecisionLogEntry(BaseModel):
    turn_index: int
    question_text: str
    skill: str
    category: str
    difficulty_before: int
    difficulty_after: int
    evaluation: Optional[EvaluationResult] = None
    action_taken: AdaptationAction
    decision_reasoning: str
    candidate_answer_preview: str = ""
    timestamp: float = Field(default_factory=time.time)


class InterviewHistoryTurn(BaseModel):
    turn_number: int
    question: QuestionItem
    candidate_answer: str
    evaluation: EvaluationResult
    decision: AdaptationAction
    decision_reason: str
    timestamp: float = Field(default_factory=time.time)


class CandidateState(BaseModel):
    interview_id: str
    user_id: Optional[str] = None
    role: str
    interview_type: str = "Standard"
    target_duration_minutes: int = 30
    start_time: float = Field(default_factory=time.time)
    current_stage: str = "Technical Fundamentals"
    current_difficulty: int = 2
    questions_asked: int = 0
    questions_remaining: int = 8
    time_remaining_seconds: int = 1800
    is_completed: bool = False

    skill_scores: Dict[str, float] = Field(default_factory=dict)
    skill_priorities: Dict[str, float] = Field(default_factory=dict)
    weak_skills: List[str] = Field(default_factory=list)
    strong_skills: List[str] = Field(default_factory=list)

    asked_questions: List[str] = Field(default_factory=list)
    covered_concepts: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)

    recent_performance: List[float] = Field(default_factory=list)
    interview_history: List[InterviewHistoryTurn] = Field(default_factory=list)
    decision_logs: List[DecisionLogEntry] = Field(default_factory=list)
    
    current_question: Optional[QuestionItem] = None
    interview_plan: Optional[InterviewPlan] = None
    resume_summary: Optional[Dict[str, Any]] = None
    job_description: Optional[str] = None


class EvidenceItem(BaseModel):
    skill_or_concept: str
    weakness_summary: str
    question_asked: str
    candidate_answer_excerpt: str
    turn_number: int
    severity: str = "Moderate"  # Minor, Moderate, High


class PreparationPlan(BaseModel):
    day_7_focus: List[str] = Field(default_factory=list)
    day_14_focus: List[str] = Field(default_factory=list)
    day_30_focus: List[str] = Field(default_factory=list)
    recommended_resources: List[Dict[str, str]] = Field(default_factory=list)


class InterviewReport(BaseModel):
    interview_id: str
    candidate_role: str
    overall_score: float = Field(ge=0.0, le=100.0)
    score_grade: str = "Borderline"  # Strong Hire, Hire, Borderline, Needs Work
    summary: str
    total_questions: int
    duration_minutes: float
    skill_breakdown: Dict[str, float] = Field(default_factory=dict)
    category_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    preparation_plan: PreparationPlan
    created_at: float = Field(default_factory=time.time)


# API Request / Response Schemas
class CreateInterviewRequest(BaseModel):
    role: str = "Software Engineer"
    job_description: Optional[str] = None
    resume_text: Optional[str] = None
    resume_structured: Optional[Dict[str, Any]] = None
    duration_minutes: int = 30
    interview_type: str = "Full Technical & Behavioral"


class StartInterviewResponse(BaseModel):
    interview_id: str
    question: QuestionItem
    current_difficulty: int
    current_stage: str
    questions_remaining: int
    time_remaining_seconds: int
    plan_summary: Dict[str, Any]


class SubmitAnswerRequest(BaseModel):
    answer: str
    code: Optional[str] = None
    time_spent_seconds: Optional[int] = 0


class SubmitAnswerResponse(BaseModel):
    interview_id: str
    is_completed: bool
    evaluation: EvaluationResult
    action_taken: AdaptationAction
    decision_reason: str
    why_this_question: str
    next_question: Optional[QuestionItem] = None
    current_difficulty: int
    current_stage: str
    questions_asked: int
    questions_remaining: int
    skill_scores: Dict[str, float]
    report: Optional[InterviewReport] = None
