"""CLI for creating and packaging minimal Roku SceneGraph applications."""
import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

DEFAULT = {
    "title": "My Roku App",
    "subtitle": "Built with Roku AI SDK",
    "version": "1.0.0",
    "background_color": "#182030"
}
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def validate(spec):
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    if set(spec) - set(DEFAULT):
        raise ValueError("unknown keys: " + ", ".join(sorted(set(spec) - set(DEFAULT))))
    for key in ("title", "subtitle"):
        value = spec.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError(key + " must be a nonempty string of at most 120 characters")
    if not isinstance(spec.get("version"), str) or not VERSION.fullmatch(spec["version"]):
        raise ValueError("version must be in X.Y.Z format")
    if not isinstance(spec.get("background_color"), str) or not COLOR.fullmatch(spec["background_color"]):
        raise ValueError("background_color must be a six-digit hex color")
    return spec


def build(spec, output):
    validate(spec)
    output = Path(output)
    (output / "source").mkdir(parents=True, exist_ok=True)
    (output / "components").mkdir(parents=True, exist_ok=True)
    major, minor, patch = spec["version"].split(".")
    manifest = (
        "title=" + spec["title"].replace("\n", " ") + "\n"
        + "major_version=" + major + "\n"
        + "minor_version=" + minor + "\n"
        + "build_version=" + patch + "\n"
        + "ui_resolutions=hd\n"
    )
    (output / "manifest").write_text(manifest, encoding="utf-8")
    (output / "source" / "main.brs").write_text(
        'sub Main()\n'
        '    screen = CreateObject("roSGScreen")\n'
        '    port = CreateObject("roMessagePort")\n'
        '    screen.SetMessagePort(port)\n'
        '    screen.CreateScene("MainScene")\n'
        '    screen.Show()\n'
        '    while true\n'
        '        msg = wait(0, port)\n'
        '        if type(msg) = "roSGScreenEvent" and msg.isScreenClosed() then exit while\n'
        '    end while\n'
        'end sub\n', encoding="utf-8"
    )
    scene = ET.Element("component", {"name": "MainScene", "extends": "Scene"})
    children = ET.SubElement(scene, "children")
    ET.SubElement(children, "Rectangle", {
        "width": "1280", "height": "720", "color": spec["background_color"]
    })
    ET.SubElement(children, "Label", {
        "id": "title", "text": spec["title"],
        "translation": "[80,220]", "width": "1120", "height": "100",
        "horizAlign": "center"
    })
    ET.SubElement(children, "Label", {
        "id": "subtitle", "text": spec["subtitle"],
        "translation": "[80,350]", "width": "1120", "height": "80",
        "horizAlign": "center"
    })
    ET.ElementTree(scene).write(output / "components" / "MainScene.xml", encoding="unicode", xml_declaration=True)


def package(source, target):
    source = Path(source)
    required = ["manifest", "source/main.brs", "components/MainScene.xml"]
    for path in required:
        if not (source / path).is_file():
            raise ValueError("missing generated file: " + path)
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            rel = path.relative_to(source).as_posix()
            if rel.startswith("../"):
                raise ValueError("invalid archive path")
            info = zipfile.ZipInfo(rel, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def main(argv=None):
    parser = argparse.ArgumentParser(prog="roku_ai")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="write a starter spec")
    init.add_argument("spec")
    build_cmd = commands.add_parser("build", help="generate Roku project")
    build_cmd.add_argument("spec")
    build_cmd.add_argument("--out", required=True)
    zip_cmd = commands.add_parser("package", help="create sideloadable ZIP")
    zip_cmd.add_argument("project")
    zip_cmd.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            path = Path(args.spec)
            with path.open("x", encoding="utf-8") as stream:
                json.dump(DEFAULT, stream, indent=2)
                stream.write("\n")
        elif args.command == "build":
            with open(args.spec, encoding="utf-8") as stream:
                spec = json.load(stream)
            build(spec, args.out)
        else:
            package(args.project, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, "error: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
