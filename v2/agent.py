from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from v1.agent import SYSTEM, context


class State(TypedDict, total=False):
    # reducer 合并节点返回的消息增量；其它普通字段通常以新值覆盖。
    messages: Annotated[list[BaseMessage], add_messages]
    task: str
    root: str
    plan: str
    steps: int
    calls: int
    tokens: int
    max_steps: int
    max_calls: int
    max_tokens: int
    pending: list[dict]
    cursor: int
    status: str


def initial(task, root, max_steps=20, max_calls=60, max_tokens=0):
    return {"messages": [SystemMessage(SYSTEM), HumanMessage(task)], "task": task,
            "root": str(root), "steps": 0, "calls": 0, "tokens": 0,
            "max_steps": max_steps, "max_calls": max_calls, "max_tokens": max_tokens,
            "plan": "", "pending": [], "cursor": 0, "status": "running"}


class Runtime:
    def __init__(self, model, tools, emit, planning=True):
        self.model, self.tools, self.emit, self.planning = model, tools, emit, planning

    def budget(self, state):
        # usage 在响应后才得知，所以 token 是软上限；工具次数在执行前逐次检查。
        return (state["steps"] >= state["max_steps"] or state["calls"] >= state["max_calls"] or
                (state["max_tokens"] > 0 and state["tokens"] >= state["max_tokens"]))

    def plan(self, state):
        # 计划是一次独立模型调用，也消耗 steps；不是免费或保证正确的隐藏推理。
        if not self.planning:
            return {"plan": ""}
        answer = self.model.complete([
            SystemMessage("Make a concise, actionable coding plan of at most 3 steps. Include verification. "
                          "Do not invent repository facts. This is planning only, do not claim execution."),
            HumanMessage(state["task"])], [], self.emit)
        self.emit({"type": "plan", "text": str(answer.content)})
        usage = (answer.usage_metadata or {}).get("total_tokens", 0)
        return {"plan": str(answer.content)[:4000], "steps": state["steps"] + 1,
                "tokens": state["tokens"] + usage}

    def act(self, state):
        if self.budget(state):
            return {"status": "budget_exhausted"}
        messages = context(state["messages"])
        messages = [SystemMessage(SYSTEM + "\nCurrent plan:\n" + state["plan"]), *messages[1:]]
        self.emit({"type": "context", "characters": sum(len(str(m.content)) for m in messages)})
        answer = self.model.complete(messages, self.tools.items, self.emit)
        if answer.invalid_tool_calls:
            raise RuntimeError("Provider returned malformed tool arguments")
        self.emit({"type": "decision", "step": state["steps"] + 1,
                   "tool_calls": answer.tool_calls, "content": answer.content})
        return {"messages": [answer], "steps": state["steps"] + 1,
                "tokens": state["tokens"] + (answer.usage_metadata or {}).get("total_tokens", 0),
                "pending": answer.tool_calls, "cursor": 0,
                "status": "running" if answer.tool_calls else "answered"}

    def tools_node(self, state):
        # 一个节点只执行一个工具，pending/cursor 让批量调用之间也有恢复边界。
        if state["calls"] >= state["max_calls"]:
            return {"status": "budget_exhausted"}
        call = state["pending"][state["cursor"]]
        self.emit({"type": "tool_start", "name": call["name"], "args": call["args"]})
        output = self.tools.execute(call["name"], call["args"])
        self.emit({"type": "tool_end", "name": call["name"], "output": output})
        return {"messages": [ToolMessage(content=output, tool_call_id=call["id"])],
                # 只返回变化的字段，框架负责合并并持久化，不必返回整个 State。
                "calls": state["calls"] + 1, "cursor": state["cursor"] + 1}

    def route_act(self, state):
        return "tools" if state["status"] == "running" else "finish"

    def route_tools(self, state):
        if state["status"] != "running":
            return "finish"
        return "tools" if state["cursor"] < len(state["pending"]) else "act"

    def finish(self, state):
        self.emit({"type": "finish", "status": state["status"], "steps": state["steps"],
                   "tool_calls": state["calls"], "tokens": state["tokens"]})
        return {}

    def build(self, saver, pause_after_tool=False):
        # 图描述控制流；SqliteSaver 保存执行状态。工具副作用与 checkpoint 不是原子事务。
        graph = StateGraph(State)
        graph.add_node("plan", self.plan)
        graph.add_node("act", self.act)
        graph.add_node("tools", self.tools_node)
        graph.add_node("finish", self.finish)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "act")
        graph.add_conditional_edges("act", self.route_act, ["tools", "finish"])
        graph.add_conditional_edges("tools", self.route_tools, ["tools", "act", "finish"])
        graph.add_edge("finish", END)
        return graph.compile(checkpointer=saver, interrupt_after=["tools"] if pause_after_tool else [])
