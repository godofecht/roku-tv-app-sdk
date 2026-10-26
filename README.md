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

## Continuous integration

[GitHub Actions CI](https://github.com/godofecht/roku-tv-app-sdk/actions/workflows/ci.yml) validates Python 3.9/3.11/3.13 on Ubuntu, macOS, and Windows, including unit tests, both Roku app builds, generated SceneGraph XML, and package integrity. Roku device execution and Google OAuth integration still require external credentials and hardware.

## CommonGround mobile-to-TV app

The room-based mobile app and live Roku pairing workflow are in [CommonGround end-to-end setup](examples/common_ground/END_TO_END.md). Start the FastAPI companion with `uvicorn examples.common_ground.app:app` after installing `examples/common_ground/requirements.txt`. Build the live Roku app using `examples/common_ground/build_live.py`. Google OAuth credentials, HTTPS hosting, Roku developer installation, and real-device verification are required; this is not yet a published consumer channel or a YouTube video player.

## Download portal

[CommonGround Downloads (GitHub Pages)](https://godofecht.github.io/roku-tv-app-sdk/) lists the latest published Roku release ZIP assets, CI artifacts, source downloads, and mobile companion setup. The page deploys via [Pages workflow](https://github.com/godofecht/roku-tv-app-sdk/actions/workflows/pages.yml); enable **Settings → Pages → Build and deployment → GitHub Actions** if deployment is not enabled. No release ZIP is advertised as downloadable until GitHub has actually published it.
