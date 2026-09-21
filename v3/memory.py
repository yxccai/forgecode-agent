import hashlib
import json
from pathlib import Path
import sqlite3
import time

from v0.tools import Tools
from v3.repository import terms


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Memory:
    def __init__(self, root):
        self.root = Path(root).resolve()
        folder = self.root / ".forgecode"
        folder.mkdir(exist_ok=True)
        self.db = folder / "memory.sqlite"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, kind TEXT, "
                         "note TEXT, sources TEXT, created REAL, confidence REAL)")

    def remember(self, note, sources, kind="semantic", confidence=0.5):
        if kind not in {"semantic", "episodic"} or not note.strip() or len(note) > 2000:
            raise ValueError("Invalid memory kind or note length")
        if not sources or len(sources) > 10:
            raise ValueError("Memory requires 1-10 source paths")
        guard = Tools(self.root)
        fingerprints = {}
        for source in sources:
            path = guard.path(source)
            if path.stat().st_size > 500_000:
                raise ValueError("Memory source too large")
            fingerprints[str(path.relative_to(self.root))] = digest(path)
        with sqlite3.connect(self.db) as conn:
            cursor = conn.execute("INSERT INTO memories(kind,note,sources,created,confidence) VALUES(?,?,?,?,?)",
                                  (kind, note, json.dumps(fingerprints), time.time(), confidence))
            return cursor.lastrowid

    def recall(self, query, limit=5):
        with sqlite3.connect(self.db) as conn:
            rows = conn.execute("SELECT id,kind,note,sources,created,confidence FROM memories "
                                "ORDER BY id DESC LIMIT 500").fetchall()
        memories = [dict(zip(("id", "kind", "note", "sources", "created", "confidence"), row)) for row in rows]
        for memory in memories:
            memory["sources"] = json.loads(memory["sources"])
            memory["score"] = len(terms(query) & terms(memory["note"] + " " + " ".join(memory["sources"])))
        return sorted([m for m in memories if m["score"]], key=lambda m: (-m["score"], -m["created"]))[:limit]
