from pathlib import Path
from urllib.parse import urlparse

import yaml


def load_config(filename=None):
    config_path = Path(filename) if filename else Path(__file__).resolve().parent.parent / "config.yaml"
    with config_path.open(encoding="utf-8") as file:
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
        test_path = Path(repository)
        if not test_path.is_absolute():
            test_path = config_path.resolve().parent / test_path
        if not test_path.is_file():
            raise ValueError(f"Тестовый файл не найден: {test_path}")
        config["repository_url"] = str(test_path)
    else:
        address = urlparse(repository)
        if address.scheme not in ("http", "https") or not address.hostname:
            raise ValueError("repository_url: нужен адрес http:// или https://")

    return config
