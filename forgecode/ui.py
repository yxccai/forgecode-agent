"""Presentation consumes events; agent cores never import Rich."""
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown


class Terminal:
    def __init__(self):
        self.console = Console()
        self.status = None
        self.streaming = False
        self.live = None
        self.text = ""

    def __call__(self, event):
        kind = event["type"]
        if kind == "model_start":
            self.close()
            self.text = ""
            self.status = self.console.status("[cyan]Thinking...", spinner="dots")
            self.status.start()
        elif kind == "token":
            if self.status:
                self.status.stop()
                self.status = None
            self.text += event["text"]
            if self.console.is_terminal:
                if self.live is None:
                    self.live = Live(console=self.console, refresh_per_second=12,
                                     vertical_overflow="visible")
                    self.live.start()
                self.live.update(Markdown(self.text))
            else:
                self.console.print(event["text"], end="", markup=False, highlight=False)
            self.streaming = True
        elif kind == "model_end":
            self.close()
            if self.streaming:
                self.console.print()
                self.streaming = False
        elif kind == "tool_start":
            self.console.print(f"  > {event['name']}", style="cyan", markup=False)
        elif kind == "tool_end":
            self.console.print(event["output"][:600], style="dim", markup=False)
        elif kind == "verification":
            passed = event["exit_code"] == 0 and not event["timed_out"]
            self.console.print(f"{event['phase']} verification: {'PASS' if passed else 'FAIL'}",
                               style="green" if passed else "red", markup=False)
            self.console.print(event["output"][:1800], style="dim", markup=False)
        elif kind == "finish":
            self.console.print(f"{event['status']} | steps={event.get('steps', 0)} | "
                               f"tools={event.get('tool_calls', 0)} | tokens={event.get('tokens', 0)}",
                               style="cyan", markup=False)
        elif kind == "error":
            self.close()
            self.console.print(event["message"], style="red", markup=False)

    def close(self):
        if self.live:
            self.live.stop()
            self.live = None
        if self.status:
            self.status.stop()
            self.status = None
