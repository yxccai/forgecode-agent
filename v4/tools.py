from v3.tools import Tools as RepositoryTools
from v4.memory import Memory


class Tools(RepositoryTools):
    def __init__(self, root, approve=lambda argv: False, repo_context=True, memory=True, store_root=None):
        super().__init__(root, approve, repo_context, memory)
        if memory:
            self.memory = Memory(root, store_root)
