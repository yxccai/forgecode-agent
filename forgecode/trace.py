import json
import time
from pathlib import Path


class Trace:
    def __init__(self, path, sink=lambda event: None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sink = sink

    def __call__(self, event):
        # 轨迹是观察日志，不是恢复状态；恢复依赖 LangGraph checkpoint。
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": time.time(), **event}, ensure_ascii=False) + "\n")
        self.sink(event)
