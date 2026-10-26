import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import urlopen

import yaml


try:
    with open("config.yaml", encoding="utf-8") as file:
        config = yaml.safe_load(file)
except FileNotFoundError:
    raise SystemExit("Ошибка: файл config.yaml не найден")
except OSError as error:
    raise SystemExit(f"Ошибка чтения файла: {error}")
except yaml.YAMLError as error:
    raise SystemExit(f"Ошибка в YAML: {error}")


if not isinstance(config, dict):
    raise SystemExit("В YAML должны быть настройки в формате ключ: значение")

required_keys = (
    "package_name",
    "repository_url",
    "test_mode",
    "ascii_tree",
    "max_depth",
)

for key in required_keys:
    if key not in config:
        raise SystemExit(f"Отсутствует настройка: {key}")

for key in ("package_name", "repository_url"):
    value = config[key]
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{key}: нужна непустая строка")

for key in ("test_mode", "ascii_tree"):
    if type(config[key]) is not bool:
        raise SystemExit(f"{key}: допустимы только true или false")

depth = config["max_depth"]
if type(depth) is not int or depth < 0:
    raise SystemExit("max_depth: нужно целое число не меньше нуля")


repository = config["repository_url"].strip()

if config["test_mode"]:
    if not Path(repository).is_file():
        raise SystemExit("repository_url: тестовый файл не найден")
else:
    try:
        parsed_url = urlparse(repository)
    except ValueError:
        raise SystemExit("repository_url: неправильный адрес")

    if parsed_url.scheme not in ("http", "https"):
        raise SystemExit(
            "repository_url: адрес должен начинаться с http:// или https://"
        )

    if not parsed_url.netloc:
        raise SystemExit("repository_url: не указано имя сайта")


for key, value in config.items():
    print(f"{key}: {value}")


if config["test_mode"]:
    raise SystemExit("Чтение тестового репозитория пока не реализовано")

package = config["package_name"].strip()
base_url = repository.rstrip("/")
url = f"{base_url}/{quote(package, safe='')}/json"

try:
    with urlopen(url, timeout=15) as response:
        data = json.load(response)
except HTTPError as error:
    if error.code == 404:
        raise SystemExit(f"Пакет {package} не найден")
    raise SystemExit(f"Ошибка HTTP: {error.code}")
except URLError as error:
    raise SystemExit(f"Не удалось подключиться: {error.reason}")
except TimeoutError:
    raise SystemExit("Сервер слишком долго не отвечает")
except (json.JSONDecodeError, UnicodeDecodeError):
    raise SystemExit("Сервер вернул данные в неправильном формате")
except OSError as error:
    raise SystemExit(f"Ошибка получения данных: {error}")


if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
    raise SystemExit("В ответе сервера отсутствует информация о пакете")

dependencies = data["info"].get("requires_dist")

if dependencies is None:
    dependencies = []

if not isinstance(dependencies, list):
    raise SystemExit("Сервер вернул неправильный список зависимостей")

if not all(isinstance(item, str) for item in dependencies):
    raise SystemExit("В списке зависимостей должны быть строки")


print(f"\nОбъявленные прямые зависимости пакета {package}:")

if dependencies:
    for dependency in dependencies:
        print(f"- {dependency}")
else:
    print("В метаданных зависимости не указаны")