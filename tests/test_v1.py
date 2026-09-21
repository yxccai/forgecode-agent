import json
from pathlib import Path
import tempfile
import unittest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from v1.agent import context, run
from v1.tools import Tools, command


class CodingTest(unittest.TestCase):
    def test_context_preserves_tool_groups(self):
        messages = [SystemMessage("system"), HumanMessage("task"),
                    AIMessage(content="x" * 200, tool_calls=[{"name": "read_file", "args": {}, "id": "old"}]),
                    ToolMessage(content="old", tool_call_id="old"),
                    AIMessage(content="", tool_calls=[{"name": "read_file", "args": {}, "id": "new"}]),
                    ToolMessage(content="new", tool_call_id="new")]
        selected = context(messages, limit=150)
        self.assertEqual([m.type for m in selected], ["system", "human", "ai", "tool"])
        self.assertEqual(selected[-1].tool_call_id, "new")

    def test_edit_ambiguity_and_permission(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "app.py")
            path.write_text("bad bad")
            tools = Tools(folder)
            self.assertIn("error", tools.execute("edit_file", {"path": "app.py", "old": "bad", "new": "ok"}))
            self.assertEqual(path.read_text(), "bad bad")
            self.assertIn("denied", tools.execute("run_command", {"argv": ["true"]}))
            self.assertIn("error", tools.execute("edit_file", {"path": "../escape", "old": "", "new": "x"}))

    def test_actual_fix_and_test_loop(self):
        calls = [
            ("read_file", {"path": "app.py"}),
            ("edit_file", {"path": "app.py", "old": "a - b", "new": "a + b"}),
            ("run_command", {"argv": ["python3", "-m", "unittest", "discover"]}),
        ]

        class Script:
            def complete(self, messages, tools, emit):
                if calls:
                    name, args = calls.pop(0)
                    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": name}])
                return AIMessage(content="Fixed and tested")

        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "app.py").write_text("def add(a, b): return a - b\n")
            Path(folder, "test_app.py").write_text(
                "import unittest\nfrom app import add\nclass Test(unittest.TestCase):\n"
                " def test_add(self): self.assertEqual(add(2, 3), 5)\n")
            events = []
            run("fix", Script(), Tools(folder, lambda argv: True), events.append)
            outputs = [e for e in events if e["type"] == "tool_end" and e["name"] == "run_command"]
            self.assertEqual(json.loads(outputs[0]["output"])["exit_code"], 0)
            self.assertIn("a + b", Path(folder, "app.py").read_text())

    def test_timeout(self):
        with tempfile.TemporaryDirectory() as folder:
            result = command(folder, ["python3", "-c", "import time; time.sleep(10)"], timeout=.05)
            self.assertTrue(result["timed_out"])
            self.assertNotEqual(result["exit_code"], 0)
