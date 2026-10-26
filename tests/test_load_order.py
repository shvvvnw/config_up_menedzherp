import contextlib
import io
from http.client import IncompleteRead
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graph import build_graph, dependency_load_order
from main import main
from repository import fetch_dependencies, load_test_repository


class LoadOrderTests(unittest.TestCase):
    def graph(self, filename, depth=10):
        repo = load_test_repository(ROOT / "tests" / "fixtures" / filename)
        return build_graph("A", depth, repo.__getitem__)

    def assert_dependencies_first(self, graph, order):
        self.assertEqual(set(order), set(graph))
        self.assertEqual(len(order), len(set(order)))
        position = {package: i for i, package in enumerate(order)}
        for package, dependencies in graph.items():
            for dependency in dependencies:
                self.assertLess(position[dependency], position[package])

    def test_chain(self):
        graph = self.graph("chain.yaml")
        self.assertEqual(dependency_load_order(graph), ["C", "B", "A"])

    def test_shared_dependency_once(self):
        graph = self.graph("acyclic.yaml")
        order = dependency_load_order(graph)
        self.assert_dependencies_first(graph, order)
        self.assertEqual(order.count("D"), 1)

    def test_cycle_has_no_order(self):
        with self.assertRaisesRegex(ValueError, "цикл"):
            dependency_load_order(self.graph("cycle.yaml"))

    def test_self_cycle_has_no_order(self):
        with self.assertRaisesRegex(ValueError, "A -> A"):
            dependency_load_order(self.graph("self_cycle.yaml"))

    def test_isolated_and_empty(self):
        self.assertEqual(dependency_load_order(self.graph("isolated.yaml")), ["A"])
        self.assertEqual(dependency_load_order({}), [])

    def test_long_chain_without_recursion(self):
        graph = {str(i): [str(i + 1)] for i in range(1500)}
        graph["1500"] = []
        order = dependency_load_order(graph)
        self.assert_dependencies_first(graph, order)
        self.assertEqual(order[0], "1500")
        self.assertEqual(order[-1], "0")

    def test_depth_boundary(self):
        repo = {"A": ["B"], "B": ["C"], "C": []}
        unexpanded = set()
        graph = build_graph("A", 1, repo.__getitem__, unexpanded)
        self.assertEqual(unexpanded, {"B"})
        self.assertEqual(dependency_load_order(graph), ["B", "A"])

    def test_shorter_path_clears_boundary(self):
        repo = {"A": ["B", "D"], "B": ["C"], "C": ["D"],
                "D": ["E"], "E": []}
        unexpanded = set()
        graph = build_graph("A", 3, repo.__getitem__, unexpanded)
        self.assertEqual(unexpanded, set())
        self.assert_dependencies_first(graph, dependency_load_order(graph))

    def test_missing_node(self):
        with self.assertRaisesRegex(ValueError, "B отсутствует"):
            dependency_load_order({"A": ["B"]})

    def test_cli_order_and_cycle_message(self):
        for filename, expected in (
            ("chain.yaml", "C -> B -> A"),
            ("cycle.yaml", "Порядок загрузки невозможен"),
        ):
            config = dict(package_name="A", test_mode=True,
                          repository_url=str(ROOT / "tests" / "fixtures" / filename),
                          max_depth=10, ascii_tree=True)
            output = io.StringIO()
            with patch("main.load_config", return_value=config):
                with contextlib.redirect_stdout(output):
                    main()
            self.assertIn(expected, output.getvalue())

    def test_cli_warns_about_hidden_cycles(self):
        config = dict(package_name="A", test_mode=True,
                      repository_url=str(ROOT / "tests" / "fixtures" / "cycle.yaml"),
                      max_depth=1, ascii_tree=True)
        output = io.StringIO()
        with patch("main.load_config", return_value=config):
            with contextlib.redirect_stdout(output):
                main()
        self.assertIn("для построенной части графа", output.getvalue())
        self.assertIn("скрытых циклов не гарантируются", output.getvalue())

    def test_interrupted_response_has_clear_error(self):
        with patch("repository.urlopen", side_effect=IncompleteRead(b"partial")):
            with self.assertRaisesRegex(ValueError, "прервал передачу"):
                fetch_dependencies("requests", "https://pypi.org/pypi")


if __name__ == "__main__":
    unittest.main()
