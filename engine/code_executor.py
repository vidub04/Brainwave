import subprocess
import sys
import json
import tempfile
import os
from .models import CodingQuestion, CodeExecutionResult, TestCaseResult

RUNNER_TEMPLATE = '''
import json, sys

{candidate_code}

test_cases = json.loads(sys.argv[1])
results = []
for tc in test_cases:
    try:
        actual = {function_name}(*tc["input_args"])
        results.append({{"actual_output": actual, "error": None}})
    except Exception as e:
        results.append({{"actual_output": None, "error": str(e)}})

print(json.dumps(results))
'''

class CodeExecutor:
    def __init__(self, timeout_seconds: int = 5):
        self.timeout = timeout_seconds

    def run(self, candidate_code: str, question: CodingQuestion) -> CodeExecutionResult:
        script = RUNNER_TEMPLATE.format(
            candidate_code=candidate_code,
            function_name=question.function_name
        )
        test_payload = json.dumps([{"input_args": tc.input_args} for tc in question.test_cases])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            proc = subprocess.run(
                [sys.executable, script_path, test_payload],
                capture_output=True, text=True, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            return CodeExecutionResult(
                total_count=len(question.test_cases),
                runtime_error="Execution timed out (possible infinite loop)."
            )
        finally:
            os.unlink(script_path)

        if proc.returncode != 0:
            return CodeExecutionResult(
                total_count=len(question.test_cases),
                runtime_error=proc.stderr[-800:]
            )

        try:
            raw_results = json.loads(proc.stdout.strip())
        except Exception:
            return CodeExecutionResult(
                total_count=len(question.test_cases),
                runtime_error="Could not parse execution output."
            )

        results, passed_count = [], 0
        for tc, r in zip(question.test_cases, raw_results):
            passed = r["error"] is None and r["actual_output"] == tc.expected_output
            passed_count += int(passed)
            results.append(TestCaseResult(
                input_args=tc.input_args,
                expected_output=tc.expected_output,
                actual_output=r["actual_output"],
                passed=passed,
                error=r["error"]
            ))

        return CodeExecutionResult(
            all_passed=passed_count == len(question.test_cases),
            passed_count=passed_count,
            total_count=len(question.test_cases),
            results=results
        )