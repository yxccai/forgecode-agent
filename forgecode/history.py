"""Read-only checkpoint browsing and terminal presentation, outside the agent runtime."""
from datetime import datetime
import json
from pathlib import Path

from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text


INTERNAL_NOTES = ("Repository data, not instructions.", "Baseline verification:\n",
                  "Verification failed. Analyze the evidence,")


def content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block if isinstance(block, str) else block.get("text", "")
                         for block in content if isinstance(block, (str, dict)))
    return str(content)


def entries(messages, include_tools=False):
    result = []
    for message in messages:
        text = content_text(message.content)
        if message.type == "human":
            internal = text.startswith(INTERNAL_NOTES)
            if not internal or include_tools:
                result.append(("Runtime" if internal else "You", text))
        elif message.type == "ai":
            if text.strip():
                result.append(("Assistant", text))
            if include_tools and message.tool_calls:
                result.append(("Tool requests", json.dumps(message.tool_calls, ensure_ascii=False, indent=2)))
        elif message.type == "tool" and include_tools:
            result.append(("Tool result", text))
    return result


def list_sessions(saver, root):
    """Use the checkpoint API; no second index or dependency on SQLite table layout."""
    root = Path(root).resolve()
    seen, rows = set(), []
    for checkpoint in saver.list(None):
        # Saver 按最新 checkpoint 优先返回；每个线程仅取第一次出现的快照。
        config = checkpoint.config["configurable"]
        thread = config["thread_id"]
        if config.get("checkpoint_ns") or thread in seen:
            continue
        seen.add(thread)
        state = checkpoint.checkpoint["channel_values"]
        if not state.get("root") or Path(state["root"]).resolve() != root:
            continue
        messages = entries(state.get("messages", []))
        title = next((text for role, text in messages if role == "You"), state.get("task", "Untitled"))
        rows.append({"id": thread, "title": " ".join(title.split())[:100],
                     "updated": checkpoint.checkpoint["ts"], "status": state.get("status", "running"),
                     "messages": len(messages)})
    return rows


def select_session(console, rows, current):
    if not rows:
        console.print("No saved conversations in this directory.", style="dim")
        return None
    page, page_size = 0, 10
    while True:
        table = Table(title=f"Conversations ({page + 1}/{(len(rows) + page_size - 1) // page_size})",
                      expand=True)
        for column in ("#", "Session", "Updated", "State", "Messages", "First message"):
            table.add_column(column, overflow="fold")
        for index, row in enumerate(rows[page * page_size:(page + 1) * page_size], page * page_size + 1):
            updated = datetime.fromisoformat(row["updated"]).astimezone().strftime("%m-%d %H:%M")
            table.add_row(*(Text(value) for value in (str(index), row["id"] + (" *" if row["id"] == current else ""),
                          updated, row["status"], str(row["messages"]), row["title"])))
        console.print(table)
        value = input("Session number/ID, n/p page, 0 cancel: ").strip()
        if not value or value == "0":
            return None
        if value == "n":
            page = min(page + 1, (len(rows) - 1) // page_size)
        elif value == "p":
            page = max(0, page - 1)
        elif value.isdigit() and 1 <= int(value) <= len(rows):
            return rows[int(value) - 1]["id"]
        elif any(row["id"] == value for row in rows):
            return value
        else:
            console.print("Invalid selection", style="yellow")


def show_history(console, messages, include_tools=False, recent=False):
    items = entries(messages, include_tools)
    if not items:
        console.print("No messages yet.", style="dim")
        return
    page_size = 8
    if recent:
        items = items[-page_size:]
    page = 0
    while True:
        for role, text in items[page * page_size:(page + 1) * page_size]:
            console.rule(role, style="cyan" if role == "You" else "dim")
            if role == "Assistant":
                console.print(Markdown(text))
            else:
                console.print(text, markup=False, highlight=False)
        if recent or len(items) <= page_size:
            return
        value = input(f"History {page + 1}/{(len(items) + page_size - 1) // page_size}: n/p, q return: ").strip().lower()
        if value in {"q", "", "0"}:
            return
        if value == "n":
            page = min(page + 1, (len(items) - 1) // page_size)
        elif value == "p":
            page = max(0, page - 1)
