import json
import re
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

import yaml


HTTP_NOT_FOUND = 404


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
                raise ValueError(
                    f"{package}: имя зависимости должно быть строкой"
                )
            if dependency not in repository:
                raise ValueError(f"Пакет {dependency} не описан в репозитории")

    return repository


def normalize_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _read_package_data(package, repository_url):
    base_url = repository_url.rstrip("/")
    url = f"{base_url}/{quote(package, safe='')}/json"

    try:
        with urlopen(url, timeout=15) as response:
            data = json.load(response)
    except HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise ValueError(f"Пакет {package} не найден") from error
        raise ValueError(f"Ошибка HTTP для {package}: {error.code}") from error
    except URLError as error:
        raise ValueError(f"Ошибка подключения: {error.reason}") from error
    except TimeoutError as error:
        raise ValueError(f"Истекло время ожидания для {package}") from error
    except HTTPException as error:
        raise ValueError(
            f"Сервер прервал передачу данных для {package}. Повторите запуск."
        ) from error

    return data


def _requirements_to_names(package, data):
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

        pattern = r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)"
        match = re.match(pattern, requirement)
        if match is None:
            raise ValueError(f"Не удалось прочитать зависимость: {requirement}")

        name = normalize_name(match.group(1))
        if name not in dependencies:
            dependencies.append(name)

    return dependencies


def fetch_dependencies(package, repository_url):
    data = _read_package_data(package, repository_url)
    return _requirements_to_names(package, data)
