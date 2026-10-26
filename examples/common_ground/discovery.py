"""Deterministic cross-interest bridge ranking for consented feeds."""
from collections import defaultdict


def discover(data):
    people = data.get("people")
    bridges = data.get("bridges", [])
    if not isinstance(people, list) or len(people) < 2:
        raise ValueError("at least two people required")
    if not isinstance(bridges, list):
        raise ValueError("bridges must be a list")
    owners = {}
    entries = defaultdict(list)
    for person in people:
        if not isinstance(person, dict):
            raise ValueError("invalid person")
        pid, name = person.get("id"), person.get("name")
        if not isinstance(pid, str) or not pid or pid in owners:
            raise ValueError("person IDs must be unique nonempty strings")
        if not isinstance(name, str) or not name:
            raise ValueError("person name required")
        owners[pid] = name
        if not isinstance(person.get("items"), list):
            raise ValueError("items must be a list")
        for item in person["items"]:
            if not isinstance(item, dict) or not isinstance(item.get("title"), str):
                raise ValueError("item title required")
            tags = item.get("topics")
            if not isinstance(tags, list) or any(not isinstance(t, str) or not t.strip() for t in tags):
                raise ValueError("topics must be nonempty strings")
            for tag in sorted(set(t.strip().lower() for t in tags)):
                entries[tag].append((pid, name, item["title"]))
    results = []
    used = set()
    for bridge in bridges:
        if not isinstance(bridge, dict):
            raise ValueError("invalid bridge")
        left, right, reason = bridge.get("from"), bridge.get("to"), bridge.get("reason")
        if not all(isinstance(v, str) and v.strip() for v in (left, right, reason)):
            raise ValueError("bridge requires from, to, reason")
        left, right = left.strip().lower(), right.strip().lower()
        if left == right:
            continue
        key = tuple(sorted((left, right)))
        if key in used:
            continue
        used.add(key)
        candidates = [(a, b) for a in entries[left] for b in entries[right] if a[0] != b[0]]
        if not candidates:
            continue
        distinct = set()
        for a, b in candidates:
            distinct.update((a[0], b[0]))
        a, b = min(candidates, key=lambda pair: (pair[0][0], pair[1][0], pair[0][2], pair[1][2]))
        results.append({
            "from": left, "to": right, "reason": reason.strip(),
            "people": len(distinct), "score": len(distinct) * 100 + len(set((x[0], y[0]) for x, y in candidates)),
            "left": {"person": a[1], "title": a[2]},
            "right": {"person": b[1], "title": b[2]}
        })
    return sorted(results, key=lambda x: (-x["score"], x["from"], x["to"]))
