from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graph import build_graph, dependency_load_order
from repository import load_test_repository


for filename, depth in (
    ("chain.yaml", 3),
    ("acyclic.yaml", 3),
    ("isolated.yaml", 3),
    ("cycle.yaml", 3),
    ("self_cycle.yaml", 3),
    ("chain.yaml", 1),
):
    repository = load_test_repository(ROOT / "tests" / "fixtures" / filename)
    boundary = set()
    graph = build_graph("A", depth, repository.__getitem__, boundary)
    print(f"\n{filename}, max_depth={depth}")
    try:
        print(" -> ".join(dependency_load_order(graph)))
    except ValueError as error:
        print(error)
    if boundary:
        print("Порядок только для построенной части; не исследованы: "
              + ", ".join(sorted(boundary)))
