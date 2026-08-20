from typing import List, Optional
from .models import CodingTestCase, CodingQuestion

CODING_QUESTION_BANK: List[CodingQuestion] = [
    CodingQuestion(
        id="two_sum",
        skill="Arrays & Hashing",
        role_tags=["Software Engineer", "Backend Developer", "Full Stack Developer"],
        difficulty=2,
        title="Two Sum",
        prompt=(
            "Given an array of integers `nums` and an integer `target`, return the "
            "indices of the two numbers that add up to `target`. Assume exactly one "
            "solution exists and you may not use the same element twice."
        ),
        function_name="two_sum",
        function_signature="def two_sum(nums: list[int], target: int) -> list[int]:",
        starter_code="def two_sum(nums, target):\n    # your code here\n    pass",
        test_cases=[
            CodingTestCase(input_args=[[2, 7, 11, 15], 9], expected_output=[0, 1]),
            CodingTestCase(input_args=[[3, 2, 4], 6], expected_output=[1, 2]),
            CodingTestCase(input_args=[[3, 3], 6], expected_output=[0, 1], is_hidden=True),
        ],
        expected_concepts=["hash map", "time complexity", "single pass"],
    ),
    CodingQuestion(
        id="valid_parens",
        skill="Stacks",
        role_tags=[],  # empty = applies to all roles
        difficulty=2,
        title="Valid Parentheses",
        prompt="Given a string containing just '()[]{}' , determine if the input is valid (properly closed and nested).",
        function_name="is_valid",
        function_signature="def is_valid(s: str) -> bool:",
        starter_code="def is_valid(s):\n    # your code here\n    pass",
        test_cases=[
            CodingTestCase(input_args=["()"], expected_output=True),
            CodingTestCase(input_args=["()[]{}"], expected_output=True),
            CodingTestCase(input_args=["(]"], expected_output=False),
            CodingTestCase(input_args=["([)]"], expected_output=False, is_hidden=True),
        ],
        expected_concepts=["stack", "matching brackets"],
    ),
    # ... add more per skill/role: BFS/DFS, DP, LRU cache, sliding window, etc.
]


def get_coding_question(
    skill: str,
    role: str,
    difficulty: int,
    exclude_ids: List[str]
) -> Optional[CodingQuestion]:
    """Picks the best-fit unused question for this skill/role/difficulty."""
    candidates = [
        q for q in CODING_QUESTION_BANK
        if q.id not in exclude_ids
        and (not q.role_tags or role in q.role_tags)
    ]
    if not candidates:
        candidates = [q for q in CODING_QUESTION_BANK if q.id not in exclude_ids]
    if not candidates:
        return None
    # Prefer closest difficulty, then loosely match skill name
    candidates.sort(key=lambda q: (abs(q.difficulty - difficulty), skill.lower() not in q.skill.lower()))
    return candidates[0]


def get_coding_question_by_id(qid: str) -> Optional[CodingQuestion]:
    return next((q for q in CODING_QUESTION_BANK if q.id == qid), None)

def load_bank_from_supabase(supabase_client) -> List[CodingQuestion]:
    try:
        rows = supabase_client.table("coding_questions").select("*").execute().data or []
        return [CodingQuestion(**{**r, "test_cases": [CodingTestCase(**tc) for tc in r["test_cases"]]}) for r in rows]
    except Exception:
        return []