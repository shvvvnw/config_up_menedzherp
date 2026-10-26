import yaml

from configuration import load_config
from graph import build_graph, find_cycles
from repository import fetch_dependencies, load_test_repository, normalize_name


def main():
    config = load_config()
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

    graph = build_graph(root, config["max_depth"], get_dependencies)

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


def run():
    try:
        main()
    except (ValueError, OSError, yaml.YAMLError) as error:
        raise SystemExit(f"Ошибка: {error}")


if __name__ == "__main__":
    run()
