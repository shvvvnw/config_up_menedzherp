def build_graph(root, max_depth, get_dependencies):
    graph = {}
    best_depth = {}
    stack = [(root, 0)]

    while stack:
        package, depth = stack.pop()

        if package in best_depth and best_depth[package] <= depth:
            continue

        best_depth[package] = depth
        graph.setdefault(package, [])

        if depth >= max_depth:
            continue

        dependencies = get_dependencies(package)
        graph[package] = dependencies

        for dependency in reversed(dependencies):
            graph.setdefault(dependency, [])
            stack.append((dependency, depth + 1))

    return graph


def find_cycles(graph):
    colors = {}
    cycles = []

    for root in graph:
        if colors.get(root, 0) != 0:
            continue

        colors[root] = 1
        path = [root]
        stack = [(root, iter(graph[root]))]

        while stack:
            package, children = stack[-1]
            dependency = next(children, None)

            if dependency is None:
                colors[package] = 2
                stack.pop()
                path.pop()

            elif colors.get(dependency, 0) == 0:
                colors[dependency] = 1
                path.append(dependency)
                stack.append((dependency, iter(graph[dependency])))

            elif colors[dependency] == 1:
                start = path.index(dependency)
                cycles.append(path[start:] + [dependency])

    return cycles
