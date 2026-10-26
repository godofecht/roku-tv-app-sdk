"""CommonGround mobile account-linking server (stdlib only).

Requires HTTPS at the public reverse proxy and Google OAuth web credentials.
Tokens are exchanged in memory and discarded after retrieving subscriptions.
"""
import html
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
BASE_URL = os.environ.get("COMMON_GROUND_BASE_URL", "http://localhost:8765").rstrip("/")
REDIRECT_URI = BASE_URL + "/oauth/callback"
SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
LOCK = threading.Lock()
PENDING = {}
PEOPLE = {}
STATE_TTL = 600
MAX_PEOPLE = 20


def fetch_json(url, data=None, token=None):
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(data).encode("utf-8")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def youtube_subscriptions(token):
    channels = {}
    page = None
    for _ in range(20):
        query = {"part": "snippet", "mine": "true", "maxResults": "50"}
        if page:
            query["pageToken"] = page
        url = "https://www.googleapis.com/youtube/v3/subscriptions?" + urllib.parse.urlencode(query)
        payload = fetch_json(url, token=token)
        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            resource = snippet.get("resourceId", {})
            cid = resource.get("channelId")
            title = snippet.get("title")
            if cid and title:
                channels[cid] = title
        page = payload.get("nextPageToken")
        if not page:
            break
    return [{"id": cid, "title": title} for cid, title in sorted(channels.items())]


def recommendations():
    with LOCK:
        people = list(PEOPLE.values())
    index = {}
    for person in people:
        for channel in person["channels"]:
            entry = index.setdefault(channel["id"], {"channel": channel["title"], "people": []})
            entry["people"].append(person["name"])
    shared = [entry for entry in index.values() if len(entry["people"]) >= 2]
    return sorted(shared, key=lambda x: (-len(x["people"]), x["channel"].casefold()))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#101c2b"><title>CommonGround</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#101c2b;color:#f5f8ff}
body{margin:0;padding:20px;max-width:720px;margin-inline:auto}
h1{font-size:2.2rem;margin-bottom:8px}p{line-height:1.5;color:#c6d2e5}
section{background:#1c3046;padding:20px;border-radius:16px;margin:18px 0}
a.button,button{display:inline-block;background:#86dfc2;color:#102235;padding:14px 20px;border-radius:12px;text-decoration:none;font-weight:700;border:0}
input{padding:14px;border-radius:8px;border:1px solid #8394ab;background:#101c2b;color:white;width:100%;box-sizing:border-box;margin:12px 0}
li{padding:8px 0}small{color:#b5c5d9}
</style></head><body>
<h1>CommonGround</h1><p>Find what connects your YouTube worlds.</p>
<section><h2>Connect your YouTube</h2>
<p>Each person uses this page on their own phone. Google will ask permission to read their YouTube account. We only retain the channel subscriptions needed for this session, not Google access tokens.</p>
<form action="/connect" method="get"><label for="name">Your display name</label>
<input id="name" name="name" maxlength="50" required placeholder="Your name">
<button type="submit">Connect with Google</button></form></section>
<section><h2>People connected</h2>__PEOPLE__</section>
<section><h2>Shared channels</h2>__SHARED__</section>
<section><h2>Watch on Roku</h2><p>For testing, enable Roku Developer Mode, open its developer installer in a browser on your local network, and upload the CommonGround ZIP. This is not an automatic consumer install.</p>
<p><a href="/setup">TV setup instructions</a></p></section>
<small>Only connect accounts with their owners' consent. This prototype keeps subscriptions in server memory until restart; do not expose it publicly without authentication, HTTPS and durable privacy controls.</small>
</body></html>"""


def render_page():
    with LOCK:
        people = list(PEOPLE.values())
    names = "<ul>" + "".join("<li>" + html.escape(p["name"]) + " — " + str(len(p["channels"])) + " channels</li>" for p in people) + "</ul>" if people else "<p>No accounts linked yet.</p>"
    shared = recommendations()
    links = "<ul>" + "".join("<li>" + html.escape(s["channel"]) + " — " + ", ".join(html.escape(n) for n in s["people"]) + "</li>" for s in shared[:30]) + "</ul>" if shared else "<p>Connect at least two people to discover shared subscriptions.</p>"
    return PAGE.replace("__PEOPLE__", names).replace("__SHARED__", links)


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, body, content_type="text/html; charset=utf-8", extra=None):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
        if extra:
            for key, value in extra.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)
        if url.path == "/":
            return self.respond(200, render_page())
        if url.path == "/setup":
            body = """<meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Roku setup</title><h1>Install CommonGround on Roku (developer testing)</h1>
            <p>On Roku, enable Developer Mode using the documented Roku remote shortcut,
            then set the developer installer password and note the device IP address.</p>
            <p>On a computer on the same network, open http://ROKU_IP in a browser,
            sign in with the Roku developer installer credentials and upload the generated ZIP.</p>
            <p>Build ZIP: <code>python3 examples/common_ground/build.py examples/common_ground/feeds.json dist/common-ground</code>
            then <code>python3 -m roku_ai package dist/common-ground --out dist/common-ground.zip</code>.</p>
            <p>For ordinary viewers, publish through Roku's channel certification and distribution process.</p><p><a href="/">Back</a></p>"""
            return self.respond(200, body)
        if url.path == "/connect":
            name = query.get("name", [""])[0].strip()
            if not 1 <= len(name) <= 50 or not CLIENT_ID or not CLIENT_SECRET:
                return self.respond(400, "Invalid name or missing Google OAuth configuration.")
            with LOCK:
                if len(PEOPLE) >= MAX_PEOPLE:
                    return self.respond(429, "Session is full.")
                now = time.time()
                for key in list(PENDING):
                    if now - PENDING[key][1] > STATE_TTL:
                        del PENDING[key]
                state = secrets.token_urlsafe(32)
                PENDING[state] = (name, now)
            params = {
                "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
                "response_type": "code", "scope": SCOPE,
                "state": state, "access_type": "online",
                "include_granted_scopes": "false"
            }
            self.send_response(302)
            self.send_header("Location", "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Set-Cookie", "cg_oauth=" + state + "; HttpOnly; SameSite=Lax; Path=/oauth/callback" + ("; Secure" if BASE_URL.startswith("https://") else ""))
            self.end_headers()
            return
        if url.path == "/oauth/callback":
            state = query.get("state", [""])[0]
            cookies = dict(part.strip().split("=", 1) for part in self.headers.get("Cookie", "").split(";") if "=" in part)
            if not state or not secrets.compare_digest(state, cookies.get("cg_oauth", "")):
                return self.respond(400, "OAuth state mismatch.")
            code = query.get("code", [""])[0]
            with LOCK:
                pending = PENDING.pop(state, None)
            if not pending or time.time() - pending[1] > STATE_TTL or not code:
                return self.respond(400, "Expired, rejected, or invalid authorization.")
            try:
                token = fetch_json("https://oauth2.googleapis.com/token", {
                    "code": code, "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code"
                })["access_token"]
                channels = youtube_subscriptions(token)
                with LOCK:
                    if len(PEOPLE) >= MAX_PEOPLE:
                        return self.respond(429, "Session is full.")
                    key = secrets.token_urlsafe(12)
                    PEOPLE[key] = {"name": pending[0], "channels": channels}
            except (urllib.error.URLError, ValueError, KeyError, TimeoutError):
                return self.respond(502, "Google authorization or YouTube fetch failed.")
            return self.respond(200, '<meta name="viewport" content="width=device-width,initial-scale=1"><h1>Connected!</h1><p>Your YouTube subscriptions have been added to CommonGround.</p><a href="/">View shared channels</a>')
        return self.respond(404, "Not found")


if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
    host = os.environ.get("COMMON_GROUND_HOST", "127.0.0.1")
    port = int(os.environ.get("COMMON_GROUND_PORT", "8765"))
    print("CommonGround listening at", BASE_URL)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
