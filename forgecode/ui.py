"""Presentation consumes events; agent cores never import Rich."""
from rich.console import Console


class Terminal:
    def __init__(self):
        self.console = Console()
        self.status = None
        self.streaming = False

    def __call__(self, event):
        kind = event["type"]
        if kind == "model_start":
            self.close()
            self.status = self.console.status("[cyan]Thinking...", spinner="dots")
            self.status.start()
        elif kind == "token":
            self.close()
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
        elif kind == "error":
            self.close()
            self.console.print(event["message"], style="red", markup=False)

    def close(self):
        if self.status:
            self.status.stop()
            self.status = None
