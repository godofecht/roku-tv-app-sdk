# Mobile YouTube linking and Roku setup

## Start the mobile companion

Create a Google Cloud OAuth 2.0 **Web application** client. Enable **YouTube Data API v3**, configure its OAuth consent screen and test users if the app is in testing. Add an **Authorized redirect URI** matching `COMMON_GROUND_BASE_URL/oauth/callback`. Google may require verification before broader public use of YouTube scopes.

```sh
export GOOGLE_CLIENT_ID='your-client-id'
export GOOGLE_CLIENT_SECRET='your-client-secret'
export COMMON_GROUND_BASE_URL='https://your-domain.example'
python3 examples/common_ground/mobile_server.py
```

Put an HTTPS reverse proxy in front of the server; configure its public URL as `COMMON_GROUND_BASE_URL`. Share that URL with participants. Each person opens it on their phone, enters a display name, and authorizes read-only access to YouTube. The server fetches up to 1,000 channel subscriptions per account, then discards the access token. It keeps subscription names and IDs in server memory until restart. No Google credentials are sent to the Roku.

The web companion currently shows shared subscriptions, not the cross-interest bridge feed. Connecting the account-linking backend to live cross-interest recommendations and the Roku channel is a subsequent milestone. No user-authenticated room membership, participant deletion, persistent storage, refresh tokens, or production abuse controls exist yet. Do **not** deploy publicly with real user data until these are implemented and reviewed.

## Roku developer installation

Build the app ZIP from the repository:

```sh
python3 examples/common_ground/build.py examples/common_ground/feeds.json dist/common-ground
python3 -m roku_ai package dist/common-ground --out dist/common-ground.zip
```

Enable Roku Developer Mode on the device using Roku's documented developer shortcut, set a developer installer password, and note the Roku's IP address. From a browser on the same network, open `http://ROKU_IP`, authenticate to the developer installer, and upload `dist/common-ground.zip`. This is a developer sideload, not an end-user installation. For consumer-friendly installation, the channel must be submitted through Roku's official distribution/certification workflow.

## Privacy and limitations

All participants should explicitly consent to sharing subscription data with the group. The current prototype shows the linked accounts and their shared subscriptions to anyone who can access the server, so it is appropriate only for a trusted local test environment. The sample Roku app is a static discovery-card feed, not a live YouTube player. Roku playback of YouTube content may require separate permissions and must comply with YouTube API policies and Roku certification rules.
