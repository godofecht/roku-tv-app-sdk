# CommonGround: mobile-to-Roku end-to-end setup

The **new** room service is `examples/common_ground/app.py`. The older `mobile_server.py` is retained for compatibility, but it does not support rooms or TV pairing.

## Run locally

```sh
python3 -m pip install -r examples/common_ground/requirements.txt
export COMMON_GROUND_SESSION_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export COMMON_GROUND_BASE_URL="http://localhost:8765"
export COMMON_GROUND_DB="./common_ground.sqlite3"
uvicorn examples.common_ground.app:app --host 127.0.0.1 --port 8765
```

Open http://localhost:8765 and create a room. Share the invitation link with friends. For Google account linking, create a Google Cloud OAuth **web client**, enable YouTube Data API v3, configure the consent screen and test users, and add `https://YOUR_HOST/auth/callback` to authorized redirect URIs. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `COMMON_GROUND_BASE_URL=https://YOUR_HOST` on the server. Use a public HTTPS reverse proxy. Each participant explicitly authorizes the YouTube read-only scope.

**Do not put OAuth client secrets in the Roku ZIP.** Access tokens are used for the subscription fetch and discarded. The server persists only subscription channel IDs/titles and account subject/name in SQLite. Back up and protect the database; there is no refresh-token collection.

## Build and sideload the live TV channel

```sh
export COMMON_GROUND_BASE_URL="https://YOUR_HOST"
python3 examples/common_ground/build_live.py examples/common_ground/feeds.json dist/common-ground-live
python3 -m roku_ai package dist/common-ground-live --out dist/common-ground-live.zip
```

The generated Roku app calls the configured server over HTTPS; the URL must be reachable from the TV and use a publicly trusted TLS certificate. The default localhost URL **will not work on a Roku device**. Enable Roku Developer Mode, open its developer installer at `http://ROKU_IP` on the same LAN, authenticate, and upload the ZIP. On TV, scan the QR code or open the companion URL, create a room, and enter the displayed six-digit code. The TV then polls for updated cards every ten seconds.

Developer sideloading is not consumer one-click installation. Consumer distribution requires Roku certification and publishing; the service does not install channels without that process.

## Current limitations and production readiness

- Rooms are invitation-link based, not fully authenticated membership systems. Anyone with an invitation URL can read that room's feed; share links only with trusted participants.
- SQLite persists subscriptions and room/device tokens. There is not yet a self-service participant removal or room deletion UI, retention schedule, account unlinking, rate limiting, audit logging, or public-hosting security review.
- The TV feed shows channel discovery cards, **not video playback**. Direct Roku playback of YouTube videos cannot be assumed permissible or technically available through the YouTube Data API. Video playback requires separately licensed/authorized playable streams and platform-compliant integration.
- The live feed ranks common subscriptions first and then surfaces channels unique to individual participants. The earlier curated cross-interest bridge engine is not yet wired to live subscription metadata; this is not semantic recommendation.
- Google API quota, consent verification, Roku hardware behavior, and deployment are external acceptance requirements. Automated tests use mock data and do not assert production OAuth success or Roku certification.

## Validate

```sh
python3 -m unittest discover -s tests -v
python3 examples/common_ground/build_live.py examples/common_ground/feeds.json dist/common-ground-live
python3 -m roku_ai package dist/common-ground-live --out dist/common-ground-live.zip
```

GitHub Actions performs unit/integration tests, build, and ZIP structure checks across operating systems and Python versions.
