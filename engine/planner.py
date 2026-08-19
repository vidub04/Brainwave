import logging
from typing import Optional, Dict, Any
from .models import InterviewPlan, SkillPriority
from .llm_client import get_llm_client, LLMClient

logger = logging.getLogger("adaptive_engine.planner")

PLANNER_SYSTEM_PROMPT = """You are an expert Technical Interview Planner and Lead Engineering Hiring Architect.
Your task is to analyze the candidate's resume, the target job description, and the target role to generate a comprehensive, adaptive interview plan.

Generate structured JSON matching this schema:
{
  "role": "string",
  "skills": [
    {
      "name": "string",
      "priority": 0.0 to 1.0
    }
  ],
  "stages": [
    "Technical Fundamentals",
    "Applied Domain Knowledge",
    "Problem Solving",
    "System Design",
    "Behavioral"
  ],
  "initial_difficulty": 1 to 5,
  "total_target_questions": 6 to 10,
  "stage_distribution": {
    "Technical Fundamentals": 0.25,
    "Applied Domain Knowledge": 0.30,
    "Problem Solving": 0.20,
    "System Design": 0.15,
    "Behavioral": 0.10
  },
  "strategy_summary": "string explaining how the interview should progress"
}

Guidelines:
1. Identify 4-7 critical skills with appropriate priority weights (0.0 to 1.0). Top role requirements should have priority >= 0.85.
2. Calibrate initial_difficulty based on resume experience (1: Intern/New Grad, 2: Junior/Mid, 3: Mid-Senior, 4: Senior/Lead, 5: Staff/Principal). Default to 2 or 3 if unspecified.
3. Total questions should be proportional to duration (e.g. 20-30 mins = 6-8 questions, 45-60 mins = 9-12 questions).
4. Stage distribution must sum to approximately 1.0.
"""

class InterviewPlanner:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def create_plan(
        self,
        role: str,
        job_description: Optional[str] = None,
        resume_text: Optional[str] = None,
        resume_structured: Optional[Dict[str, Any]] = None,
        duration_minutes: int = 30,
        interview_type: str = "Standard"
    ) -> InterviewPlan:
        """Analyzes candidate resume & JD to produce the initial interview plan."""
        resume_summary = ""
        if resume_structured:
            skills = ", ".join(resume_structured.get("skills", []))
            exp = resume_structured.get("years_experience", "N/A")
            summary = resume_structured.get("summary", "")
            resume_summary = f"Structured Resume:\n- Skills: {skills}\n- Experience: {exp} years\n- Summary: {summary}"
        elif resume_text:
            resume_summary = f"Resume Raw Text:\n{resume_text[:2000]}"

        jd_text = job_description or "Standard expectations for a top-tier tech company role."

        prompt = f"""
TARGET ROLE: {role}
INTERVIEW DURATION: {duration_minutes} minutes
INTERVIEW TYPE: {interview_type}

JOB DESCRIPTION:
\"\"\"{jd_text[:2500]}\"\"\"

CANDIDATE RESUME:
\"\"\"{resume_summary}\"\"\"

Generate the complete interview plan in JSON format.
"""

        # Determine sensible fallback plan if LLM is unavailable
        default_skills = self._get_default_skills_for_role(role)
        target_questions = max(5, min(12, int(duration_minutes / 3.5)))
        default_plan_data = {
            "role": role,
            "skills": [{"name": s[0], "priority": s[1]} for s in default_skills],
            "stages": [
                "Technical Fundamentals",
                "Applied Domain Knowledge",
                "Problem Solving",
                "System Design",
                "Behavioral"
            ],
            "initial_difficulty": 2,
            "total_target_questions": target_questions,
            "stage_distribution": {
                "Technical Fundamentals": 0.25,
                "Applied Domain Knowledge": 0.30,
                "Problem Solving": 0.20,
                "System Design": 0.15,
                "Behavioral": 0.10
            },
            "strategy_summary": f"Targeted assessment for {role} focusing on fundamental depth, practical scenario problem solving, and architecture."
        }

        raw_result = self.llm.generate_json(
            prompt=prompt,
            system_instruction=PLANNER_SYSTEM_PROMPT,
            default_data=default_plan_data
        )

        try:
            skills_list = []
            for s in raw_result.get("skills", []):
                if isinstance(s, dict) and "name" in s:
                    skills_list.append(SkillPriority(
                        name=str(s.get("name")),
                        priority=float(s.get("priority", 0.8))
                    ))
                elif isinstance(s, str):
                    skills_list.append(SkillPriority(name=s, priority=0.8))

            if not skills_list:
                skills_list = [SkillPriority(name=s[0], priority=s[1]) for s in default_skills]

            plan = InterviewPlan(
                role=raw_result.get("role", role),
                skills=skills_list,
                stages=raw_result.get("stages", default_plan_data["stages"]),
                initial_difficulty=int(raw_result.get("initial_difficulty", 2)),
                total_target_questions=int(raw_result.get("total_target_questions", target_questions)),
                target_duration_minutes=duration_minutes,
                stage_distribution=raw_result.get("stage_distribution", default_plan_data["stage_distribution"]),
                strategy_summary=raw_result.get("strategy_summary", default_plan_data["strategy_summary"])
            )
            return plan
        except Exception as ex:
            logger.error(f"Error parsing interview plan: {ex}, returning default plan")
            return InterviewPlan(
                role=role,
                skills=[SkillPriority(name=s[0], priority=s[1]) for s in default_skills],
                stages=default_plan_data["stages"],
                initial_difficulty=2,
                total_target_questions=target_questions,
                target_duration_minutes=duration_minutes,
                stage_distribution=default_plan_data["stage_distribution"],
                strategy_summary=default_plan_data["strategy_summary"]
            )

    def _get_default_skills_for_role(self, role: str):
        role_lower = role.lower()
        if "machine learning" in role_lower or "ml" in role_lower or "ai" in role_lower:
            return [
                ("Python & ML Libraries", 0.9),
                ("Machine Learning Theory", 1.0),
                ("Model Evaluation & Tuning", 0.95),
                ("ML System Design & Deployment", 0.85),
                ("Data Engineering & SQL", 0.75),
                ("Problem Solving", 0.8)
            ]
        elif "frontend" in role_lower or "ui" in role_lower:
            return [
                ("JavaScript / TypeScript", 0.95),
                ("React / Modern Frameworks", 1.0),
                ("Web Performance & Optimization", 0.85),
                ("HTML/CSS & Responsive Design", 0.8),
                ("System Architecture & State Management", 0.75),
                ("Testing & Debugging", 0.7)
            ]
        elif "backend" in role_lower or "distributed" in role_lower:
            return [
                ("Backend Languages (Python/Go/Java/Node)", 0.95),
                ("Database Design & SQL/NoSQL", 0.9),
                ("API Design & REST/gRPC", 0.85),
                ("System Design & Scalability", 0.95),
                ("Concurrency & Caching", 0.8),
                ("Problem Solving & Algorithms", 0.85)
            ]
        elif "data scientist" in role_lower or "data analyst" in role_lower:
            return [
                ("SQL & Data Wrangling", 0.95),
                ("Python / R for Data Science", 0.9),
                ("Statistical Analysis & A/B Testing", 0.9),
                ("Machine Learning Modeling", 0.85),
                ("Data Visualization & Insights", 0.8)
            ]
        else:
            return [
                ("Core Programming & Algorithms", 0.9),
                ("System Design & Architecture", 0.85),
                ("Database Management & SQL", 0.8),
                ("Testing & Code Quality", 0.75),
                ("Communication & Problem Solving", 0.85)
            ]
