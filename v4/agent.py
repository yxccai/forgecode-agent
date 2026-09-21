import json

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from v1.tools import command
from v2.agent import State as BaseState, initial as base_initial
from v3.agent import Runtime as RepositoryRuntime


class State(BaseState, total=False):
    verify_argv: list[str]
    verification: dict
    baseline: dict
    repairs: int
    max_repairs: int
    verification_enabled: bool


def initial(task, root, verify, max_steps=20, max_calls=60, max_tokens=0,
            max_repairs=3, verification=True):
    return {**base_initial(task, root, max_steps, max_calls, max_tokens), "verify_argv": verify,
            "repairs": 0, "max_repairs": max_repairs, "verification_enabled": verification,
            "verification": {}, "baseline": {}}


class Runtime(RepositoryRuntime):
    def tools_node(self, state):
        if state["calls"] >= state["max_calls"]:
            return {"status": "budget_exhausted"}
        call = state["pending"][state["cursor"]]
        if call["name"] == "run_command":
            # 恢复可能重新进入本节点；危险副作用必须位于 interrupt 之后。
            decision = interrupt({"kind": "command", "argv": call["args"].get("argv"),
                                  "cwd": str(self.tools.root), "tool_call_id": call["id"]})
            self.emit({"type": "approval", "approved": decision is True, "call_id": call["id"]})
            if decision is not True:
                output = json.dumps({"error": "Command denied by user"})
                self.emit({"type": "tool_end", "name": call["name"], "output": output})
                return {"messages": [ToolMessage(content=output, tool_call_id=call["id"])],
                        "calls": state["calls"] + 1, "cursor": state["cursor"] + 1}
            old = self.tools.approve
            # 本次批准只放行当前 argv，并在 finally 恢复策略，避免授权扩大到后续命令。
            self.tools.approve = lambda argv: argv == call["args"].get("argv")
            try:
                return super().tools_node(state)
            finally:
                self.tools.approve = old
        return super().tools_node(state)

    def baseline(self, state):
        if not state["verification_enabled"]:
            return {}
        result = command(self.tools.root, state["verify_argv"])
        self.emit({"type": "verification", "phase": "baseline", **result})
        return {"baseline": result, "messages": [HumanMessage("Baseline verification:\n" + json.dumps(result))]}

    def route_act(self, state):
        # 模型的“回答结束”只触发验证；verified 必须由运行时的实际命令结果授予。
        if state["status"] == "running":
            return "tools"
        if state["status"] == "answered" and state["verification_enabled"]:
            return "verify"
        return "finish"

    def verify(self, state):
        result = command(self.tools.root, state["verify_argv"])
        self.emit({"type": "verification", "phase": "final", **result})
        if result["exit_code"] == 0 and not result["timed_out"]:
            return {"verification": result, "status": "verified"}
        if state["repairs"] >= state["max_repairs"] or self.budget(state):
            return {"verification": result, "status": "verification_failed"}
        return {"verification": result, "status": "running", "repairs": state["repairs"] + 1,
                # 失败输出进入消息历史，让下一次 Act 基于环境证据修复。
                "messages": [HumanMessage("Verification failed. Analyze the evidence, repair the code, "
                                          "and finish for another verification.\n" + json.dumps(result))]}

    def route_verify(self, state):
        return "act" if state["status"] == "running" else "finish"

    def finish(self, state):
        if state["status"] == "verified" and self.tools.memory:
            from v4.workspace import git
            changed = git(self.tools.root, "diff", "--name-only", "HEAD").splitlines()
            sources = [p for p in changed if (self.tools.root / p).is_file()][:10]
            if sources:
                self.tools.memory.remember("Verified task: " + state["task"][:1600], sources,
                                           kind="episodic", confidence=.8)
        self.emit({"type": "diff", "output": self.tools.git_diff()})
        return super().finish(state)

    def build(self, saver, pause_after_tool=False):
        graph = StateGraph(State)
        for name, fn in (("plan", self.plan), ("baseline", self.baseline), ("act", self.act),
                         ("tools", self.tools_node), ("verify", self.verify), ("finish", self.finish)):
            graph.add_node(name, fn)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "baseline")
        graph.add_edge("baseline", "act")
        graph.add_conditional_edges("act", self.route_act, ["tools", "verify", "finish"])
        graph.add_conditional_edges("tools", self.route_tools, ["tools", "act", "finish"])
        graph.add_conditional_edges("verify", self.route_verify, ["act", "finish"])
        graph.add_edge("finish", END)
        return graph.compile(checkpointer=saver, interrupt_after=["tools"] if pause_after_tool else [])
