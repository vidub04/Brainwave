import logging
from typing import Optional, Dict, Any, Tuple, List
from .models import (
    CandidateState,
    EvaluationResult,
    AdaptationAction,
    DifficultyLevel,
    QuestionItem,
    InterviewPlan
)
from .llm_client import get_llm_client, LLMClient

logger = logging.getLogger("adaptive_engine.adaptation")

DECISION_SYSTEM_PROMPT = """You are the Adaptive Decision Engine of an intelligent, agentic technical interview platform.
Your goal is to decide the single best next action, next target skill, and next difficulty level to maximize the signal gained about the candidate.

Possible Actions:
- "FOLLOW_UP": Stay on the current question/topic to probe an incomplete answer or missing concept.
- "INCREASE_DIFFICULTY": Candidate gave an outstanding answer; step up difficulty on the current skill or stage.
- "DECREASE_DIFFICULTY": Candidate is struggling or lost; step down difficulty to assess fundamental baseline.
- "SWITCH_SKILL": Candidate proved proficiency or sufficiently tested on current skill; move to next high-priority skill.
- "PROBE_WEAKNESS": Target a detected weak skill or concept with a targeted scenario or fundamental check.
- "MOVE_TO_NEW_TOPIC": Advance to the next interview stage (e.g. from Fundamentals to System Design or Behavioral).
- "REVISIT_PREVIOUS_WEAKNESS": Loop back to verify if a previously weak area was a fluke or consistent gap.
- "END_INTERVIEW": Target questions/time reached, conclude interview.

Output ONLY valid JSON matching this schema:
{
  "action": "ACTION_NAME",
  "target_skill": "Skill Name",
  "target_stage": "Stage Name",
  "new_difficulty": 1 to 5,
  "internal_reasoning": "Detailed technical justification for hackathon judges & logs",
  "why_this_question": "Concise, user-facing explanation (e.g. 'Your previous answer showed strong fundamentals, so we are increasing the difficulty to test advanced scenarios.')"
}

Guardrails:
1. Difficulty jumps must not exceed +/-1 level per turn.
2. If overall_score >= 8.0, consider INCREASE_DIFFICULTY or SWITCH_SKILL to an advanced level.
3. If overall_score <= 5.0, consider PROBE_WEAKNESS or DECREASE_DIFFICULTY.
4. If missing_concepts is non-empty and needs_followup is true, prioritize FOLLOW_UP.
5. If questions_remaining <= 0, action MUST be END_INTERVIEW.
"""

class AdaptiveDecisionEngine:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def calculate_skill_scores_priority(self, state: CandidateState) -> List[Tuple[str, float]]:
        """
        Computes multi-signal priority scores for each candidate skill:
        Score = Skill Importance + Weakness Relevance + Coverage Deficit - Repetition Penalty
        """
        scores = []
        plan_skills = {s.name: s.priority for s in (state.interview_plan.skills if state.interview_plan else [])}
        
        for skill_name, priority in state.skill_priorities.items():
            importance = priority
            current_score = state.skill_scores.get(skill_name, None)
            
            # Weakness relevance: skills scored < 6.0 need more probing
            weakness_bonus = 0.4 if (current_score is not None and current_score < 6.0) else 0.0
            
            # Repetition penalty: skills repeatedly tested and mastered (>= 8.0) get penalized
            mastery_penalty = 0.5 if (current_score is not None and current_score >= 8.5) else 0.0
            
            # Coverage deficit: skills not yet tested receive higher score
            tested_count = sum(1 for h in state.interview_history if h.question.skill == skill_name)
            coverage_bonus = 0.6 if tested_count == 0 else max(0.0, 0.3 - 0.1 * tested_count)
            
            total_priority = (importance * 0.4) + (weakness_bonus * 0.3) + (coverage_bonus * 0.3) - (mastery_penalty * 0.4)
            scores.append((skill_name, total_priority))

        # Sort descending by priority
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def decide_next_action(
        self,
        state: CandidateState,
        latest_eval: Optional[EvaluationResult] = None
    ) -> Dict[str, Any]:
        """
        Determines the next adaptation action, target skill, difficulty level, and user-facing rationale.
        """
        # Check termination condition first
        if state.questions_remaining <= 0 or state.is_completed:
            return {
                "action": AdaptationAction.END_INTERVIEW,
                "target_skill": "All Skills",
                "target_stage": "Conclusion",
                "new_difficulty": state.current_difficulty,
                "internal_reasoning": "Target question count reached. Wrapping up interview with comprehensive evaluation.",
                "why_this_question": "Interview completed. Generating your performance scorecard and personalized study plan."
            }

        # If it's the very first question (no previous evaluation)
        if latest_eval is None or not state.interview_history:
            top_skill = list(state.skill_priorities.keys())[0] if state.skill_priorities else "Technical Fundamentals"
            initial_diff = state.interview_plan.initial_difficulty if state.interview_plan else 2
            first_stage = state.interview_plan.stages[0] if state.interview_plan and state.interview_plan.stages else "Technical Fundamentals"
            return {
                "action": AdaptationAction.MOVE_TO_NEW_TOPIC,
                "target_skill": top_skill,
                "target_stage": first_stage,
                "new_difficulty": initial_diff,
                "internal_reasoning": f"Initiating interview plan with baseline difficulty {initial_diff} on high-priority skill '{top_skill}'.",
                "why_this_question": f"Starting with core fundamentals in {top_skill} to establish a baseline."
            }

        # Multi-signal analysis for subsequent turns
        current_diff = state.current_difficulty
        overall = latest_eval.overall_score
        missing = latest_eval.missing_concepts
        last_skill = state.current_question.skill if state.current_question else "Core Technical"
        last_stage = state.current_stage

        # Compute skill priorities
        skill_rankings = self.calculate_skill_scores_priority(state)
        top_uncovered_skill = skill_rankings[0][0] if skill_rankings else last_skill

        # Guardrail baseline rules
        guardrail_action = AdaptationAction.SWITCH_SKILL
        guardrail_diff = current_diff
        guardrail_reason = ""
        guardrail_why = ""

        # Case 1: Incomplete or shallow answer with important missing concepts -> FOLLOW_UP
        if latest_eval.needs_followup and missing and len(missing) > 0 and latest_eval.relevance_score >= 4.0:
            guardrail_action = AdaptationAction.FOLLOW_UP
            guardrail_diff = current_diff
            guardrail_reason = f"Candidate answered with overall score {overall:.1f} but omitted critical concept(s): {', '.join(missing[:2])}. Following up for depth."
            guardrail_why = f"Your previous answer covered the basics but left out {missing[0]}. Let's explore that aspect."

        # Case 2: Strong answer (>= 8.0) -> INCREASE_DIFFICULTY or SWITCH_SKILL at high difficulty
        elif overall >= 8.0:
            if current_diff < 5:
                guardrail_diff = min(5, current_diff + 1)
                guardrail_action = AdaptationAction.INCREASE_DIFFICULTY
                guardrail_reason = f"Candidate demonstrated high mastery ({overall:.1f}/10) on {last_skill}. Escalating difficulty from {current_diff} to {guardrail_diff}."
                guardrail_why = "Your previous answer showed strong depth and clear understanding, so we're increasing the difficulty."
            else:
                guardrail_action = AdaptationAction.SWITCH_SKILL
                guardrail_diff = 4
                guardrail_reason = f"Candidate mastered {last_skill} at maximum difficulty. Transitioning to next skill: {top_uncovered_skill}."
                guardrail_why = f"Great mastery on {last_skill}. Moving forward to assess {top_uncovered_skill}."

        # Case 3: Weak answer (<= 5.0) -> PROBE_WEAKNESS or DECREASE_DIFFICULTY
        elif overall <= 5.0:
            if current_diff > 1:
                guardrail_diff = max(1, current_diff - 1)
                guardrail_action = AdaptationAction.DECREASE_DIFFICULTY
                guardrail_reason = f"Candidate struggled ({overall:.1f}/10) on {last_skill} at difficulty {current_diff}. Lowering difficulty to {guardrail_diff} to probe fundamentals."
                guardrail_why = "Let's step back and look at a fundamental concept in this area before moving ahead."
            else:
                guardrail_action = AdaptationAction.PROBE_WEAKNESS
                guardrail_diff = 1
                guardrail_reason = f"Candidate showed persistent weakness on {last_skill}. Probing core practical fundamentals."
                guardrail_why = f"Probing fundamental practical application of {last_skill}."

        # Case 4: Moderate answer (5.1 - 7.9) -> SWITCH_SKILL or MOVE_TO_NEW_TOPIC maintaining difficulty
        else:
            guardrail_diff = current_diff
            guardrail_action = AdaptationAction.SWITCH_SKILL
            guardrail_reason = f"Candidate gave a solid answer ({overall:.1f}/10). Progressing across interview plan to test {top_uncovered_skill}."
            guardrail_why = f"Good foundational explanation. Let's move on to explore {top_uncovered_skill}."

        # Determine target stage progression
        total_q = state.interview_plan.total_target_questions if state.interview_plan else 8
        progress_ratio = state.questions_asked / max(1, total_q)
        stages = state.interview_plan.stages if state.interview_plan and state.interview_plan.stages else ["Technical Fundamentals", "System Design", "Behavioral"]
        stage_idx = min(len(stages) - 1, int(progress_ratio * len(stages)))
        target_stage = stages[stage_idx]

        # Call LLM reasoning to refine decision within guardrails
        prompt = f"""
CANDIDATE INTERVIEW STATE:
- Target Role: {state.role}
- Current Stage: {state.current_stage} -> Proposed Stage: {target_stage}
- Current Difficulty: {state.current_difficulty}
- Questions Asked: {state.questions_asked} / Total Target: {total_q}
- Questions Remaining: {state.questions_remaining}
- Skill Scores: {state.skill_scores}
- Weak Skills: {state.weak_skills}
- Strong Skills: {state.strong_skills}
- Covered Concepts: {state.covered_concepts[-6:]}

LATEST QUESTION:
\"{state.current_question.question if state.current_question else 'N/A'}\" (Skill: {last_skill}, Diff: {current_diff})

LATEST EVALUATION:
- Overall Score: {latest_eval.overall_score}/10
- Technical: {latest_eval.technical_score}, Reasoning: {latest_eval.reasoning_score}, Completeness: {latest_eval.completeness_score}
- Strengths: {latest_eval.strengths}
- Weaknesses: {latest_eval.weaknesses}
- Missing Concepts: {latest_eval.missing_concepts}
- Needs Followup: {latest_eval.needs_followup}

GUARDRAIL PROPOSED DECISION:
- Action: {guardrail_action}
- Target Skill: {top_uncovered_skill if guardrail_action != AdaptationAction.FOLLOW_UP else last_skill}
- Target Difficulty: {guardrail_diff}
- Target Stage: {target_stage}

Synthesize all signals and return the final JSON decision.
"""

        default_decision = {
            "action": guardrail_action.value if hasattr(guardrail_action, 'value') else str(guardrail_action),
            "target_skill": top_uncovered_skill if guardrail_action != AdaptationAction.FOLLOW_UP else last_skill,
            "target_stage": target_stage,
            "new_difficulty": guardrail_diff,
            "internal_reasoning": guardrail_reason,
            "why_this_question": guardrail_why
        }

        llm_decision = self.llm.generate_json(
            prompt=prompt,
            system_instruction=DECISION_SYSTEM_PROMPT,
            default_data=default_decision
        )

        try:
            raw_action = str(llm_decision.get("action", guardrail_action)).upper()
            # Match action to valid enum
            action_map = {a.value: a for a in AdaptationAction}
            final_action = action_map.get(raw_action, guardrail_action)

            # Ensure difficulty is clamped and within +/-1 of current difficulty
            new_diff = int(llm_decision.get("new_difficulty", guardrail_diff))
            diff_step = max(-1, min(1, new_diff - current_diff))
            final_diff = max(1, min(5, current_diff + diff_step))

            target_sk = str(llm_decision.get("target_skill", top_uncovered_skill))
            if final_action == AdaptationAction.FOLLOW_UP:
                target_sk = last_skill

            return {
                "action": final_action,
                "target_skill": target_sk,
                "target_stage": str(llm_decision.get("target_stage", target_stage)),
                "new_difficulty": final_diff,
                "internal_reasoning": str(llm_decision.get("internal_reasoning", guardrail_reason)),
                "why_this_question": str(llm_decision.get("why_this_question", guardrail_why))
            }
        except Exception as ex:
            logger.error(f"Error resolving adaptation decision: {ex}, returning guardrail decision")
            return {
                "action": guardrail_action,
                "target_skill": top_uncovered_skill,
                "target_stage": target_stage,
                "new_difficulty": guardrail_diff,
                "internal_reasoning": guardrail_reason,
                "why_this_question": guardrail_why
            }
