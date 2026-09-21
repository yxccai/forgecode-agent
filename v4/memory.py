from pathlib import Path
import time

from v0.tools import Tools
from v3.memory import Memory as StoredMemory, digest


class Memory(StoredMemory):
    def __init__(self, root, store_root=None):
        super().__init__(store_root or root)
        self.root = Path(root).resolve()

    def recall(self, query, limit=5):
        # 过滤而不是删除：时间、置信标签、来源哈希都通过才返回；仍不能证明结论正确。
        candidates = super().recall(query, limit=500)
        valid = []
        guard = Tools(self.root)
        for note in candidates:
            if time.time() - note["created"] > 30 * 86400 or note["confidence"] < .4:
                continue
            try:
                if all(digest(guard.path(path)) == fingerprint for path, fingerprint in note["sources"].items()):
                    valid.append({**note, "validated": True})
            except (OSError, ValueError):
                continue
        return valid[:limit]
