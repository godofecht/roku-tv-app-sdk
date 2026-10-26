import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "examples" / "common_ground" / "mobile_server.py"
spec = importlib.util.spec_from_file_location("cg_mobile", PATH)
mobile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mobile)


class MobileTests(unittest.TestCase):
    def setUp(self):
        with mobile.LOCK:
            mobile.PEOPLE.clear()

    def tearDown(self):
        with mobile.LOCK:
            mobile.PEOPLE.clear()

    def test_shared_subscriptions_count_distinct_people(self):
        with mobile.LOCK:
            mobile.PEOPLE["a"] = {"name": "Alex", "channels": [
                {"id": "UC1", "title": "Music"}, {"id": "UC2", "title": "Travel"}]}
            mobile.PEOPLE["b"] = {"name": "Sam", "channels": [
                {"id": "UC1", "title": "Music"}]}
        result = mobile.recommendations()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["people"], ["Alex", "Sam"])

    def test_escapes_participant_names(self):
        with mobile.LOCK:
            mobile.PEOPLE["a"] = {"name": "<script>alert(1)</script>", "channels": []}
        page = mobile.render_page()
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    @patch.object(mobile, "fetch_json")
    def test_youtube_pagination(self, fetch):
        fetch.side_effect = [
            {"items": [{"snippet": {"resourceId": {"channelId": "UC1"}, "title": "Music"}}], "nextPageToken": "NEXT"},
            {"items": [{"snippet": {"resourceId": {"channelId": "UC2"}, "title": "Travel"}}]}
        ]
        self.assertEqual(len(mobile.youtube_subscriptions("fake")), 2)
        self.assertIn("pageToken=NEXT", fetch.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
