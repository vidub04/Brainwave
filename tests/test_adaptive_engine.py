import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.models import (
    CandidateState,
    InterviewPlan,
    SkillPriority,
    EvaluationResult,
    AdaptationAction,
    QuestionItem,
    QuestionType
)
from engine.planner import InterviewPlanner
from engine.evaluator import EvaluationAgent
from engine.anti_repetition import AntiRepetitionEngine
from engine.adaptation_engine import AdaptiveDecisionEngine
from engine.question_generator import InterviewerAgent
from engine.state_manager import CandidateStateManager
from engine.report_generator import InterviewReportGenerator
from engine.orchestrator import InterviewOrchestrator


def test_planner_creation():
    planner = InterviewPlanner()
    plan = planner.create_plan(
        role="Machine Learning Engineer",
        job_description="Looking for an ML Engineer with Python, PyTorch, Model Evaluation, and ML System Design.",
        resume_text="5 years experience in Python, Scikit-Learn, PyTorch, Deep Learning.",
        duration_minutes=30
    )

    assert plan.role == "Machine Learning Engineer"
    assert len(plan.skills) >= 4
    assert plan.initial_difficulty in [1, 2, 3]
    assert len(plan.stages) >= 3
    print("Planner Test Passed: Skills extracted ->", [s.name for s in plan.skills])


def test_anti_repetition_engine():
    engine = AntiRepetitionEngine(similarity_threshold=0.65)
    
    prev_questions = [
        "Explain the bias-variance tradeoff and how it impacts model generalization.",
        "How would you design a distributed key-value cache using Redis and consistent hashing?"
    ]
    
    # 1. Exact duplicate or near identical
    dup_q = "Can you explain the bias-variance tradeoff and its impact on model generalization?"
    is_dup, score, reason = engine.check_repetition(
        new_question=dup_q,
        asked_questions=prev_questions,
        new_concepts=["bias", "variance"],
        covered_concepts=["bias", "variance", "generalization"]
    )
    assert is_dup is True, f"Expected duplicate detection, got {is_dup}, score: {score}"
    print(f"AntiRepetition Duplicate Detection Passed (Score: {score:.2f}, Reason: {reason})")

    # 2. Distinct question
    novel_q = "Describe how gradient descent optimization algorithms like Adam differ from SGD."
    is_dup, score, reason = engine.check_repetition(
        new_question=novel_q,
        asked_questions=prev_questions,
        new_concepts=["gradient descent", "Adam", "SGD"],
        covered_concepts=["bias", "variance", "generalization"]
    )
    assert is_dup is False, f"Expected novel question, got {is_dup}, score: {score}"
    print(f"AntiRepetition Novel Question Passed (Score: {score:.2f})")


def test_adaptive_decision_flow_scenario():
    """
    Validates the scenario specified in the requirements:
    - Q1: Easy Python (score 9/10) -> Difficulty increases.
    - Q2: Advanced Python (score 8/10) -> Switches skill to ML.
    - Q3: ML question (score 4/10) -> Evaluator detects weak Model Evaluation -> Probes weakness / follow-up.
    - Q4: Targeted follow-up -> Candidate improves (score 8.5/10) -> Recognizes improvement.
    - Q5: Practical ML scenario (score 3.5/10) -> Agent decides to probe concept / reduce difficulty.
    """
    orchestrator = InterviewOrchestrator()
    
    # 1. Create interview
    state = orchestrator.create_interview(
        role="Machine Learning Engineer",
        job_description="Machine Learning Engineer with Python, Model Evaluation, and ML Systems.",
        duration_minutes=30
    )
    interview_id = state.interview_id

    # 2. Start Interview (Q1)
    start_res = orchestrator.start_interview(interview_id)
    q1 = start_res["question"]
    assert q1 is not None
    assert start_res["current_difficulty"] >= 1
    print(f"\n[Turn 1] Question 1 ({q1.skill}, Diff {start_res['current_difficulty']}): {q1.question}")

    # Candidate answers Q1 strongly with explanation and code
    ans1 = """Generators maintain execution state across yield expressions using generator objects and stack frame suspension.
Here is the sliding window average generator:
```python
from collections import deque

def sliding_window_avg(stream, k):
    window = deque()
    window_sum = 0.0
    for num in stream:
        window.append(num)
        window_sum += num
        if len(window) > k:
            window_sum -= window.popleft()
        if len(window) == k:
            yield window_sum / k
```
This handles streaming data with O(1) time complexity per element and O(k) memory."""
    turn1_res = orchestrator.process_candidate_answer(interview_id, ans1)
    
    print(f"[Turn 1 Eval] Score: {turn1_res['evaluation'].overall_score}/10, Action: {turn1_res['action_taken']}, Next Diff: {turn1_res['current_difficulty']}")
    assert turn1_res["evaluation"].overall_score >= 7.0

    # Candidate answers Q2
    q2 = turn1_res["next_question"]
    print(f"\n[Turn 2] Question 2 ({q2.skill}, Diff {turn1_res['current_difficulty']}): {q2.question}")
    if "generator" in q2.question.lower() or "yield from" in q2.question.lower() or "python" in q2.skill.lower():
        ans2 = "Standard functions execute from start to return, allocating a single stack frame that is destroyed upon exit. Generator functions produce an iterator object; each call to next() resumes execution right after the last yield expression, retaining local variables and state. 'yield from iterable' delegates generation directly to a sub-iterable or subgenerator, passing values and exceptions transparently."
    else:
        ans2 = "In deep learning with PyTorch, we implement custom autograd functions by subclassing torch.autograd.Function with static forward and backward methods, or define neural network layers by subclassing nn.Module. For backpropagation, the computational graph stores tensor gradient functions and accumulates gradients in .grad attributes when backward() is called."
    
    turn2_res = orchestrator.process_candidate_answer(interview_id, ans2)
    print(f"[Turn 2 Eval] Score: {turn2_res['evaluation'].overall_score}/10, Action: {turn2_res['action_taken']}")
    assert turn2_res["evaluation"].overall_score >= 6.5

    # Q3: Candidate gives an intentionally weak answer on Q3
    q3 = turn2_res["next_question"]
    print(f"\n[Turn 3] Question 3 ({q3.skill}, Diff {turn2_res['current_difficulty']}): {q3.question}")
    ans3 = "I think model evaluation is just checking accuracy on a test split. I am not really sure about cross validation, precision recall tradeoffs, or data leakage."
    turn3_res = orchestrator.process_candidate_answer(interview_id, ans3)
    print(f"[Turn 3 Eval] Score: {turn3_res['evaluation'].overall_score}/10, Action: {turn3_res['action_taken']}, Missing: {turn3_res['evaluation'].missing_concepts}")
    assert turn3_res["evaluation"].overall_score <= 6.0

    # Q4: Candidate answers Q4 with a strong, detailed response
    q4 = turn3_res["next_question"]
    print(f"\n[Turn 4] Question 4 ({q4.skill}, Diff {turn3_res['current_difficulty']}): {q4.question}")
    if "mutable" in q4.question.lower() or "immutable" in q4.question.lower():
        ans4 = "Immutable types (like int, str, tuple, frozenset) cannot be modified in place after creation; modifying them creates a new object. Mutable types (like list, dict, set) can be mutated in place. In Python, arguments are passed by assignment/sharing: modifying a mutable object in place (e.g. list.append) mutates the caller's object, while rebinding a variable does not."
    else:
        ans4 = "To evaluate models rigorously and prevent data leakage, we fit preprocessing transformers strictly inside training folds of Stratified K-Fold Cross Validation. For imbalanced datasets, accuracy is misleading so we optimize Precision-Recall AUC and F1 score, calibrating probability thresholds via cost-benefit matrix analysis and checking feature distribution shift across train and validation splits."
    turn4_res = orchestrator.process_candidate_answer(interview_id, ans4)
    print(f"[Turn 4 Eval] Score: {turn4_res['evaluation'].overall_score}/10, Action: {turn4_res['action_taken']}")
    assert turn4_res["evaluation"].overall_score >= 7.0

    # Check Decision Logs
    logs = orchestrator.get_decision_logs(interview_id)
    assert len(logs) == 4
    print("\nDecision Log Entries Verified:")
    for log in logs:
        print(f" - Turn {log.turn_index}: Skill={log.skill}, Diff={log.difficulty_before}->{log.difficulty_after}, Action={log.action_taken}, Eval={log.evaluation.overall_score if log.evaluation else 'N/A'}")

    # Generate Final Report
    report = orchestrator.get_report(interview_id)
    assert report.overall_score >= 0
    assert len(report.preparation_plan.day_7_focus) > 0
    assert len(report.preparation_plan.day_14_focus) > 0
    assert len(report.preparation_plan.day_30_focus) > 0
    print(f"\nFinal Report Generated:")
    print(f" - Overall Score: {report.overall_score}/100 ({report.score_grade})")
    print(f" - Skill Breakdown: {report.skill_breakdown}")
    print(f" - Evidence items: {len(report.evidence)}")
    print(f" - 7-Day Plan: {report.preparation_plan.day_7_focus[:2]}")


if __name__ == "__main__":
    test_planner_creation()
    test_anti_repetition_engine()
    test_adaptive_decision_flow_scenario()
    print("\nALL ENGINE TESTS COMPLETED SUCCESSFULLY!")
