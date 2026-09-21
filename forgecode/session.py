"""Interactive turns reuse the versioned runtime; presentation lives elsewhere."""
import json
from pathlib import Path

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command, interrupt
from v4.agent import Runtime, initial
from v4.tools import Tools


class InteractiveRuntime(Runtime):
    def tools_node(self, state):
        call = state["pending"][state["cursor"]]
        if call["name"] == "edit_file" and state["calls"] < state["max_calls"]:
            approved = interrupt({"kind": "edit", "cwd": str(self.tools.root), **call["args"]})
            if approved is not True:
                return {"messages": [ToolMessage(content=json.dumps({"error": "Edit denied by user"}),
                                                tool_call_id=call["id"])],
                        "calls": state["calls"] + 1, "cursor": state["cursor"] + 1}
        return super().tools_node(state)


class Session:
    def __init__(self, root, thread, saver, model, emit, max_steps=20):
        self.root = Path(root).resolve()
        self.options = {"configurable": {"thread_id": thread}, "recursion_limit": 1000}
        self.runtime = InteractiveRuntime(model, Tools(self.root), emit, planning=False)
        self.graph = self.runtime.build(saver)
        self.max_steps = max_steps

    def snapshot(self):
        return self.graph.get_state(self.options)

    def turn(self, text, verify, approve, resume=False):
        snapshot = self.snapshot()
        if snapshot.values and snapshot.values["root"] != str(self.root):
            raise ValueError("Session repository mismatch")
        if resume:
            if not snapshot.next:
                raise ValueError("No interrupted turn to resume")
            payload = None
        else:
            if snapshot.next:
                raise ValueError("Use /resume for the interrupted turn or /new to start over")
            if snapshot.values and snapshot.values["status"] not in {"answered", "verified", "verification_failed"}:
                raise ValueError("Previous turn exhausted its budget; use /new")
            payload = initial(text, str(self.root), verify, max_steps=self.max_steps,
                              verification=bool(verify))
            if snapshot.values:
                payload["messages"] = [HumanMessage(text)]
        while True:
            pending = [item for task in self.snapshot().tasks for item in task.interrupts]
            if pending:
                payload = Command(resume=approve(pending[0].value))
            result = self.graph.invoke(payload, self.options)
            if not result.get("__interrupt__"):
                return result
            payload = None
