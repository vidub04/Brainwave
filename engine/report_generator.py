import logging
import time
from typing import Optional, List, Dict, Any
from .models import (
    CandidateState,
    InterviewReport,
    EvidenceItem,
    PreparationPlan
)
from .llm_client import get_llm_client, LLMClient

logger = logging.getLogger("adaptive_engine.report_generator")

REPORT_SYSTEM_PROMPT = """You are the Principal Bar Raiser and Technical Evaluation Architect.
Your task is to generate an exhaustive, evidence-backed final interview report and a customized 7/14/30-day preparation roadmap based on the candidate's complete interview trajectory.

Output valid JSON matching this schema:
{
  "overall_score": 0.0 to 100.0,
  "score_grade": "Strong Hire" | "Hire" | "Borderline" | "Needs Work",
  "summary": "2-3 paragraph executive evaluation summary",
  "skill_breakdown": {
    "Skill A": 85.0,
    "Skill B": 65.0
  },
  "category_scores": {
    "Technical Fundamentals": 8.0,
    "System Design": 6.5,
    "Problem Solving": 7.0,
    "Communication": 8.5
  },
  "strengths": ["Clear strength 1", "Clear strength 2"],
  "weaknesses": ["Specific weakness 1", "Specific weakness 2"],
  "evidence": [
    {
      "skill_or_concept": "Concept name",
      "weakness_summary": "Diagnosis of what was missing",
      "question_asked": "Exact question text",
      "candidate_answer_excerpt": "Quote or excerpt of candidate answer",
      "turn_number": 1,
      "severity": "Minor" | "Moderate" | "High"
    }
  ],
  "preparation_plan": {
    "day_7_focus": ["Day 1-7 actionable goals and fundamentals to master"],
    "day_14_focus": ["Day 8-14 intermediate scenarios and applied practice"],
    "day_30_focus": ["Day 15-30 advanced system architecture & full mock simulations"],
    "recommended_resources": [
      {"topic": "Topic Name", "resource": "Specific book, documentation, or guide"}
    ]
  }
}

Guidelines:
1. Every major weakness MUST cite exact evidence from the interview turns (question + answer excerpt).
2. The 7/14/30-day plan must directly address the specific missing concepts and weak skills diagnosed during the interview.
3. Calibrate score_grade:
   - 85-100: "Strong Hire"
   - 70-84: "Hire"
   - 55-69: "Borderline"
   - < 55: "Needs Work"
"""

class InterviewReportGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def generate_report(self, state: CandidateState) -> InterviewReport:
        """Generates the comprehensive final report with evidence cards and study plan."""
        # Calculate quantitative aggregates
        all_evals = [h.evaluation for h in state.interview_history if h.evaluation]
        if all_evals:
            avg_overall = sum(e.overall_score for e in all_evals) / len(all_evals)
            scaled_score = round(min(100.0, max(0.0, avg_overall * 10.0)), 1)
        else:
            scaled_score = 50.0

        # Skill percentage breakdown
        skill_breakdown = {}
        for s, score in state.skill_scores.items():
            skill_breakdown[s] = round(min(100.0, max(0.0, score * 10.0)), 1)

        # Build trajectory summary for LLM synthesis
        trajectory_lines = []
        for h in state.interview_history:
            q = h.question
            ev = h.evaluation
            trajectory_lines.append(
                f"Turn {h.turn_number} [{q.category} / {q.skill} / Diff {q.difficulty}]:\n"
                f"Question: \"{q.question}\"\n"
                f"Candidate Answer: \"{h.candidate_answer}\"\n"
                f"Evaluation Score: {ev.overall_score}/10 (Tech: {ev.technical_score}, Reasoning: {ev.reasoning_score}, Comm: {ev.communication_score})\n"
                f"Strengths: {ev.strengths}\n"
                f"Weaknesses: {ev.weaknesses}\n"
                f"Missing Concepts: {ev.missing_concepts}\n"
            )

        trajectory_text = "\n".join(trajectory_lines)

        prompt = f"""
CANDIDATE ROLE: {state.role}
INTERVIEW DURATION: {state.target_duration_minutes} minutes
TOTAL QUESTIONS ASKED: {state.questions_asked}
SKILL SCORES (out of 10): {state.skill_scores}
WEAK SKILLS: {state.weak_skills}
STRONG SKILLS: {state.strong_skills}
ALL MISSING CONCEPTS: {state.missing_concepts}

COMPLETE INTERVIEW TRAJECTORY:
{trajectory_text}

Generate the comprehensive final interview report and personalized 7/14/30-day prep roadmap.
"""

        # Fallback evidence builder from turns
        default_evidence = []
        for h in state.interview_history:
            if h.evaluation.overall_score < 6.0 or h.evaluation.missing_concepts:
                default_evidence.append({
                    "skill_or_concept": h.question.skill,
                    "weakness_summary": h.evaluation.weaknesses[0] if h.evaluation.weaknesses else "Omitted core concepts",
                    "question_asked": h.question.question,
                    "candidate_answer_excerpt": h.candidate_answer[:100] + "...",
                    "turn_number": h.turn_number,
                    "severity": "High" if h.evaluation.overall_score < 4.5 else "Moderate"
                })

        default_report_data = {
            "overall_score": scaled_score,
            "score_grade": "Hire" if scaled_score >= 70 else ("Borderline" if scaled_score >= 55 else "Needs Work"),
            "summary": f"The candidate completed an adaptive technical interview for {state.role}. Demonstrated foundational proficiency in primary skills with identified areas for deeper architectural and edge-case preparation.",
            "skill_breakdown": skill_breakdown or {state.role: scaled_score},
            "category_scores": {
                "Technical Fundamentals": round(min(10.0, scaled_score / 10.0), 1),
                "Problem Solving": round(min(10.0, (scaled_score + 2) / 10.0), 1),
                "Communication": 8.0
            },
            "strengths": state.strong_skills or ["Good conceptual communication"],
            "weaknesses": state.weak_skills or ["Practical edge-case depth"],
            "evidence": default_evidence[:4],
            "preparation_plan": {
                "day_7_focus": [f"Review core fundamentals in {s}" for s in (state.weak_skills or ["core CS"])] + ["Practice 10 targeted interview problems"],
                "day_14_focus": ["Implement end-to-end practical implementations", "Analyze production tradeoffs and failure recovery"],
                "day_30_focus": ["Conduct full mock interview simulations under timed pressure", "Review scalable system design patterns"],
                "recommended_resources": [
                    {"topic": s, "resource": f"Official documentation and production best practices for {s}"}
                    for s in (state.weak_skills or [state.role])
                ]
            }
        }

        raw_report = self.llm.generate_json(
            prompt=prompt,
            system_instruction=REPORT_SYSTEM_PROMPT,
            default_data=default_report_data
        )

        try:
            final_overall = float(raw_report.get("overall_score", scaled_score))
            grade = str(raw_report.get("score_grade", default_report_data["score_grade"]))
            summary = str(raw_report.get("summary", default_report_data["summary"]))
            
            raw_breakdown = raw_report.get("skill_breakdown", skill_breakdown)
            clean_breakdown = {}
            if isinstance(raw_breakdown, dict):
                for k, v in raw_breakdown.items():
                    try:
                        clean_breakdown[str(k)] = float(v)
                    except Exception:
                        clean_breakdown[str(k)] = 70.0
            else:
                clean_breakdown = skill_breakdown

            category_scores = {}
            raw_cat = raw_report.get("category_scores", default_report_data["category_scores"])
            if isinstance(raw_cat, dict):
                for k, v in raw_cat.items():
                    try:
                        category_scores[str(k)] = float(v)
                    except Exception:
                        category_scores[str(k)] = 7.0

            strengths = [str(x) for x in raw_report.get("strengths", default_report_data["strengths"]) if x]
            weaknesses = [str(x) for x in raw_report.get("weaknesses", default_report_data["weaknesses"]) if x]

            evidence_items = []
            for ev in raw_report.get("evidence", default_evidence):
                if isinstance(ev, dict):
                    evidence_items.append(EvidenceItem(
                        skill_or_concept=str(ev.get("skill_or_concept", "Core Area")),
                        weakness_summary=str(ev.get("weakness_summary", "Unaddressed concept")),
                        question_asked=str(ev.get("question_asked", "")),
                        candidate_answer_excerpt=str(ev.get("candidate_answer_excerpt", "")),
                        turn_number=int(ev.get("turn_number", 1)),
                        severity=str(ev.get("severity", "Moderate"))
                    ))

            prep_data = raw_report.get("preparation_plan", default_report_data["preparation_plan"])
            prep_plan = PreparationPlan(
                day_7_focus=[str(x) for x in prep_data.get("day_7_focus", []) if x],
                day_14_focus=[str(x) for x in prep_data.get("day_14_focus", []) if x],
                day_30_focus=[str(x) for x in prep_data.get("day_30_focus", []) if x],
                recommended_resources=[
                    {"topic": str(r.get("topic", "")), "resource": str(r.get("resource", ""))}
                    for r in prep_data.get("recommended_resources", [])
                    if isinstance(r, dict)
                ]
            )

            elapsed_mins = round((time.time() - state.start_time) / 60.0, 1)

            return InterviewReport(
                interview_id=state.interview_id,
                candidate_role=state.role,
                overall_score=final_overall,
                score_grade=grade,
                summary=summary,
                total_questions=state.questions_asked,
                duration_minutes=elapsed_mins,
                skill_breakdown=clean_breakdown,
                category_scores=category_scores,
                strengths=strengths,
                weaknesses=weaknesses,
                evidence=evidence_items,
                preparation_plan=prep_plan
            )
        except Exception as ex:
            logger.error(f"Error structuring final interview report: {ex}, returning default report")
            return InterviewReport(
                interview_id=state.interview_id,
                candidate_role=state.role,
                overall_score=scaled_score,
                score_grade="Hire" if scaled_score >= 70 else "Borderline",
                summary=f"Candidate successfully finished the {state.role} interview. Strong baseline competence across core focus areas.",
                total_questions=state.questions_asked,
                duration_minutes=round((time.time() - state.start_time) / 60.0, 1),
                skill_breakdown=skill_breakdown or {state.role: scaled_score},
                category_scores=default_report_data["category_scores"],
                strengths=default_report_data["strengths"],
                weaknesses=default_report_data["weaknesses"],
                evidence=[EvidenceItem(**ev) for ev in default_evidence[:3]],
                preparation_plan=PreparationPlan(**default_report_data["preparation_plan"])
            )
