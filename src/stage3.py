import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import urlopen

import yaml


def load_config():
    with open("config3.yaml", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("В YAML должны быть настройки ключ: значение")

    required_keys = (
        "package_name",
        "repository_url",
        "test_mode",
        "ascii_tree",
        "max_depth",
    )

    for key in required_keys:
        if key not in config:
            raise ValueError(f"Отсутствует настройка: {key}")

    for key in ("package_name", "repository_url"):
        value = config[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key}: нужна непустая строка")
        config[key] = value.strip()

    for key in ("test_mode", "ascii_tree"):
        if type(config[key]) is not bool:
            raise ValueError(f"{key}: допустимы только true или false")

    depth = config["max_depth"]
    if type(depth) is not int or depth < 0:
        raise ValueError("max_depth: нужно целое число не меньше нуля")

    repository = config["repository_url"]

    if config["test_mode"]:
        if not Path(repository).is_file():
            raise ValueError("Тестовый файл не найден")
    else:
        address = urlparse(repository)
        if address.scheme not in ("http", "https") or not address.hostname:
            raise ValueError("repository_url: нужен адрес http:// или https://")

    return config


def load_test_repository(filename):
    with open(filename, encoding="utf-8") as file:
        repository = yaml.safe_load(file)

    if not isinstance(repository, dict) or not repository:
        raise ValueError("Тестовый репозиторий должен быть непустым словарём")

    for package, dependencies in repository.items():
        if not isinstance(package, str) or not re.fullmatch(r"[A-Z]+", package):
            raise ValueError("Имена тестовых пакетов: большие латинские буквы")

        if not isinstance(dependencies, list):
            raise ValueError(f"{package}: зависимости должны быть списком")

        for dependency in dependencies:
            if not isinstance(dependency, str):
                raise ValueError(f"{package}: имя зависимости должно быть строкой")
            if dependency not in repository:
                raise ValueError(f"Пакет {dependency} не описан в репозитории")

    return repository


def normalize_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def fetch_dependencies(package, repository_url):
    base_url = repository_url.rstrip("/")
    url = f"{base_url}/{quote(package, safe='')}/json"

    try:
        with urlopen(url, timeout=15) as response:
            data = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            raise ValueError(f"Пакет {package} не найден") from error
        raise ValueError(f"Ошибка HTTP для {package}: {error.code}") from error
    except URLError as error:
        raise ValueError(f"Ошибка подключения: {error.reason}") from error
    except TimeoutError as error:
        raise ValueError(f"Истекло время ожидания для {package}") from error

    if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
        raise ValueError(f"{package}: неправильный ответ сервера")

    requirements = data["info"].get("requires_dist")
    if requirements is None:
        requirements = []

    if not isinstance(requirements, list):
        raise ValueError(f"{package}: неправильный список зависимостей")

    dependencies = []

    for requirement in requirements:
        if not isinstance(requirement, str):
            raise ValueError(f"{package}: зависимость должна быть строкой")

        match = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
        if match is None:
            raise ValueError(f"Не удалось прочитать зависимость: {requirement}")

        name = normalize_name(match.group(1))
        if name not in dependencies:
            dependencies.append(name)

    return dependencies


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


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, yaml.YAMLError) as error:
        raise SystemExit(f"Ошибка: {error}")