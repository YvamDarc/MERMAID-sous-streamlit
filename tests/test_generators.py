from __future__ import annotations

import unittest

from diagram_generators import generate_diagram
from templates import DIAGRAM_TYPES, get_template


EXPECTED_HEADERS = {
    "flowchart": "flowchart",
    "sequence": "sequenceDiagram",
    "mindmap": "mindmap",
    "timeline": "timeline",
    "gantt": "gantt",
    "er": "erDiagram",
    "class": "classDiagram",
    "journey": "journey",
    "pie": "pie",
    "quadrant": "quadrantChart",
    "state": "stateDiagram-v2",
}


class GeneratorSmokeTests(unittest.TestCase):
    def test_every_template_generates_non_empty_mermaid(self):
        self.assertEqual(set(DIAGRAM_TYPES), set(EXPECTED_HEADERS))
        for diagram_type, expected_header in EXPECTED_HEADERS.items():
            with self.subTest(diagram_type=diagram_type):
                code, warnings = generate_diagram(get_template(diagram_type))
                self.assertTrue(code.startswith(expected_header))
                self.assertGreater(len(code.splitlines()), 2)
                self.assertEqual(warnings, [])

    def test_flowchart_reports_unknown_connection(self):
        project = get_template("flowchart")
        project["tables"]["edges"].append(
            {"source": "inconnu", "destination": "reception", "libellé": "", "style": "Flèche"}
        )
        _, warnings = generate_diagram(project)
        self.assertTrue(any("introuvable" in warning for warning in warnings))

    def test_empty_project_still_generates_code(self):
        project = get_template("pie")
        project["tables"]["slices"] = []
        code, warnings = generate_diagram(project)
        self.assertTrue(code.startswith("pie"))
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
