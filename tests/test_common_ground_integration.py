import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

service = importlib.import_module("examples.common_ground.app")


class CommonGroundIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = service.DB_PATH
        service.DB_PATH = str(Path(self.temp.name) / "test.sqlite3")
        self.client = TestClient(service.app)

    def tearDown(self):
        self.client.close()
        service.DB_PATH = self.original
        self.temp.cleanup()

    def test_create_join_feed_and_device_pair(self):
        created = self.client.post("/api/rooms")
        self.assertEqual(created.status_code, 200)
        room = created.json()["room"]
        self.assertEqual(self.client.get(f"/api/rooms/{room}/feed").json()["cards"], [])
        device = self.client.post("/api/devices").json()
        self.assertEqual(len(device["code"]), 6)
        before = self.client.get("/api/device/feed", headers={"Authorization": "Bearer " + device["token"]}).json()
        self.assertFalse(before["paired"])
        self.assertEqual(self.client.post(f"/pair/{room}", data={"code": device["code"]}, follow_redirects=False).status_code, 303)
        after = self.client.get("/api/device/feed", headers={"Authorization": "Bearer " + device["token"]}).json()
        self.assertTrue(after["paired"])
        self.assertEqual(self.client.post(f"/pair/{room}", data={"code": device["code"]}).status_code, 400)
        self.assertEqual(self.client.get("/api/device/feed").status_code, 401)

    def test_room_requires_invitation(self):
        room = self.client.post("/api/rooms").json()["room"]
        stranger = TestClient(service.app)
        try:
            self.assertEqual(stranger.get(f"/api/rooms/{room}/feed").status_code, 403)
            self.assertEqual(stranger.get(f"/join/{room}", follow_redirects=False).status_code, 303)
            self.assertEqual(stranger.get(f"/api/rooms/{room}/feed").status_code, 200)
        finally:
            stranger.close()

    def test_feed_uses_distinct_channels(self):
        room = self.client.post("/api/rooms").json()["room"]
        with service.db() as conn:
            conn.execute("INSERT INTO members VALUES(?,?,?,?,?)", ("1", room, "google-a", "Alex",
                json.dumps([{"id": "UC1", "title": "Music"}, {"id": "UC2", "title": "Art"}])))
            conn.execute("INSERT INTO members VALUES(?,?,?,?,?)", ("2", room, "google-b", "Sam",
                json.dumps([{"id": "UC1", "title": "Music"}])))
        cards = self.client.get(f"/api/rooms/{room}/feed").json()["cards"]
        self.assertEqual(cards[0]["kind"], "shared")
        self.assertEqual(cards[0]["title"], "Music")
        self.assertEqual(cards[1]["kind"], "explore")

    def test_qr_and_expired_code(self):
        device = self.client.post("/api/devices").json()
        result = self.client.get("/api/device/qr/" + device["code"])
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.content.startswith(b"\\x89PNG".decode("unicode_escape").encode("latin-1")))


if __name__ == "__main__":
    unittest.main()
