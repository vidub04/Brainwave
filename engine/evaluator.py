import logging
from typing import Optional, List
from .models import EvaluationResult, QuestionItem
from .llm_client import get_llm_client, LLMClient


logger = logging.getLogger("adaptive_engine.evaluator")

EVALUATOR_SYSTEM_PROMPT = """You are a rigorous, objective Technical Interview Evaluation Agent.
Your SOLE responsibility is to diagnose and score the candidate's answer to a single interview question.
You do NOT engage in conversation, you do NOT ask questions, and you do NOT talk to the candidate.
You output a structured diagnostic evaluation in JSON.

Output JSON schema:
{
  "technical_score": 0.0 to 10.0,
  "reasoning_score": 0.0 to 10.0,
  "relevance_score": 0.0 to 10.0,
  "communication_score": 0.0 to 10.0,
  "completeness_score": 0.0 to 10.0,
  "overall_score": 0.0 to 10.0,
  "missing_concepts": ["concept1", "concept2"],
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "needs_followup": true/false,
  "confidence": 0.0 to 1.0
}

Evaluation Guidelines:
1. "technical_score": Accuracy of factual statements, correctness of code/algorithms, syntax, logic.
2. "reasoning_score": Understanding of tradeoffs, depth of justification, edge-case analysis.
3. "relevance_score": Directness of response to what was specifically asked.
4. "communication_score": Clarity, structure, terminology usage, conciseness.
5. "completeness_score": Coverage of core expected concepts for this question.
6. "overall_score": Weighted synthesis (technical: 35%, reasoning: 25%, completeness: 20%, relevance: 10%, communication: 10%).
7. "missing_concepts": Important concepts or practical aspects the candidate skipped or got wrong.
8. "strengths": Specific accurate insights or positive demonstrations.
9. "weaknesses": Concrete misunderstandings, shallow explanations, or omissions.
10. "needs_followup": true if the candidate gave a partially correct or shallow answer that warrants probing, or omitted a key concept.
11. "confidence": Evidence level (0.8-1.0 if answer is substantive, 0.4-0.7 if very short or ambiguous).
"""

class EvaluationAgent:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def evaluate(
        self,
        question: QuestionItem,
        candidate_answer: str,
        role: str = "Software Engineer",
        code_submission: Optional[str] = None,
        execution_result=None
    ) -> EvaluationResult:
        """Runs the Evaluation Agent on the candidate's answer."""
        expected_str = ", ".join(question.expected_concepts) if question.expected_concepts else "Core principles"
        
        user_content = f"Candidate's Answer:\n{candidate_answer}"
        if code_submission:
            user_content += f"\n\nCandidate's Code Submission:\n```\n{code_submission}\n```"

        execution_block = ""
        if execution_result:
            execution_block = f"""
    CODE EXECUTION RESULTS (ground truth from actually running the code):
    - Passed {execution_result.passed_count}/{execution_result.total_count} test cases
    - Runtime error: {execution_result.runtime_error or 'None'}
    Trust these results over your own reading of the code for correctness.
    """

        prompt = f"""
TARGET ROLE: {role}
QUESTION CATEGORY: {question.category}
SKILL BEING TESTED: {question.skill}
DIFFICULTY LEVEL: {question.difficulty} / 5
EXPECTED CONCEPTS: {expected_str}


QUESTION ASKED:
\"\"\"{question.question}\"\"\"

{user_content}
{execution_block}

Evaluate the candidate's response rigorously.
"""

        # Resilient fallback if LLM call encounters an issue
        default_eval = {
            "technical_score": 6.0,
            "reasoning_score": 6.0,
            "relevance_score": 7.0,
            "communication_score": 7.0,
            "completeness_score": 6.0,
            "overall_score": 6.2,
            "missing_concepts": [],
            "strengths": ["Clear communication"],
            "weaknesses": [],
            "needs_followup": False,
            "confidence": 0.7
        }

        # If answer is empty or trivial
        trimmed = candidate_answer.strip()
        if len(trimmed) < 10 and not code_submission:
            return EvaluationResult(
                technical_score=1.0,
                reasoning_score=1.0,
                relevance_score=2.0,
                communication_score=2.0,
                completeness_score=1.0,
                overall_score=1.4,
                missing_concepts=question.expected_concepts or ["Direct response to question"],
                strengths=[],
                weaknesses=["Did not provide an answer or response was too brief"],
                needs_followup=True,
                confidence=0.95
            )

        raw_eval = self.llm.generate_json(
            prompt=prompt,
            system_instruction=EVALUATOR_SYSTEM_PROMPT,
            default_data=default_eval
        )

        try:
            # Clean and clamp scores between 0 and 10
            def clamp(val, low=0.0, high=10.0, default=5.0):
                try:
                    num = float(val)
                    return max(low, min(high, round(num, 1)))
                except (ValueError, TypeError):
                    return default

            tech = clamp(raw_eval.get("technical_score"), default=6.0)
            reas = clamp(raw_eval.get("reasoning_score"), default=6.0)
            rele = clamp(raw_eval.get("relevance_score"), default=7.0)
            comm = clamp(raw_eval.get("communication_score"), default=7.0)
            comp = clamp(raw_eval.get("completeness_score"), default=6.0)
            
            # Recalculate or clamp overall score
            overall = raw_eval.get("overall_score")
            if overall is not None:
                overall_val = clamp(overall, default=6.0)
            else:
                overall_val = round(tech * 0.35 + reas * 0.25 + comp * 0.20 + rele * 0.10 + comm * 0.10, 1)

            conf = raw_eval.get("confidence", 0.85)
            try:
                conf_val = max(0.1, min(1.0, float(conf)))
            except (ValueError, TypeError):
                conf_val = 0.85

            if execution_result and execution_result.total_count > 0:
                pass_rate = execution_result.passed_count / execution_result.total_count
                deterministic_score = round(pass_rate * 10.0, 1)
                tech = round(0.7 * deterministic_score + 0.3 * tech, 1)  # ground truth dominates

            missing = [str(x) for x in raw_eval.get("missing_concepts", []) if isinstance(x, (str, int, float))]
            strengths = [str(x) for x in raw_eval.get("strengths", []) if isinstance(x, (str, int, float))]
            weaknesses = [str(x) for x in raw_eval.get("weaknesses", []) if isinstance(x, (str, int, float))]
            needs_fol = bool(raw_eval.get("needs_followup", False))

            return EvaluationResult(
                technical_score=tech,
                reasoning_score=reas,
                relevance_score=rele,
                communication_score=comm,
                completeness_score=comp,
                overall_score=overall_val,
                missing_concepts=missing,
                strengths=strengths,
                weaknesses=weaknesses,
                needs_followup=needs_fol,
                confidence=conf_val
            )
        except Exception as ex:
            logger.error(f"Error parsing evaluation response: {ex}, returning fallback evaluation")
            return EvaluationResult(
                technical_score=6.0,
                reasoning_score=6.0,
                relevance_score=7.0,
                communication_score=7.0,
                completeness_score=6.0,
                overall_score=6.2,
                missing_concepts=[],
                strengths=["Candidate responded to the prompt"],
                weaknesses=[],
                needs_followup=False,
                confidence=0.7
            )
