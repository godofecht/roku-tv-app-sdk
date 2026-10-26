"""Build a static Roku channel from consented multi-person feed exports."""
import json
import sys
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

# Allow execution from the repository root without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from roku_ai.__main__ import build as build_roku


def shared_topics(data):
    people = data.get("people")
    if not isinstance(people, list) or len(people) < 2:
        raise ValueError("provide at least two people")
    seen_ids = set()
    topics = defaultdict(lambda: {"people": set(), "posts": []})
    for person in people:
        if not isinstance(person, dict):
            raise ValueError("each person must be an object")
        pid, name = person.get("id"), person.get("name")
        if not isinstance(pid, str) or not pid or pid in seen_ids:
            raise ValueError("person IDs must be unique nonempty strings")
        seen_ids.add(pid)
        if not isinstance(name, str) or not name:
            raise ValueError("person name is required")
        items = person.get("items")
        if not isinstance(items, list):
            raise ValueError("items must be a list")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("title"), str):
                raise ValueError("each item needs a title")
            tags = item.get("topics")
            if not isinstance(tags, list) or any(not isinstance(t, str) or not t.strip() for t in tags):
                raise ValueError("topics must be a list of nonempty strings")
            for tag in set(t.strip().lower() for t in tags):
                entry = topics[tag]
                entry["people"].add(pid)
                entry["posts"].append((pid, name, item["title"]))
    ranked = []
    for topic, entry in topics.items():
        if len(entry["people"]) >= 2:
            ranked.append({
                "topic": topic,
                "people": len(entry["people"]),
                "posts": sorted(entry["posts"]),
            })
    return sorted(ranked, key=lambda x: (-x["people"], x["topic"]))


def generate(data, output):
    ranked = shared_topics(data)
    build_roku({
        "title": "CommonGround",
        "subtitle": "Shared interests, different perspectives",
        "version": "0.1.0",
        "background_color": "#101C2B"
    }, output)
    output = Path(output)
    scene = ET.Element("component", {"name": "MainScene", "extends": "Scene"})
    children = ET.SubElement(scene, "children")
    ET.SubElement(children, "Rectangle", {
        "width": "1280", "height": "720", "color": "#101C2B"
    })
    ET.SubElement(children, "Label", {
        "text": "CommonGround", "translation": "[70,35]",
        "width": "1140", "height": "80"
    })
    ET.SubElement(children, "Label", {
        "text": "Where your feeds meet", "translation": "[70,115]",
        "width": "1140", "height": "60"
    })
    for i, entry in enumerate(ranked[:5]):
        # Avoid excessive text and screen overflow on a 720p layout.
        preview = entry["posts"][0][2].replace("\n", " ")[:65]
        label = f'{entry["topic"].title()}  |  {entry["people"]} people  |  {preview}'
        ET.SubElement(children, "Label", {
            "text": label, "translation": f"[70,{205 + 90 * i}]",
            "width": "1140", "height": "72"
        })
    if not ranked:
        ET.SubElement(children, "Label", {
            "text": "No shared topics yet", "translation": "[70,240]",
            "width": "1140", "height": "80"
        })
    ET.ElementTree(scene).write(
        output / "components" / "MainScene.xml",
        encoding="unicode", xml_declaration=True
    )
    (output / "commonality.json").write_text(
        json.dumps(ranked, indent=2) + "\n", encoding="utf-8"
    )
    return ranked


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 examples/common_ground/build.py FEEDS.json OUTPUT_DIR")
    with open(sys.argv[1], encoding="utf-8") as stream:
        data = json.load(stream)
    generate(data, sys.argv[2])
