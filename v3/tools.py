import json
from langchain_core.tools import StructuredTool

from v1.tools import Tools as CodingTools
from v3.memory import Memory
from v3.repository import Repository


class Tools(CodingTools):
    def __init__(self, root, approve=lambda argv: False, repo_context=True, memory=True):
        super().__init__(root, approve)
        self.repository = Repository(root)
        self.memory = Memory(root) if memory else None
        self.repo_context = repo_context
        if repo_context:
            self.items.extend([StructuredTool.from_function(self.repo_map),
                               StructuredTool.from_function(self.find_symbols)])
        if memory:
            self.items.extend([StructuredTool.from_function(self.recall_memory),
                               StructuredTool.from_function(self.remember)])

    def files(self):
        yield from self.repository.paths()

    def repo_map(self, query: str):
        """Rank relevant paths, Python symbols and imports for a task; no full source dump."""
        return json.dumps(self.repository.select(query))

    def find_symbols(self, query: str):
        """Find Python function/class names and source line numbers using AST."""
        return json.dumps(self.repository.symbols(query))

    def recall_memory(self, query: str):
        """Retrieve fallible repository notes with source fingerprints and confidence."""
        return json.dumps(self.memory.recall(query) if self.memory else [])

    def remember(self, note: str, sources: list[str], kind: str = "semantic"):
        """Save a concise semantic or episodic note backed by existing source file paths."""
        if not self.memory:
            return "Memory disabled"
        return json.dumps({"memory_id": self.memory.remember(note, sources, kind)})
