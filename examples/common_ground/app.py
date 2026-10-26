"""CommonGround room service: FastAPI + Authlib + SQLite.

Run with uvicorn examples.common_ground.app:app --host 0.0.0.0 --port 8765.
Use a public HTTPS reverse proxy and set PUBLIC_URL accordingly.
"""
import io
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote, parse_qs

import httpx
import qrcode
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

PUBLIC_URL = os.getenv("COMMON_GROUND_BASE_URL", "http://localhost:8765").rstrip("/")
DB_PATH = os.getenv("COMMON_GROUND_DB", "common_ground.sqlite3")
SECRET = os.getenv("COMMON_GROUND_SESSION_SECRET", "")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
if not SECRET:
    # Explicitly local-only until a stable secret is supplied.
    SECRET = secrets.token_urlsafe(32)
app = FastAPI(title="CommonGround", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET, same_site="lax", https_only=PUBLIC_URL.startswith("https://"))
oauth = OAuth()
if CLIENT_ID and CLIENT_SECRET:
    oauth.register(
        name="google", client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile https://www.googleapis.com/auth/youtube.readonly"},
    )


@contextmanager
def db():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS rooms(
          id TEXT PRIMARY KEY, admin_key TEXT NOT NULL, created INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS members(
          id TEXT PRIMARY KEY, room_id TEXT NOT NULL, google_sub TEXT NOT NULL,
          name TEXT NOT NULL, channels TEXT NOT NULL,
          UNIQUE(room_id, google_sub)
        );
        CREATE TABLE IF NOT EXISTS devices(
          code TEXT PRIMARY KEY, room_id TEXT, created INTEGER NOT NULL,
          device_token TEXT UNIQUE NOT NULL
        );
        """)
        yield connection
        connection.commit()
    finally:
        connection.close()


class RoomCreate(BaseModel):
    pass


class PairRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


def room_or_404(room_id):
    with db() as conn:
        row = conn.execute("SELECT id FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Unknown room")


def room_access(request, room_id):
    # Invitation grants read access to the room; never include admin key in invitations.
    if room_id not in request.session.get("rooms", []):
        raise HTTPException(403, "Open the invitation link first")


def feed_for(room_id):
    with db() as conn:
        rows = conn.execute("SELECT id,name,channels FROM members WHERE room_id=? ORDER BY id", (room_id,)).fetchall()
    members = [dict(id=r["id"], name=r["name"], channels=json.loads(r["channels"])) for r in rows]
    index = {}
    for member in members:
        for channel in member["channels"]:
            item = index.setdefault(channel["id"], {"channel_id": channel["id"], "title": channel["title"], "people": []})
            item["people"].append(member["name"])
    shared = [v for v in index.values() if len(v["people"]) > 1]
    shared.sort(key=lambda v: (-len(v["people"]), v["title"].casefold()))
    # Distinct channels by distinct people are a discovery pool, not falsely
    # claimed to be semantically related. True bridge scoring requires metadata.
    unique = [v for v in index.values() if len(v["people"]) == 1]
    unique.sort(key=lambda v: (v["title"].casefold(), v["channel_id"]))
    cards = [{"title": v["title"], "subtitle": ", ".join(v["people"]), "kind": "shared",
              "url": "https://www.youtube.com/channel/" + quote(v["channel_id"])} for v in shared]
    cards += [{"title": v["title"], "subtitle": "From " + v["people"][0], "kind": "explore",
               "url": "https://www.youtube.com/channel/" + quote(v["channel_id"])} for v in unique]
    return {"participants": len(members), "cards": cards[:100]}


@app.post("/api/rooms")
def create_room(request: Request):
    room_id, admin = secrets.token_urlsafe(9), secrets.token_urlsafe(24)
    with db() as conn:
        conn.execute("INSERT INTO rooms VALUES(?,?,?)", (room_id, admin, int(time.time())))
    request.session["rooms"] = list(set(request.session.get("rooms", []) + [room_id]))
    request.session["admins"] = list(set(request.session.get("admins", []) + [room_id]))
    return {"room": room_id, "invite": PUBLIC_URL + "/join/" + room_id, "dashboard": PUBLIC_URL + "/room/" + room_id}


@app.get("/join/{room_id}")
def join(room_id: str, request: Request):
    room_or_404(room_id)
    request.session["rooms"] = list(set(request.session.get("rooms", []) + [room_id]))
    return RedirectResponse("/room/" + room_id, status_code=303)


@app.get("/room/{room_id}", response_class=HTMLResponse)
def dashboard(room_id: str, request: Request):
    room_access(request, room_id)
    import html
    invite = PUBLIC_URL + "/join/" + room_id
    feed = feed_for(room_id)
    pair_code = request.query_params.get("pair", "")
    if len(pair_code) != 6 or not pair_code.isdecimal():
        pair_code = ""
    cards = "".join("<li>" + html.escape(c["title"]) + " — " + html.escape(c["subtitle"]) + "</li>" for c in feed["cards"][:30])
    return HTMLResponse(f"""<!doctype html><html lang="en"><head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta http-equiv="refresh" content="30">
    <title>CommonGround room</title>
    <style>body{{background:#101c2b;color:white;font:17px system-ui;max-width:650px;margin:auto;padding:24px}}
    a,button{{color:#102235;background:#8ee8c7;padding:12px;border-radius:9px;display:inline-block;margin:8px 0}}
    input{{padding:12px;width:90%}}li{{padding:8px}}</style></head><body>
    <h1>CommonGround</h1><p>{feed["participants"]} people connected</p>
    <h2>Invite friends</h2><input aria-label="Invite URL" readonly value="{html.escape(invite, quote=True)}">
    <p>Share this link privately. Anyone with the link can join the room.</p>
    <h2>Your YouTube account</h2><a href="/auth/google/{room_id}">Connect YouTube with Google</a>
    <h2>Connect a Roku TV</h2><form action="/pair/{room_id}" method="post">
    <label>Enter the six-digit code shown on TV <input name="code" value="{pair_code}" maxlength="6" pattern="[0-9]{{6}}" required></label>
    <button type="submit">Connect TV</button></form>
    <h2>Discover</h2><ul>{cards or "<li>Invite someone to get started</li>"}</ul>
    <p>Refreshes every 30 seconds. Only connect accounts you own or have permission to share.</p>
    </body></html>""")


@app.get("/api/rooms/{room_id}/feed")
def room_feed(room_id: str, request: Request):
    room_access(request, room_id)
    return feed_for(room_id)


@app.get("/auth/google/{room_id}")
async def google_login(room_id: str, request: Request):
    room_access(request, room_id)
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(503, "Google OAuth credentials not configured")
    request.session["oauth_room"] = room_id
    return await oauth.google.authorize_redirect(request, PUBLIC_URL + "/auth/callback")


@app.get("/auth/callback")
async def google_callback(request: Request):
    room_id = request.session.pop("oauth_room", None)
    if not room_id:
        raise HTTPException(400, "OAuth room expired")
    room_access(request, room_id)
    try:
        token = await oauth.google.authorize_access_token(request)
        profile = token.get("userinfo")
        if not profile:
            async with httpx.AsyncClient(timeout=15) as client:
                result = await client.get("https://openidconnect.googleapis.com/v1/userinfo",
                                          headers={"Authorization": "Bearer " + token["access_token"]})
                result.raise_for_status()
                profile = result.json()
        sub, name = profile["sub"], profile.get("name", "YouTube participant")
        channels = {}
        async with httpx.AsyncClient(timeout=15) as client:
            page = None
            for _ in range(20):
                params = {"part": "snippet", "mine": "true", "maxResults": 50}
                if page:
                    params["pageToken"] = page
                result = await client.get("https://www.googleapis.com/youtube/v3/subscriptions",
                                          params=params, headers={"Authorization": "Bearer " + token["access_token"]})
                result.raise_for_status()
                payload = result.json()
                for item in payload.get("items", []):
                    snippet = item.get("snippet", {})
                    cid = snippet.get("resourceId", {}).get("channelId")
                    if cid:
                        channels[cid] = snippet.get("title", cid)
                page = payload.get("nextPageToken")
                if not page:
                    break
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(502, "YouTube authorization failed") from exc
    with db() as conn:
        conn.execute("""INSERT INTO members(id,room_id,google_sub,name,channels)
                        VALUES(?,?,?,?,?) ON CONFLICT(room_id,google_sub)
                        DO UPDATE SET name=excluded.name,channels=excluded.channels""",
                     (secrets.token_urlsafe(12), room_id, sub, name,
                      json.dumps([{"id": k, "title": v} for k, v in sorted(channels.items())])))
    return RedirectResponse("/room/" + room_id, status_code=303)


@app.post("/api/devices")
def create_device():
    # Device displays a short code; never use code alone to read private feeds.
    now = int(time.time())
    with db() as conn:
        conn.execute("DELETE FROM devices WHERE created<?", (now - 86400,))
        for _ in range(10):
            code = str(secrets.randbelow(900000) + 100000)
            if not conn.execute("SELECT 1 FROM devices WHERE code=?", (code,)).fetchone():
                token = secrets.token_urlsafe(32)
                conn.execute("INSERT INTO devices VALUES(?,?,?,?)", (code, None, now, token))
                return {"code": code, "token": token, "pair_url": PUBLIC_URL}
    raise HTTPException(503, "Could not allocate device code")


@app.post("/pair/{room_id}")
async def pair(room_id: str, request: Request):
    room_access(request, room_id)
    form = parse_qs((await request.body()).decode("utf-8"))
    code = form.get("code", [""])[0]
    if len(code) != 6 or not code.isdecimal():
        raise HTTPException(400, "Invalid device code")
    with db() as conn:
        cursor = conn.execute("UPDATE devices SET room_id=? WHERE code=? AND room_id IS NULL AND created>?",
                              (room_id, code, int(time.time()) - 600))
        if cursor.rowcount != 1:
            raise HTTPException(400, "Code invalid, expired or already used")
    return RedirectResponse("/room/" + room_id, status_code=303)


@app.get("/api/device/feed")
def device_feed(request: Request):
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Device token required")
    token = authorization[7:]
    with db() as conn:
        row = conn.execute("SELECT room_id,code,created FROM devices WHERE device_token=?", (token,)).fetchone()
    if not row:
        raise HTTPException(401, "Unknown device")
    if not row["room_id"]:
        return {"paired": False, "code": row["code"], "cards": []}
    return {"paired": True, **feed_for(row["room_id"])}


@app.get("/api/device/qr/{code}")
def device_qr(code: str):
    with db() as conn:
        row = conn.execute("SELECT created FROM devices WHERE code=?", (code,)).fetchone()
    if not row or row["created"] < int(time.time()) - 600:
        raise HTTPException(404, "Device code expired")
    image = qrcode.make(PUBLIC_URL + "/?pair=" + code)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return Response(out.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/rooms/{room_id}/qr")
def qr(room_id: str, request: Request):
    room_access(request, room_id)
    image = qrcode.make(PUBLIC_URL + "/join/" + room_id)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return Response(out.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>CommonGround</title><style>body{font:20px system-ui;background:#101c2b;color:white;padding:32px}
    button{padding:18px;border-radius:12px;background:#8ee8c7}</style></head>
    <body><h1>CommonGround</h1><p>One stream, many perspectives.</p>
    <button id="start">Create private room</button><script>
    document.getElementById("start").onclick=async()=>{
      const r=await fetch("/api/rooms",{method:"POST"});if(r.ok){
      const data=await r.json();location.href="/room/"+data.room+"?pair="+encodeURIComponent(new URLSearchParams(location.search).get("pair")||"");}}
    </script></body></html>"""
