# Roku AI App SDK

A dependency-free, AI-friendly toolkit for generating Roku SceneGraph apps from a declarative JSON specification.

## Quick start

```bash
python3 -m roku_ai init example.json
python3 -m roku_ai build example.json --out dist/demo
python3 -m roku_ai package dist/demo --out dist/demo.zip
python3 -m unittest discover -s tests -v
```

The generated app contains `manifest`, `source/main.brs`, and `components/MainScene.xml`. Sideload the ZIP through the Roku developer installer after enabling Developer Mode on your own Roku device.

## Spec

```json
{
  "title": "My Roku App",
  "subtitle": "Built with AI",
  "version": "1.0.0",
  "background_color": "#182030"
}
```

This first version supports a static SceneGraph landing screen, deterministic packaging, JSON validation, and a stable CLI suitable for coding agents. It does not yet implement media playback, authentication, device deployment, or the Roku certification pipeline.

See [AGENTS.md](AGENTS.md) for agent instructions. Python 3.9+; no external dependencies.
