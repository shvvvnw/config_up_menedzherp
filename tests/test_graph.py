from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from configuration import load_config
from graph import build_graph, find_cycles
from repository import load_test_repository


class GraphTests(unittest.TestCase):
    def fixture(self, name):
        return load_test_repository(ROOT / "tests" / "fixtures" / name)

    def test_transitive_dependencies(self):
        repo = self.fixture("acyclic.yaml")
        graph = build_graph("A", 3, repo.__getitem__)
        self.assertEqual(graph, repo)
        self.assertEqual(find_cycles(graph), [])

    def test_depth_limits(self):
        repo = self.fixture("cycle.yaml")
        self.assertEqual(build_graph("A", 0, repo.__getitem__), {"A": []})
        self.assertEqual(build_graph("A", 1, repo.__getitem__),
                         {"A": ["B", "C"], "B": [], "C": []})

    def test_cycle(self):
        repo = self.fixture("cycle.yaml")
        graph = build_graph("A", 3, repo.__getitem__)
        self.assertEqual(graph, repo)
        self.assertIn(["A", "B", "D", "A"], find_cycles(graph))

    def test_self_cycle(self):
        repo = self.fixture("self_cycle.yaml")
        self.assertEqual(find_cycles(build_graph("A", 1, repo.__getitem__)),
                         [["A", "A"]])

    def test_shorter_path(self):
        repo = {"A": ["B", "D"], "B": ["C"], "C": ["D"],
                "D": ["E"], "E": []}
        self.assertEqual(build_graph("A", 3, repo.__getitem__), repo)

    def test_deep_graph_without_recursion(self):
        size = 1500
        repo = {str(i): [str(i + 1)] for i in range(size)}
        repo[str(size)] = []
        graph = build_graph("0", size + 1, repo.__getitem__)
        self.assertEqual(len(graph), size + 1)
        self.assertEqual(find_cycles(graph), [])

    def test_missing_dependency(self):
        with self.assertRaisesRegex(ValueError, "не описан"):
            self.fixture("missing.yaml")

    def test_configuration(self):
        config = load_config()
        self.assertTrue(config["test_mode"])
        self.assertTrue(Path(config["repository_url"]).is_file())

    def test_cli_from_another_directory(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "src" / "main.py")],
            cwd=tempfile.gettempdir(), capture_output=True, text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("A -> B -> D -> A", result.stdout)


if __name__ == "__main__":
    unittest.main()
