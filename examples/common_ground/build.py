"""Build a static Roku channel from consented multi-person feed exports."""
import json
import sys
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent))
from discovery import discover

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
    recommendations = discover(data)
    build_roku({
        "title": "CommonGround",
        "subtitle": "Discover connections between different interests",
        "version": "0.2.0",
        "background_color": "#101C2B"
    }, output)
    output = Path(output)
    scene = ET.Element("component", {"name": "MainScene", "extends": "Scene"})
    ET.SubElement(scene, "script", {"type": "text/brightscript", "uri": "pkg:/components/MainScene.brs"})
    children = ET.SubElement(scene, "children")
    ET.SubElement(children, "Rectangle", {
        "width": "1280", "height": "720", "color": "#101C2B"
    })
    for ident, y, height in [
        ("heading", 35, 80), ("counter", 130, 55),
        ("topics", 220, 80), ("reason", 320, 100),
        ("people", 460, 100), ("hint", 630, 60)
    ]:
        ET.SubElement(children, "Label", {
            "id": ident, "translation": f"[70,{y}]",
            "width": "1140", "height": str(height)
        })
    ET.ElementTree(scene).write(
        output / "components" / "MainScene.xml",
        encoding="unicode", xml_declaration=True
    )
    def clean(value, limit=100):
        return str(value).replace("\\n", " ").replace("\\r", " ")[:limit]
    cards = []
    for entry in recommendations:
        cards.append({
            "topics": clean(entry["from"].title() + " + " + entry["to"].title()),
            "reason": clean(entry["reason"]),
            "people": clean(entry["left"]["person"] + ": " + entry["left"]["title"]
                            + " / " + entry["right"]["person"] + ": " + entry["right"]["title"])
        })
    def brs(value):
        # JSON strings are valid BrightScript string literals only after
        # replacing JSON escape sequences and doubling quote characters.
        return '"' + clean(value).replace('"', '""') + '"'
    lines = [
        "sub init()",
        '    m.heading = m.top.findNode("heading")',
        '    m.counter = m.top.findNode("counter")',
        '    m.topics = m.top.findNode("topics")',
        '    m.reason = m.top.findNode("reason")',
        '    m.people = m.top.findNode("people")',
        '    m.hint = m.top.findNode("hint")',
        '    m.heading.text = "CommonGround | Cross-interest discovery"',
        '    m.hint.text = "LEFT / RIGHT to browse connections"',
        '    m.cards = []',
    ]
    for card in cards:
        lines.append("    m.cards.push({topics: " + brs(card["topics"])
                     + ", reason: " + brs(card["reason"])
                     + ", people: " + brs(card["people"]) + "})")
    lines += [
        "    m.index = 0",
        "    renderCard()",
        "    m.top.setFocus(true)",
        "end sub",
        "",
        "sub renderCard()",
        "    if m.cards.count() = 0 then",
        '        m.counter.text = "No cross-interest bridges found"',
        '        m.topics.text = "Add bridges between different feed topics"',
        '        m.reason.text = ""',
        '        m.people.text = ""',
        "        return",
        "    end if",
        "    card = m.cards[m.index]",
        '    m.counter.text = str(m.index + 1).trim() + " / " + str(m.cards.count()).trim()',
        "    m.topics.text = card.topics",
        "    m.reason.text = card.reason",
        "    m.people.text = card.people",
        "end sub",
        "",
        "function onKeyEvent(key as String, press as Boolean) as Boolean",
        "    if not press or m.cards.count() = 0 then return false",
        '    if key = "right" or key = "down" then',
        "        m.index = (m.index + 1) mod m.cards.count()",
        '    else if key = "left" or key = "up" then',
        "        m.index = (m.index + m.cards.count() - 1) mod m.cards.count()",
        "    else",
        "        return false",
        "    end if",
        "    renderCard()",
        "    return true",
        "end function",
    ]
    (output / "components" / "MainScene.brs").write_text(
        "\\n".join(lines) + "\\n", encoding="utf-8"
    )
    (output / "commonality.json").write_text(
        json.dumps(recommendations, indent=2) + "\\n", encoding="utf-8"
    )
    return recommendations


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 examples/common_ground/build.py FEEDS.json OUTPUT_DIR")
    with open(sys.argv[1], encoding="utf-8") as stream:
        data = json.load(stream)
    generate(data, sys.argv[2])
