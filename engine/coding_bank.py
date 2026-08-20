from typing import List, Optional
from .models import CodingTestCase, CodingQuestion


##question bank default
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



##calling coding questions

def get_coding_question(
    skill: str,
    role: str,
    difficulty: int,
    exclude_ids: List[str],
    supabase_client=None
) -> Optional[CodingQuestion]:

    # Start with fallback questions
    question_bank = CODING_QUESTION_BANK.copy()

    # Try loading questions from Supabase
    if supabase_client:
        supabase_questions = load_bank_from_supabase(supabase_client)

        # If Supabase worked, use those questions
        if supabase_questions:
            question_bank = supabase_questions

    candidates = [
        q for q in question_bank
        if q.id not in exclude_ids
        and (not q.role_tags or role in q.role_tags)
    ]

    # If no role match, ignore role
    if not candidates:
        candidates = [
            q for q in question_bank
            if q.id not in exclude_ids
        ]

    if not candidates:
        return None

    # Closest difficulty first, then skill match
    candidates.sort(
        key=lambda q: (
            abs(q.difficulty - difficulty),
            skill.lower() not in q.skill.lower()
        )
    )

    return candidates[0]

'''
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

'''

def get_coding_question_by_id(
    qid: str,
    supabase_client=None
) -> Optional[CodingQuestion]:

    # Try Supabase first
    if supabase_client:
        try:
            row = (
                supabase_client
                .table("coding_questions")
                .select("*")
                .eq("id", qid)
                .maybe_single()
                .execute()
                .data
            )

            if row:
                return CodingQuestion(
                    id=row["id"],
                    skill=row["skill"],
                    role_tags=row.get("role_tags", []),
                    difficulty=row.get("difficulty", 3),
                    title=row["title"],
                    prompt=row["prompt"],
                    function_name=row["function_name"],
                    function_signature=row["function_signature"],
                    starter_code=row["starter_code"],
                    test_cases=[
                        CodingTestCase(**tc)
                        for tc in row.get("test_cases", [])
                    ],
                    expected_concepts=row.get("expected_concepts", [])
                )

        except Exception as e:
            print(f"Failed to fetch coding question from Supabase: {e}")

    # Fallback
    return next(
        (q for q in CODING_QUESTION_BANK if q.id == qid),
        None
    )

def load_bank_from_supabase(supabase_client) -> List[CodingQuestion]:
    try:
        rows = (
            supabase_client
            .table("coding_questions")
            .select("*")
            .execute()
            .data or []
        )

        return [
            CodingQuestion(
                id=r["id"],
                skill=r["skill"],
                role_tags=r.get("role_tags", []),
                difficulty=r.get("difficulty", 3),
                title=r["title"],
                prompt=r["prompt"],
                function_name=r["function_name"],
                function_signature=r["function_signature"],
                starter_code=r["starter_code"],
                test_cases=[
                    CodingTestCase(**tc)
                    for tc in r.get("test_cases", [])
                ],
                expected_concepts=r.get("expected_concepts", []),
            )
            for r in rows
        ]

    except Exception as e:
        print(f"Failed to load coding questions from Supabase: {e}")
        return []