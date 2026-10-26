# CommonGround — cross-interest discovery

Build a Roku SceneGraph channel that connects different interests across consented feeds, rather than requiring identical topics.

```sh
python3 examples/common_ground/build.py examples/common_ground/feeds.json dist/common-ground
python3 -m roku_ai package dist/common-ground --out dist/common-ground.zip
python3 -m unittest discover -s tests -v
```

Use the Roku remote's left/right or up/down buttons to browse recommended connections. Each card shows two connected interests, a human-authored explanation, and representative posts from different people.

The input JSON contains `people` with `id`, `name`, and `items` (each with `title` and `topics`). An optional `bridges` array contains `from`, `to`, and `reason` fields. Bridges are explicit, auditable editorial relationships; no semantic model or social API is required. Rankings count distinct participants and cross-person pairs, not raw posts from one person. Ties are deterministic.

The generated package is a **static interactive discovery feed**. It does not fetch live feeds, play media, provide authentication, or claim Roku certification. It requires sideloading on a developer-enabled Roku device for on-device validation.
