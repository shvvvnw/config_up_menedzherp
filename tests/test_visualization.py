import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graph import build_graph
from main import main
from visualization import to_ascii_tree, to_d2


class VisualizationTests(unittest.TestCase):
    def test_d2_nodes_and_edges(self):
        graph = {"A": ["B", "B"], "B": [], "C": []}
        text = to_d2(graph, "A")
        self.assertIn('n0: "A"', text)
        self.assertIn('n2: "C"', text)
        self.assertEqual(text.count("n0 -> n1"), 1)

    def test_d2_safe_identifiers_and_quoted_labels(self):
        text = to_d2({'a.b': ['direction'], 'direction': [], 'a"b': []})
        self.assertIn('"a.b"', text)
        self.assertIn('"direction"', text)
        self.assertIn('"a\\"b"', text)
        self.assertNotIn('a.b ->', text)

    def test_d2_cycle_and_depth(self):
        text = to_d2({"A": ["B"], "B": ["A"]}, "A", {"B"})
        self.assertIn("n0 -> n1", text)
        self.assertIn("n1 -> n0", text)
        self.assertIn("style.stroke-dash: 5", text)
        self.assertIn("B [depth limit]", text)

    def test_ascii_chain(self):
        text = to_ascii_tree({"A": ["B"], "B": ["C"], "C": []}, "A")
        self.assertEqual(text, "A\n`-- B\n    `-- C\n")
        self.assertTrue(text.isascii())

    def test_ascii_shared_dependency(self):
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(to_ascii_tree(graph, "A"),
                         "A\n|-- B\n|   `-- D\n`-- C\n    `-- D [seen]\n")

    def test_ascii_cycles(self):
        self.assertEqual(to_ascii_tree({"A": ["A"]}, "A"),
                         "A\n`-- A [cycle]\n")
        self.assertIn("A [cycle]", to_ascii_tree({"A": ["B"], "B": ["A"]}, "A"))

    def test_ascii_respects_depth_on_longer_path(self):
        repo = {"A": ["B", "D"], "B": ["C"], "C": ["D"],
                "D": ["E"], "E": []}
        boundary = set()
        graph = build_graph("A", 3, repo.__getitem__, boundary)
        text = to_ascii_tree(graph, "A", boundary, 3)
        self.assertIn("D [depth limit]", text)
        self.assertEqual(text.count("`-- E"), 1)

    def test_ascii_zero_depth(self):
        self.assertEqual(to_ascii_tree({"A": []}, "A", {"A"}, 0),
                         "A [depth limit]\n")

    def test_ascii_reopens_seen_node_on_shorter_path(self):
        repo = {"A": ["B", "D"], "B": ["D"], "D": ["E"],
                "E": ["F"], "F": []}
        boundary = set()
        graph = build_graph("A", 3, repo.__getitem__, boundary)
        text = to_ascii_tree(graph, "A", boundary, 3)
        self.assertIn("E [depth limit]", text)
        self.assertIn("F [depth limit]", text)
        self.assertNotIn("D [seen]", text)

    def test_ascii_long_chain(self):
        graph = {str(i): [str(i + 1)] for i in range(1100)}
        graph["1100"] = []
        self.assertEqual(len(to_ascii_tree(graph, "0").splitlines()), 1101)

    def test_invalid_root_and_missing_node(self):
        with self.assertRaises(ValueError):
            to_ascii_tree({"A": []}, "B")
        with self.assertRaises(ValueError):
            to_d2({"A": ["B"]})

    def test_cli_ascii_toggle(self):
        for enabled in (True, False):
            fixture = ROOT / "tests" / "fixtures" / "chain.yaml"
            config = dict(package_name="A", test_mode=True, max_depth=3,
                          ascii_tree=enabled,
                          repository_url=str(fixture))
            output = io.StringIO()
            with patch("main.load_config", return_value=config):
                with contextlib.redirect_stdout(output):
                    main()
            self.assertIn("Граф в формате D2:", output.getvalue())
            self.assertEqual("ASCII-дерево:" in output.getvalue(), enabled)


if __name__ == "__main__":
    unittest.main()
