import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graph import build_graph
from repository import fetch_dependencies
from visualization import to_ascii_tree, to_d2


def generate(offline=False):
    output = ROOT / "examples" / "stage5"
    output.mkdir(parents=True, exist_ok=True)

    for package in ("requests", "urllib3", "six"):
        snapshot_path = output / f"{package}.json"
        if offline:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        else:
            unexpanded = set()
            graph = build_graph(
                package, 1,
                lambda name: fetch_dependencies(name, "https://pypi.org/pypi"),
                unexpanded,
            )
            snapshot = {
                "package": package,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "repository_url": "https://pypi.org/pypi",
                "max_depth": 1,
                "graph": graph,
                "unexpanded": sorted(unexpanded),
            }
            snapshot_path.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        graph = snapshot["graph"]
        unexpanded = snapshot["unexpanded"]
        d2 = to_d2(graph, package, unexpanded)
        tree = to_ascii_tree(graph, package, unexpanded, snapshot["max_depth"])
        (output / f"{package}.d2").write_text(d2, encoding="utf-8")
        (output / f"{package}.txt").write_text(tree, encoding="utf-8")
        print(f"\n{package}\n{tree}", end="", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Три примера визуализации")
    parser.add_argument("--offline", action="store_true",
                        help="использовать сохранённые ответы без интернета")
    arguments = parser.parse_args()
    try:
        generate(arguments.offline)
    except (ValueError, OSError) as error:
        raise SystemExit(f"Ошибка: {error}")
