import logging
from typing import Optional, List, Dict, Any
from .models import CandidateMemory

logger = logging.getLogger("adaptive_engine.candidate_memory")

# Skill-ish scorecard columns we can trend over time (out of 10 each in the scorecards table)
SCORECARD_SKILL_COLUMNS = [
    "technical_knowledge",
    "problem_solving",
    "core_cs_fundamentals",
    "project_knowledge",
    "communication",
    "confidence",
    "leadership",
    "behavioral_skills",
]

STRONG_THRESHOLD = 7.5
WEAK_THRESHOLD = 6.0

MAX_PAST_INTERVIEWS = 5  # how many recent scorecards to pull for memory


class CandidateMemoryManager:
    """
    Builds a long-term memory profile of a candidate from their past interview
    scorecards, so a *new* interview session can start by leaning on what we
    already learned about them, instead of treating every session as a
    stranger with no history.
    """

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client

    def get_candidate_memory(
        self,
        user_id: Optional[str],
        current_role: Optional[str] = None
    ) -> Optional[CandidateMemory]:
        """Fetches and aggregates a candidate's past scorecards into a CandidateMemory.

        Returns None if there is no Supabase client, no user_id, or no past
        history — i.e. a first-time candidate, which is a valid/expected case.
        """
        if not self.supabase or not user_id:
            return None

        try:
            result = (
                self.supabase.table("scorecards")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(MAX_PAST_INTERVIEWS)
                .execute()
            )
            rows: List[Dict[str, Any]] = result.data or []
        except Exception as e:
            logger.warning(f"Could not fetch candidate memory for {user_id}: {e}")
            return None

        if not rows:
            return None

        # Oldest -> newest, so trends read chronologically
        rows = list(reversed(rows))

        overall_scores = []
        skill_running_totals: Dict[str, List[float]] = {c: [] for c in SCORECARD_SKILL_COLUMNS}

        for row in rows:
            per_skill_vals = []
            for col in SCORECARD_SKILL_COLUMNS:
                try:
                    val = float(row.get(col) or 0)
                except (TypeError, ValueError):
                    val = 0.0
                skill_running_totals[col].append(val)
                per_skill_vals.append(val)
            if per_skill_vals:
                overall_scores.append(sum(per_skill_vals) / len(per_skill_vals))

        avg_overall_score = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0.0

        skill_averages = {
            col: round(sum(vals) / len(vals), 1)
            for col, vals in skill_running_totals.items() if vals
        }

        recurring_weak_skills = sorted(
            [s for s, avg in skill_averages.items() if avg < WEAK_THRESHOLD],
            key=lambda s: skill_averages[s]
        )
        recurring_strong_skills = sorted(
            [s for s, avg in skill_averages.items() if avg >= STRONG_THRESHOLD],
            key=lambda s: -skill_averages[s]
        )

        last_row = rows[-1]
        last_role = last_row.get("target_role")
        last_recommendation = last_row.get("recommendation")

        # Simple trend: compare first-half vs second-half average overall score
        score_trend = [round(s, 1) for s in overall_scores]
        trend_direction = "stable"
        if len(overall_scores) >= 2:
            midpoint = len(overall_scores) // 2 or 1
            first_half_avg = sum(overall_scores[:midpoint]) / midpoint
            second_half_avg = sum(overall_scores[midpoint:]) / max(1, len(overall_scores) - midpoint)
            if second_half_avg - first_half_avg >= 0.5:
                trend_direction = "improving"
            elif first_half_avg - second_half_avg >= 0.5:
                trend_direction = "declining"

        summary_text = self._build_summary_text(
            total_past_interviews=len(rows),
            avg_overall_score=avg_overall_score,
            recurring_weak_skills=recurring_weak_skills,
            recurring_strong_skills=recurring_strong_skills,
            last_role=last_role,
            last_recommendation=last_recommendation,
            trend_direction=trend_direction,
            current_role=current_role
        )

        return CandidateMemory(
            total_past_interviews=len(rows),
            avg_overall_score=avg_overall_score,
            recurring_weak_skills=recurring_weak_skills,
            recurring_strong_skills=recurring_strong_skills,
            last_role=last_role,
            last_recommendation=last_recommendation,
            score_trend=score_trend,
            trend_direction=trend_direction,
            summary_text=summary_text
        )

    def _build_summary_text(
        self,
        total_past_interviews: int,
        avg_overall_score: float,
        recurring_weak_skills: List[str],
        recurring_strong_skills: List[str],
        last_role: Optional[str],
        last_recommendation: Optional[str],
        trend_direction: str,
        current_role: Optional[str]
    ) -> str:
        """Builds a compact natural-language brief the LLM planner/report can consume directly."""
        parts = [
            f"This candidate has completed {total_past_interviews} prior interview(s) on this platform, "
            f"with an average overall score of {avg_overall_score}/10 (trend: {trend_direction})."
        ]
        if last_role:
            parts.append(f"Most recent prior interview was for the role '{last_role}'"
                         + (f", with a recommendation of '{last_recommendation}'." if last_recommendation else "."))
        if recurring_weak_skills:
            parts.append(f"Recurring weak areas across past interviews: {', '.join(recurring_weak_skills)}.")
        if recurring_strong_skills:
            parts.append(f"Consistently strong areas: {', '.join(recurring_strong_skills)}.")
        if current_role and last_role and current_role.lower() != last_role.lower():
            parts.append(f"Note: candidate is now targeting '{current_role}', a different role than last time — "
                         f"reuse relevant past signal but do not over-anchor to the previous role's skill set.")
        return " ".join(parts)
