import yaml

from configuration import load_config
from graph import build_graph, dependency_load_order, find_cycles
from repository import fetch_dependencies, load_test_repository, normalize_name


def main(config_file=None):
    config = load_config(config_file)
    root = config["package_name"]
    cache = {}

    if config["test_mode"]:
        repository = load_test_repository(config["repository_url"])

        if root not in repository:
            raise ValueError(f"Пакет {root} отсутствует в тестовом репозитории")

        def get_dependencies(package):
            return repository[package]

    else:
        root = normalize_name(root)

        def get_dependencies(package):
            if package not in cache:
                print(f"Получение зависимостей: {package}")
                cache[package] = fetch_dependencies(
                    package, config["repository_url"]
                )
            return cache[package]

    unexpanded = set()
    graph = build_graph(
        root, config["max_depth"], get_dependencies, unexpanded
    )

    print("\nГраф зависимостей:")

    for package, dependencies in graph.items():
        targets = ", ".join(dependencies) if dependencies else "[]"
        print(f"{package} -> {targets}")

    print("\n[] — нет исходящих связей в построенной части графа.")
    print("Узлы на предельной глубине не запрашивались.")

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


def run():
    try:
        main()
    except (ValueError, OSError, yaml.YAMLError) as error:
        raise SystemExit(f"Ошибка: {error}")


if __name__ == "__main__":
    run()
