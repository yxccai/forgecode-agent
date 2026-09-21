import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from forgecode.config import Config
from v0.agent import run
from v0.model import Model
from v0.tools import Tools


class ProtocolTest(unittest.TestCase):
    def test_real_sse_and_repository_tools(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(request)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                if len(requests) == 1:
                    deltas = [{"tool_calls": [{"index": 0, "id": "call_1", "type": "function",
                               "function": {"name": "read_file", "arguments": '{"path":'}}]},
                              {"tool_calls": [{"index": 0, "function": {"arguments": '"app.py"}'}}]}]
                else:
                    deltas = [{"content": "app.py:1 defines add."}]
                for delta in deltas:
                    self.wfile.write(("data: " + json.dumps({"choices": [{"delta": delta}]}) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                Path(folder, "app.py").write_text("def add(a, b): return a + b\n")
                config = Config(base_url=f"http://127.0.0.1:{server.server_port}/v1", model="fixture")
                events = []
                answer = run("Find add", Model(config), Tools(folder), events.append)
                self.assertEqual(answer, "app.py:1 defines add.")
                self.assertIn("def add", requests[1]["messages"][-1]["content"])
                self.assertEqual(events[-1]["steps"], 2)
                self.assertTrue(any(e["type"] == "token" for e in events))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_tool_boundaries_and_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            tools = Tools(folder)
            for path in ("../outside", ".env", ".git/config", "config.local.json"):
                self.assertIn("error", tools.execute("read_file", {"path": path}))
            Path(folder, "escape").symlink_to("/etc/passwd")
            self.assertIn("error", tools.execute("read_file", {"path": "escape"}))
            self.assertIn("error", tools.execute("unknown", {}))

    def test_budget(self):
        class Forever:
            def complete(self, *args):
                return {"role": "assistant", "content": "", "tool_calls": [
                    {"id": "x", "function": {"name": "list_files", "arguments": "{}"}}]}
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "budget"):
                run("loop", Forever(), Tools(folder), lambda e: None, max_steps=2)


if __name__ == "__main__":
    unittest.main()
