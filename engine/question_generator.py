import logging
from typing import Optional, List, Dict, Any
from .models import (
    QuestionItem,
    QuestionType,
    CandidateState,
    AdaptationAction
)
from .llm_client import get_llm_client, LLMClient
from .anti_repetition import AntiRepetitionEngine
from .coding_bank import get_coding_question

logger = logging.getLogger("adaptive_engine.question_generator")

INTERVIEWER_SYSTEM_PROMPT = """You are the Senior AI Interviewer Agent for a premier technical interview platform.
Your task is to generate exactly ONE high-signal interview question tailored directly to the candidate's interview state, current stage, skill focus, difficulty level, and adaptation directive.

You must output valid JSON matching this schema:
{
  "question": "Clear, direct, and professional question text",
  "category": "e.g. Machine Learning, Distributed Systems, Algorithms, Behavioral",
  "skill": "e.g. Model Evaluation, Concurrency, Dynamic Programming",
  "difficulty": 1 to 5,
  "type": "technical" | "coding" | "system_design" | "behavioral" | "problem_solving",
  "expected_concepts": ["concept1", "concept2", "concept3"],
  "reason": "Internal rationale for asking this specific question",
  "why_this_question": "Short, natural, candidate-facing reason (e.g. 'Your previous answer covered basics; now let us test how you handle edge cases.')",
  "speaker": "Alex" | "Ricky",
  "requires_code": true | false
}

Rules:
1. Speak as a natural, elite tech interviewer (Alex for technical/design/coding, Ricky for HR/behavioral/leadership).
2. For CODING questions (Alex DSA/algorithms): state the problem, input/output, and constraints clearly. Set requires_code to true.
3. For FOLLOW_UP questions: directly reference or build upon what the candidate previously said or missed without sounding robotic.
4. Difficulty Calibration:
   - Level 1 (Beginner): Fundamental syntax, definitions, basic usage.
   - Level 2 (Easy): Standard concepts, common library usage, standard workflows.
   - Level 3 (Intermediate): Tradeoffs, failure modes, practical production challenges, medium DSA.
   - Level 4 (Advanced): Distributed architecture, optimization, internal engine mechanics, hard edge cases.
   - Level 5 (Expert): Complex system failures, low-level concurrency, theoretical proofs, large-scale architecture.
5. NEVER repeat questions or core scenarios already asked.
"""

class InterviewerAgent:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        anti_repetition: Optional[AntiRepetitionEngine] = None
    ):
        self.llm = llm_client or get_llm_client()
        self.anti_repetition = anti_repetition or AntiRepetitionEngine()

    def _generate_coding_question(self, state, decision, target_skill, target_diff):
        bank_q = get_coding_question(
            skill=target_skill,
            role=state.role,
            difficulty=target_diff,
            exclude_ids=state.used_coding_question_ids
        )
        if not bank_q:
            return None  # falls through to LLM-generated question instead

        state.used_coding_question_ids.append(bank_q.id)

        return QuestionItem(
            question=bank_q.prompt,
            category="Problem Solving & Coding",
            skill=bank_q.skill,
            difficulty=bank_q.difficulty,
            type=QuestionType.CODING,
            expected_concepts=bank_q.expected_concepts,
            reason=f"Bank coding assessment: {bank_q.title}.",
            why_this_question=decision.get("why_this_question") or f"Let's see how you implement {bank_q.title}.",
            speaker="Alex",
            requires_code=True,
            coding_question_id=bank_q.id,
            function_signature=bank_q.function_signature,
            starter_code=bank_q.starter_code,
            visible_test_cases=[
                tc.model_dump() for tc in bank_q.test_cases if not tc.is_hidden
            ]
        )    

    def generate_question(
        self,
        state: CandidateState,
        decision: Dict[str, Any],
        max_regeneration_attempts: int = 3
    ) -> QuestionItem:
        """
        Generates the next question based on the decision and validates against anti-repetition.
        """
        action = decision.get("action", AdaptationAction.SWITCH_SKILL)
        target_skill = decision.get("target_skill", "Core Engineering")
        target_stage = decision.get("target_stage", state.current_stage)
        target_diff = int(decision.get("new_difficulty", state.current_difficulty))
        why_reason = decision.get("why_this_question", "")
        decision_reasoning = decision.get("internal_reasoning", "")

        ##coding round

        is_coding_stage = "coding" in target_stage.lower() or "problem solving" in target_stage.lower()
        if is_coding_stage and action != AdaptationAction.FOLLOW_UP:
            coding_item = self._generate_coding_question(state, decision, target_skill, target_diff)
            if coding_item:
                return coding_item

        is_behavioral_stage = "behavioral" in target_stage.lower() or "culture" in target_stage.lower()
        speaker = "Ricky" if is_behavioral_stage else "Alex"
        is_followup = action == AdaptationAction.FOLLOW_UP

        # Extract last turn context
        last_turn_text = ""
        last_eval_text = ""
        if state.interview_history:
            last_turn = state.interview_history[-1]
            last_turn_text = f"Previous Question Asked: \"{last_turn.question.question}\"\nCandidate's Previous Answer: \"{last_turn.candidate_answer[:400]}\""
            last_eval_text = f"Previous Evaluation: Overall {last_turn.evaluation.overall_score}/10, Missing: {last_turn.evaluation.missing_concepts}, Weaknesses: {last_turn.evaluation.weaknesses}"

        for attempt in range(max_regeneration_attempts):
            prompt = f"""
TARGET ROLE: {state.role}
INTERVIEW STAGE: {target_stage}
TARGET SKILL: {target_skill}
DIFFICULTY: {target_diff} / 5
ADAPTATION ACTION: {action}
SPEAKER: {speaker}

DECISION DIRECTIVE:
{decision_reasoning}

{last_turn_text}
{last_eval_text}

PREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT OR DUPLICATE):
{chr(10).join(f"- {q}" for q in state.asked_questions[-8:])}

ALREADY COVERED CONCEPTS:
{', '.join(state.covered_concepts[-12:]) if state.covered_concepts else 'None yet'}

Generate ONE top-tier interview question conforming to this directive.
"""

            default_q_type = QuestionType.BEHAVIORAL if is_behavioral_stage else QuestionType.TECHNICAL
            default_question_data = {
                "question": f"Explain the core principles of {target_skill} and describe a scenario where you implemented it.",
                "category": target_stage,
                "skill": target_skill,
                "difficulty": target_diff,
                "type": default_q_type.value,
                "expected_concepts": [target_skill, "practical application", "tradeoffs"],
                "reason": f"Evaluating candidate understanding of {target_skill} at difficulty {target_diff}.",
                "why_this_question": why_reason or f"Assessing your experience with {target_skill}.",
                "speaker": speaker,
                "requires_code": False
            }

            raw_q = self.llm.generate_json(
                prompt=prompt,
                system_instruction=INTERVIEWER_SYSTEM_PROMPT,
                default_data=default_question_data
            )

            question_text = str(raw_q.get("question", default_question_data["question"])).strip()
            category = str(raw_q.get("category", target_stage)).strip()
            skill = str(raw_q.get("skill", target_skill)).strip()
            diff = int(raw_q.get("difficulty", target_diff))
            q_type_str = str(raw_q.get("type", default_q_type.value)).lower()
            expected_concepts = [str(c) for c in raw_q.get("expected_concepts", []) if c]
            reason = str(raw_q.get("reason", decision_reasoning)).strip()
            why_text = str(raw_q.get("why_this_question", why_reason)).strip()
            speaker_out = str(raw_q.get("speaker", speaker)).strip()
            requires_code = bool(raw_q.get("requires_code", False) or q_type_str == "coding")

            # Validate Question Type enum
            q_type_enum = default_q_type
            for member in QuestionType:
                if member.value == q_type_str:
                    q_type_enum = member
                    break

            # Anti-repetition check
            is_dup, sim_score, anti_rep_reason = self.anti_repetition.check_repetition(
                new_question=question_text,
                asked_questions=state.asked_questions,
                new_concepts=expected_concepts,
                covered_concepts=state.covered_concepts,
                is_followup=is_followup
            )

            if is_dup and attempt < max_regeneration_attempts - 1:
                logger.info(f"Question rejected by AntiRepetitionEngine (attempt {attempt+1}): {anti_rep_reason}. Regenerating...")
                continue

            return QuestionItem(
                question=question_text,
                category=category,
                skill=skill,
                difficulty=diff,
                type=q_type_enum,
                expected_concepts=expected_concepts or [skill],
                reason=reason,
                why_this_question=why_text or why_reason,
                speaker=speaker_out,
                requires_code=requires_code
            )

        # Fallback question item
        return QuestionItem(
            question=f"In the context of {target_skill}, how would you approach debugging performance degradation or errors in production?",
            category=target_stage,
            skill=target_skill,
            difficulty=target_diff,
            type=QuestionType.TECHNICAL,
            expected_concepts=[target_skill, "root cause analysis", "monitoring"],
            reason="Fallback question generated on target skill.",
            why_this_question=why_reason or f"Testing practical problem solving in {target_skill}.",
            speaker=speaker,
            requires_code=False
        )
