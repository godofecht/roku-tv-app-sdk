# CommonGround

A proof-of-concept Roku channel that combines multiple people's feeds into a shared stream ordered by cross-person topic overlap.

Run:

```sh
python3 examples/common_ground/build.py examples/common_ground/feeds.json dist/common-ground
python3 -m roku_ai package dist/common-ground --out dist/common-ground.zip
python3 -m unittest discover -s tests -v
```

This MVP uses explicitly provided, consented feed data. It does not scrape social networks, infer private interests, or connect to social APIs. It builds a static, sideloadable Roku SceneGraph channel. The TV screen shows the highest-scoring shared topics and an example post for each topic; it is not yet an automatically updating video player.

Feed input has `people`, each with `id`, `name`, and `items`; each item has `title` and `topics`. A topic earns a higher score when it is represented by more distinct people. Multiple posts by one person do not increase cross-person coverage. Use meaningful shared topic identifiers; semantic similarity and inferred commonality are future work.
