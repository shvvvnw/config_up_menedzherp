import yaml
from urllib.parse import urlparse
from pathlib import Path


try:  # пытается прочитать конфигурацию
    with open("config.yaml", encoding="utf-8") as file:
        config = yaml.safe_load(file)
except FileNotFoundError:  # сообщает, если файл не найден
    raise SystemExit("Ошибка: файл config.yaml не найден")
except yaml.YAMLError as error:  # сообщает, если YAML написан неправильно
    raise SystemExit(f"Ошибка в структуре YAML: {error}")
    # завершает программу и показывает понятную ошибку без большого traceback


if not isinstance(config, dict):  # проверяет, что получили словарь
    raise ValueError("В YAML должны быть настройки в формате ключ: значение")


required_keys = (  # перечисляет обязательные ключи
    "package_name",
    "repository_url",
    "test_mode",
    "ascii_tree",
    "max_depth",
)

for key in required_keys:
    if key not in config:  # проверяет, не забыли ли обязательный ключ
        raise ValueError(f"Отсутствует настройка: {key}")


for key in ("package_name", "repository_url"):
    value = config[key]
    # strip() удаляет пробелы по краям; строка из пробелов считается пустой
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}: нужна непустая строка")


for key in ("test_mode", "ascii_tree"):
    if type(config[key]) is not bool:
        raise ValueError(f"{key}: допустимы только true или false")


depth = config["max_depth"]
if type(depth) is not int or depth < 0:
    raise ValueError("max_depth: нужно целое число не меньше нуля")


repository = config["repository_url"]

if config["test_mode"]:
    # в тестовом режиме repository_url содержит путь к файлу
    if not Path(repository).is_file():
        raise ValueError("repository_url: тестовый файл не найден")
else:
    # в обычном режиме repository_url содержит адрес сайта
    parsed_url = urlparse(repository)

    if parsed_url.scheme not in ("http", "https"):
        raise ValueError(
            "repository_url: адрес должен начинаться с http:// или https://"
        )

    if not parsed_url.netloc:
        raise ValueError("repository_url: не указано имя сайта")


for key, value in config.items():
    print(f"{key}: {value}")  # показывает прочитанные данные