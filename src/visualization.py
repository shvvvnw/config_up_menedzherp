import json


def validate_graph(graph, root=None):
    if root is not None and root not in graph:
        raise ValueError(f"Корень {root} отсутствует в графе")
    for dependencies in graph.values():
        for dependency in dependencies:
            if dependency not in graph:
                raise ValueError(f"Пакет {dependency} отсутствует в графе")


def to_d2(graph, root=None, unexpanded=()):
    validate_graph(graph, root)
    boundary = set(unexpanded)
    identifiers = {name: f"n{i}" for i, name in enumerate(sorted(graph))}
    lines = ["direction: right", ""]

    for package, identifier in identifiers.items():
        label = package
        if package in boundary:
            label += " [depth limit]"
        lines.append(f"{identifier}: {json.dumps(label, ensure_ascii=False)} {{")
        if package == root:
            lines.append('  style.fill: "#dbeafe"')
        if package in boundary:
            lines.append("  style.stroke-dash: 5")
        lines.append("}")

    edges = set()
    for package, dependencies in graph.items():
        for dependency in dependencies:
            edges.add((package, dependency))

    for package, dependency in sorted(edges):
        lines.append(f"{identifiers[package]} -> {identifiers[dependency]}")

    return "\n".join(lines) + "\n"


def to_ascii_tree(graph, root, unexpanded=(), max_depth=None):
    validate_graph(graph, root)
    if max_depth is not None and (type(max_depth) is not int or max_depth < 0):
        raise ValueError("Глубина дерева должна быть целым числом от нуля")

    boundary = set(unexpanded)
    seen_depth = {}
    lines = []
    stack = [(root, "", "", (), 0)]

    while stack:
        package, prefix, connector, ancestors, depth = stack.pop()
        marker = ""
        if package in ancestors:
            marker = " [cycle]"
        elif package in boundary or (
            max_depth is not None and depth >= max_depth and graph[package]
        ):
            marker = " [depth limit]"
        elif package in seen_depth and seen_depth[package] <= depth:
            marker = " [seen]"

        lines.append(prefix + connector + package + marker)
        if marker:
            continue

        seen_depth[package] = depth
        children = list(dict.fromkeys(graph[package]))
        child_prefix = prefix
        if connector:
            child_prefix += "    " if connector == "`-- " else "|   "

        for index in range(len(children) - 1, -1, -1):
            child_connector = "`-- " if index == len(children) - 1 else "|-- "
            stack.append((children[index], child_prefix, child_connector,
                          ancestors + (package,), depth + 1))

    return "\n".join(lines) + "\n"
