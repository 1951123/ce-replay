import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "tools" / "analyze_locality.py"
SPEC = importlib.util.spec_from_file_location("analyze_locality", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LocalityAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workload = Path(self.temp_dir.name) / "queries.sql"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_component_structure_and_isolated_query(self):
        self.workload.write_text(
            "SELECT COUNT(*) FROM t WHERE a = 1 AND b = 2 AND c = 3||4\n"
            "SELECT COUNT(*) FROM t WHERE b = 1 AND c BETWEEN 2 AND 4||5\n"
            "SELECT COUNT(*) FROM t WHERE x = 1 AND y = 2||6\n"
            "SELECT COUNT(*) FROM t WHERE z = 1||7\n",
            encoding="utf-8",
        )

        report = MODULE.analyze(MODULE.parse_queries(self.workload), (2,))

        self.assertEqual(report["counts"], {
            "queries": 4,
            "candidate_bearing_queries": 3,
            "candidates": 4,
            "edges": 5,
            "components": 3,
        })
        self.assertEqual(
            [(c["query_count"], c["candidate_count"]) for c in report["components"]],
            [(2, 3), (1, 1), (1, 0)],
        )
        self.assertEqual(report["giant_component"]["query_ratio"], 0.5)
        self.assertEqual(
            [(b["degree"], b["candidate_count"]) for b in report["candidate_degree_histogram"]],
            [(1, 3), (2, 1)],
        )
        # Removing the sole degree-2 candidate disconnects the first two queries.
        peeled_at_one = report["high_degree_peeling_curve"][1]
        self.assertEqual(peeled_at_one["removed_candidate_count"], 1)
        self.assertEqual(peeled_at_one["component_count"], 4)
        self.assertEqual(peeled_at_one["giant_query_count"], 1)
        neighborhood = report["candidate_interaction_neighborhood"]
        self.assertEqual(neighborhood["size"]["mean"], 2.5)
        self.assertEqual(neighborhood["size"]["median"], 3.0)
        self.assertEqual(neighborhood["size"]["max"], 3)
        self.assertEqual(neighborhood["candidate_interaction_edges"], 3)

    def test_higher_arity_does_not_change_connectivity(self):
        self.workload.write_text(
            "SELECT COUNT(*) FROM climate WHERE a >= 1 AND b <= 2 AND c = 3||4\n"
            "SELECT COUNT(*) FROM climate WHERE a = 1 AND b = 2||5\n",
            encoding="utf-8",
        )
        queries = MODULE.parse_queries(self.workload)

        pairs = MODULE.analyze(queries, (2,))
        pairs_and_triples = MODULE.analyze(queries, (2, 3))

        self.assertEqual(pairs["counts"]["components"], 1)
        self.assertEqual(pairs_and_triples["counts"]["components"], 1)
        self.assertEqual(pairs["counts"]["candidates"], 3)
        self.assertEqual(pairs_and_triples["counts"]["candidates"], 4)
