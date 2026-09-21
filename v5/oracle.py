"""Independent evaluation: source is copied outside the agent workspace before testing."""
import ast
import json
from pathlib import Path
import tempfile

from v1.tools import command


def function_name(source):
    return next(node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef))


def test_source(task, cases=None):
    selected = task.cases if cases is None else cases
    lines = ["import unittest, copy", f"from subject import {function_name(task.solution)} as function",
             "class Acceptance(unittest.TestCase):"]
    for index, (argument, expected) in enumerate(selected):
        lines += [f"    def test_{index}(self):", f"        value = {argument!r}", "        before = copy.deepcopy(value)"]
        if isinstance(expected, dict) and "raises" in expected:
            lines += [f"        with self.assertRaises({expected['raises']}):", "            function(value)"]
        else:
            lines += [f"        self.assertEqual(function(value), {expected!r})"]
        if task.constraint == "no_mutation":
            lines += ["        self.assertEqual(value, before)"]
    return "\n".join(lines) + "\n"


def evaluate_source(task, source):
    # 完整用例在 Agent 工作区之外运行，防止公开测试修改直接决定分数；不是安全沙箱。
    with tempfile.TemporaryDirectory(prefix="forgecode-oracle-") as root:
        Path(root, "subject.py").write_text(source)
        Path(root, "test_acceptance.py").write_text(test_source(task))
        runner = (
            "import json, unittest\n"
            "suite=unittest.defaultTestLoader.discover('.', pattern='test_acceptance.py')\n"
            "result=unittest.TestResult()\nsuite.run(result)\n"
            "print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),"
            "'errors':len(result.errors)}))\n")
        Path(root, "oracle.py").write_text(runner)
        result = command(root, ["python3", "oracle.py"], timeout=10)
        try:
            scores = json.loads(result["output"].splitlines()[-1]) if result["exit_code"] == 0 else {}
        except (json.JSONDecodeError, IndexError):
            scores = {}
        total = len(task.cases)
        passed = max(0, scores.get("tests", 0) - scores.get("failures", 0) - scores.get("errors", 0))
        structural = True
        try:
            tree = ast.parse(source)
            if task.constraint in {"no_loops", "join"}:
                structural = not any(isinstance(n, (ast.For, ast.While, ast.AsyncFor)) for n in ast.walk(tree))
            if task.constraint == "join":
                structural &= any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                  and n.func.attr == "join" for n in ast.walk(tree))
        except SyntaxError:
            structural = False
        return {"passed": passed, "total": total, "structural": structural,
                # 必须发现预期数量的用例且满足结构约束，不能把零测试当成功。
                "success": passed == total and scores.get("tests") == total and structural,
                "output": result["output"][:2000]}
