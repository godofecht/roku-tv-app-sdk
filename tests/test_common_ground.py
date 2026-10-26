import importlib.util
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1] / "examples" / "common_ground" / "build.py"
spec = importlib.util.spec_from_file_location("common_ground", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CommonGroundTests(unittest.TestCase):
    def test_distinct_people_not_post_count(self):
        data = {"people": [
            {"id": "a", "name": "A", "items": [
                {"title": "One", "topics": ["music", "music"]},
                {"title": "Two", "topics": ["music"]}]},
            {"id": "b", "name": "B", "items": [
                {"title": "Three", "topics": ["music"]}]}
        ]}
        result = module.shared_topics(data)
        self.assertEqual(result[0]["people"], 2)
        self.assertEqual(result[0]["topic"], "music")

    def test_disjoint_feeds(self):
        data = {"people": [
            {"id": "a", "name": "A", "items": [{"title": "X", "topics": ["x"]}]},
            {"id": "b", "name": "B", "items": [{"title": "Y", "topics": ["y"]}]}
        ]}
        self.assertEqual(module.shared_topics(data), [])
        with tempfile.TemporaryDirectory() as temp:
            module.generate(data, temp)
            root = ET.parse(Path(temp) / "components" / "MainScene.xml").getroot()
            self.assertEqual(root.attrib["name"], "MainScene")

    def test_duplicate_person_rejected(self):
        with self.assertRaises(ValueError):
            module.shared_topics({"people": [
                {"id": "a", "name": "A", "items": []},
                {"id": "a", "name": "B", "items": []}
            ]})


if __name__ == "__main__":
    unittest.main()
