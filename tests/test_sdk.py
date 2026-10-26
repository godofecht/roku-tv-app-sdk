import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from roku_ai.__main__ import DEFAULT, build, package, validate


class RokuSDKTests(unittest.TestCase):
    def test_valid_spec(self):
        self.assertEqual(validate(DEFAULT), DEFAULT)

    def test_reject_bad_color(self):
        with self.assertRaises(ValueError):
            validate({**DEFAULT, "background_color": "red"})

    def test_reject_unknown_key(self):
        with self.assertRaises(ValueError):
            validate({**DEFAULT, "secret": "bad"})

    def test_build_and_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project = root / "app"
            build(DEFAULT, project)
            scene = ET.parse(project / "components/MainScene.xml").getroot()
            self.assertEqual(scene.attrib["name"], "MainScene")
            archive = root / "app.zip"
            package(project, archive)
            first = archive.read_bytes()
            package(project, archive)
            self.assertEqual(first, archive.read_bytes())
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(sorted(z.namelist()), [
                    "components/MainScene.xml", "manifest", "source/main.brs"
                ])


if __name__ == "__main__":
    unittest.main()
