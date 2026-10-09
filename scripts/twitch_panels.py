"""Render Twitch channel panels as a metrics-style SVG (same look as the AniList plugin).

Usage: uv run --with pillow python scripts/twitch_panels.py
"""
import base64
import hashlib
import io
import json
import pathlib
import re
import urllib.request

from PIL import Image, ImageOps

LOGIN = "iseedeadp3ople"
OUTPUT = "metrics/panels.svg"
PER_ROW = 8
ROWS = 7
TILE_W, TILE_H, GAP = 52, 78, 6
# Panels with photos of real people
EXCLUDED = {
    "136592081", "135154154", "135154146", "127259493", "124329055",
    "122036414", "122138582", "122138151", "122617283", "124068579",
}
# Panels the user asked to remove
EXCLUDED |= {"124329031"}

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = (ROOT / "scripts/metrics.css").read_text()
ICONS = json.loads((ROOT / "scripts/icons.json").read_text())

QUERY = '{user(login:"%s"){panels{id ... on DefaultPanel{imageURL linkURL}}}}' % LOGIN


def fetch(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def thumbnail(url, width, height):
    image = Image.open(io.BytesIO(fetch(url))).convert("RGB")
    image = ImageOps.fit(image, (width * 2, height * 2), Image.LANCZOS, centering=(0.5, 0.3))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def icon(name):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">{ICONS[name]}</svg>'


def main():
    body = json.dumps({"query": QUERY}).encode()
    headers = {"Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko", "Content-Type": "application/json"}
    user = json.loads(fetch("https://gql.twitch.tv/gql", body, headers))["data"]["user"]

    panels = [
        p for p in user["panels"]
        if p.get("imageURL") and not p.get("linkURL") and p["id"] not in EXCLUDED
    ][: PER_ROW * ROWS]
    tiles = "".join(
        f'<img src="{thumbnail(p["imageURL"], TILE_W, TILE_H)}" width="{TILE_W}" height="{TILE_H}" style="border-radius:7px;display:block" alt="" />' for p in panels
    )

    rows = -(-len(panels) // PER_ROW)
    height = 40 + rows * (TILE_H + GAP)
    grid = (
        f"display:grid;grid-template-columns:repeat({PER_ROW},{TILE_W}px);gap:{GAP}px;"
        f"margin:4px 0 0 10px"
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}">
<style>{CSS}</style>
<foreignObject x="0" y="0" width="100%" height="100%">
<div xmlns="http://www.w3.org/1999/xhtml" class="items-wrapper">
<section>
  <h2 class="field">{icon("heart")} Favorites panels</h2>
  <div style="{grid}">{tiles}</div>
</section>
</div>
</foreignObject>
</svg>
"""
    (ROOT / OUTPUT).write_text(svg)
    # Version query in README so GitHub's image cache picks up the new file
    version = hashlib.sha1(svg.encode()).hexdigest()[:8]
    readme = ROOT / "README.md"
    pattern = re.escape(OUTPUT) + r"(\?v=\w+)?"
    readme.write_text(re.sub(pattern, f"{OUTPUT}?v={version}", readme.read_text()))
    print(f"{OUTPUT}: {len(panels)} panels, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
