from collections import defaultdict

def has_cycle(graph: dict[str, list[str]]) -> bool:
    visited = set()
    visiting = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False

        visiting.add(node)
        for dep in graph.get(node, []):
            if dfs(dep):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    for node in graph:
        if dfs(node):
            return True

    return False
