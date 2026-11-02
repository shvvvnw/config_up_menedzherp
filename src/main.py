import yaml

from configuration import load_config
from graph import build_graph, dependency_load_order, find_cycles
from repository import fetch_dependencies, load_test_repository, normalize_name
from visualization import to_ascii_tree, to_d2


def _dependency_source(config):
    root = config["package_name"]

    if config["test_mode"]:
        repository = load_test_repository(config["repository_url"])
        if root not in repository:
            raise ValueError(f"Пакет {root} отсутствует в тестовом репозитории")
        return root, repository.__getitem__

    root = normalize_name(root)
    cache = {}

    def get_dependencies(package):
        if package not in cache:
            print(f"Получение зависимостей: {package}")
            cache[package] = fetch_dependencies(
                package, config["repository_url"]
            )
        return cache[package]

    return root, get_dependencies


def _print_graph(graph):

    print("\nГраф зависимостей:")

    for package, dependencies in graph.items():
        targets = ", ".join(dependencies) if dependencies else "[]"
        print(f"{package} -> {targets}")

    print("\n[] — нет исходящих связей в построенной части графа.")
    print("Узлы на предельной глубине не запрашивались.")


def _print_analysis(graph, unexpanded):
    cycles = find_cycles(graph)
    if cycles:
        print("\nОбнаружены циклы:")
        for cycle in cycles:
            print(" -> ".join(cycle))
    else:
        print("\nВ построенной части графа циклы не обнаружены.")

    if cycles:
        print("\nПорядок загрузки невозможен: граф содержит цикл.")
    else:
        order = dependency_load_order(graph)
        if unexpanded:
            print("\nПорядок загрузки для построенной части графа:")
        else:
            print("\nПорядок загрузки (зависимости перед пакетами):")
        print(" -> ".join(order))

    if unexpanded:
        print("\nИз-за ограничения глубины не исследованы: "
              + ", ".join(sorted(unexpanded)))
        print("Полный порядок загрузки и отсутствие скрытых циклов "
              "не гарантируются.")


def _print_visualization(graph, root, unexpanded, config):
    print("\nГраф в формате D2:")
    print(to_d2(graph, root, unexpanded), end="")

    if config["ascii_tree"]:
        print("\nASCII-дерево:")
        tree = to_ascii_tree(graph, root, unexpanded, config["max_depth"])
        print(tree, end="")
        print("[cycle] — цикл; [seen] — уже показан; "
              "[depth limit] — предел глубины.")


def main(config_file=None):
    config = load_config(config_file)
    root, get_dependencies = _dependency_source(config)
    unexpanded = set()
    graph = build_graph(
        root, config["max_depth"], get_dependencies, unexpanded
    )
    _print_graph(graph)
    _print_analysis(graph, unexpanded)
    _print_visualization(graph, root, unexpanded, config)


def run():
    try:
        main()
    except (ValueError, OSError, yaml.YAMLError) as error:
        raise SystemExit(f"Ошибка: {error}")


if __name__ == "__main__":
    run()
