import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "examples" / "common_ground" / "build.py"
spec = importlib.util.spec_from_file_location("common_ground_discovery_build", PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class CrossInterestTests(unittest.TestCase):
    def test_cross_interest_without_shared_tags(self):
        data = {"people": [
            {"id": "a", "name": "A", "items": [{"title": "Synths", "topics": ["technology"]}]},
            {"id": "b", "name": "B", "items": [{"title": "Jazz", "topics": ["improvisation"]}]}
        ], "bridges": [{"from": "technology", "to": "improvisation", "reason": "Creative exploration"}]}
        self.assertEqual(app.shared_topics(data), [])
        ranked = app.discover(data)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["people"], 2)
        with tempfile.TemporaryDirectory() as folder:
            app.generate(data, folder)
            script = (Path(folder) / "components" / "MainScene.brs").read_text()
            self.assertIn('function onKeyEvent(', script)
            self.assertIn('renderCard()', script)
            self.assertIn('Creative exploration', script)
            root = ET.parse(Path(folder) / "components" / "MainScene.xml").getroot()
            self.assertIsNotNone(root.find("script"))
            self.assertEqual(len(json.loads((Path(folder) / "commonality.json").read_text())), 1)

    def test_no_self_connection_or_duplicate_bridge(self):
        data = {"people": [
            {"id": "a", "name": "A", "items": [{"title": "A", "topics": ["x", "y"]}]},
            {"id": "b", "name": "B", "items": [{"title": "B", "topics": ["y"]}]}
        ], "bridges": [
            {"from": "x", "to": "y", "reason": "First"},
            {"from": "y", "to": "x", "reason": "Duplicate"},
            {"from": "y", "to": "y", "reason": "Self"}
        ]}
        self.assertEqual(len(app.discover(data)), 1)

    def test_no_same_person_only_bridge(self):
        data = {"people": [
            {"id": "a", "name": "A", "items": [{"title": "A", "topics": ["x", "y"]}]},
            {"id": "b", "name": "B", "items": []}
        ], "bridges": [{"from": "x", "to": "y", "reason": "Related"}]}
        self.assertEqual(app.discover(data), [])

    def test_invalid_bridge_rejected(self):
        data = {"people": [
            {"id": "a", "name": "A", "items": []},
            {"id": "b", "name": "B", "items": []}
        ], "bridges": [{"from": "x", "to": "y"}]}
        with self.assertRaises(ValueError):
            app.discover(data)

    def test_sample_has_discoveries(self):
        data = json.loads((ROOT / "examples" / "common_ground" / "feeds.json").read_text())
        self.assertGreaterEqual(len(app.discover(data)), 2)


if __name__ == "__main__":
    unittest.main()
