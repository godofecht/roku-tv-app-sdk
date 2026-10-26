"""Generate Roku channel with live CommonGround room pairing and feed polling.

Usage: python examples/common_ground/build_live.py INPUT.json OUTPUT_DIR
Set COMMON_GROUND_BASE_URL to the public HTTPS server origin.
"""
import json
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from build import generate

SERVER = os.getenv("COMMON_GROUND_BASE_URL", "http://localhost:8765").rstrip("/")


def build_live(data, output):
    generate(data, output)
    output = Path(output)
    scene = ET.Element("component", {"name": "MainScene", "extends": "Scene"})
    ET.SubElement(scene, "script", {"type": "text/brightscript", "uri": "pkg:/components/MainScene.brs"})
    children = ET.SubElement(scene, "children")
    ET.SubElement(children, "Rectangle", {"width": "1280", "height": "720", "color": "#101C2B"})
    for name, y in [("heading", 35), ("status", 130), ("title", 260), ("detail", 370), ("hint", 600)]:
        ET.SubElement(children, "Label", {"id": name, "translation": f"[70,{y}]", "width": "1140", "height": "100"})
    ET.SubElement(children, "Poster", {"id": "pairQR", "translation": "[950,120]", "width": "220", "height": "220"})
    ET.SubElement(children, "FeedTask", {"id": "feedTask"})
    ET.ElementTree(scene).write(output / "components/MainScene.xml", encoding="unicode", xml_declaration=True)
    task = ET.Element("component", {"name": "FeedTask", "extends": "Task"})
    interface = ET.SubElement(task, "interface")
    for name in ("pairCode", "feedJson"):
        ET.SubElement(interface, "field", {"id": name, "type": "string"})
    ET.SubElement(task, "script", {"type": "text/brightscript", "uri": "pkg:/components/FeedTask.brs"})
    ET.ElementTree(task).write(output / "components/FeedTask.xml", encoding="unicode", xml_declaration=True)
    (output / "components/FeedTask.brs").write_text(TASK.replace("__SERVER__", SERVER.replace('"', '')), encoding="utf-8")
    (output / "components/MainScene.brs").write_text(SCENE.replace("__SERVER__", SERVER), encoding="utf-8")


TASK = '''sub init()
    m.top.functionName = "run"
end sub

function requestJson(path as String, token as String, method as String) as Dynamic
    x = CreateObject("roUrlTransfer")
    x.SetUrl("__SERVER__" + path)
    x.SetCertificatesFile("common:/certs/ca-bundle.crt")
    x.InitClientCertificates()
    if token <> "" then x.AddHeader("Authorization", "Bearer " + token)
    if method = "POST" then
        x.AddHeader("Content-Type", "application/json")
        body = x.PostFromString("{}")
    else
        body = x.GetToString()
    end if
    if x.GetResponseCode() < 200 or x.GetResponseCode() >= 300 then return invalid
    if body = invalid or body = "" then return invalid
    return ParseJson(body)
end function

sub run()
    section = CreateObject("roRegistrySection", "CommonGround")
    token = section.Read("deviceToken")
    if token = invalid then token = ""
    if token = "" then
        pairing = requestJson("/api/devices", "", "POST")
        if pairing = invalid then
            m.top.pairCode = "Server unavailable. Check network and server URL."
            return
        end if
        token = pairing.token
        section.Write("deviceToken", token)
        section.Flush()
        m.top.pairCode = pairing.code
    end if
    pairCode = m.top.pairCode
    while true
        data = requestJson("/api/device/feed", token, "GET")
        if data <> invalid then
            if data.paired = true then
                m.top.pairCode = ""
                m.top.feedJson = FormatJson(data)
            else
                m.top.pairCode = pairCode
            end if
        end if
        sleep(10000)
    end while
end sub
'''

SCENE = '''sub init()
    m.heading = m.top.findNode("heading")
    m.status = m.top.findNode("status")
    m.qr = m.top.findNode("pairQR")
    m.title = m.top.findNode("title")
    m.detail = m.top.findNode("detail")
    m.hint = m.top.findNode("hint")
    m.heading.text = "CommonGround"
    m.hint.text = "LEFT / RIGHT: discover channels"
    m.cards = []
    m.index = 0
    m.task = m.top.findNode("feedTask")
    m.task.observeField("pairCode", "onPair")
    m.task.observeField("feedJson", "onFeed")
    m.task.control = "RUN"
    m.top.setFocus(true)
end sub

sub onPair()
    if m.task.pairCode = "" then
        m.qr.visible = false
        return
    end if
    m.status.text = "Scan QR or open companion app. TV code: " + m.task.pairCode
    m.qr.uri = "__SERVER__/api/device/qr/" + m.task.pairCode
end sub

sub onFeed()
    data = ParseJson(m.task.feedJson)
    if data = invalid then return
    if data.cards = invalid then return
    m.cards = data.cards
    if m.index >= m.cards.count() then m.index = 0
    renderCard()
end sub

sub renderCard()
    if m.cards.count() = 0 then
        m.title.text = "Waiting for subscriptions"
        m.detail.text = "Invite friends to connect YouTube on their phones"
        return
    end if
    card = m.cards[m.index]
    m.status.text = Str(m.index + 1).Trim() + " / " + Str(m.cards.count()).Trim()
    m.title.text = card.title
    m.detail.text = card.kind + " | " + card.subtitle
end sub

function onKeyEvent(key as String, press as Boolean) as Boolean
    if not press or m.cards.count() = 0 then return false
    if key = "right" or key = "down" then
        m.index = (m.index + 1) mod m.cards.count()
    else if key = "left" or key = "up" then
        m.index = (m.index + m.cards.count() - 1) mod m.cards.count()
    else
        return false
    end if
    renderCard()
    return true
end function
'''


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_live.py FEEDS.json OUTPUT_DIR")
    with open(sys.argv[1], encoding="utf-8") as stream:
        build_live(json.load(stream), sys.argv[2])
