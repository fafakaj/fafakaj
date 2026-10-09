"""Render Twitch channel panels as a metrics-style SVG (same look as the AniList plugin).

Usage: uv run --with pillow python scripts/twitch_panels.py
"""
import base64
import io
import json
import pathlib
import urllib.request
from html import escape

from PIL import Image, ImageOps

LOGIN = "iseedeadp3ople"
OUTPUT = "metrics/twitch.svg"
PER_ROW = 11
ROWS = 6
# Panels with photos of real people
EXCLUDED = {
    "136592081", "135154154", "135154146", "127259493", "124329055",
    "122036414", "122138582", "122138151", "122617283", "124068579",
}

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = (ROOT / "scripts/metrics.css").read_text()
ICONS = json.loads((ROOT / "scripts/icons.json").read_text())

QUERY = """{user(login:"%s"){displayName description profileImageURL(width:150)
followers{totalCount} lastBroadcast{game{displayName}}
panels{id ... on DefaultPanel{imageURL linkURL}}}}""" % LOGIN


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


def compact(number):
    return f"{number / 1000:.1f}k" if number >= 1000 else str(number)


def main():
    body = json.dumps({"query": QUERY}).encode()
    headers = {"Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko", "Content-Type": "application/json"}
    user = json.loads(fetch("https://gql.twitch.tv/gql", body, headers))["data"]["user"]

    panels = [
        p for p in user["panels"]
        if p.get("imageURL") and not p.get("linkURL") and p["id"] not in EXCLUDED
    ][: PER_ROW * ROWS]
    tiles = "".join(
        f'<img src="{thumbnail(p["imageURL"], 36, 54)}" width="36" height="54" alt="" />' for p in panels
    )

    name = escape(user["displayName"])
    followers = compact(user["followers"]["totalCount"])
    game = escape((user["lastBroadcast"] or {}).get("game", {}).get("displayName", "—"))
    about = escape(user["description"].split(" mail")[0].strip())
    avatar = thumbnail(user["profileImageURL"], 48, 72)
    rows = -(-len(panels) // PER_ROW)
    height = 220 + rows * 58

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}">
<style>{CSS}</style>
<foreignObject x="0" y="0" width="100%" height="100%">
<div xmlns="http://www.w3.org/1999/xhtml" class="items-wrapper">
<section>
  <h2 class="field">{icon("bookmark")} Twitch</h2>
  <div class="row fill-width"><section>
    <div class="field">{icon("tag")} Last stream: {game}</div>
  </section></div>
  <div class="row">
    <section><div class="field">{icon("video")} twitch.tv/{name}</div></section>
    <section><div class="field">{icon("heart")} {followers} followers</div></section>
  </div>
  <div class="row fill-width"><section><div class="anilist">
    <h2 class="field">{icon("list")} Featured channel</h2>
    <div class="medias"><div class="media">
      <img src="{avatar}" width="48" height="72" alt="" />
      <div class="about">
        <div class="name">{name}</div>
        <div class="infos">
          <div>{icon("video")} Twitch</div>
          <div>{icon("tag")} {game}</div>
          <div>{icon("thumbsup")} {followers}</div>
        </div>
        <div class="description">{about}</div>
      </div>
    </div></div>
    <h2 class="field">{icon("heart")} Favorites panels</h2>
    <div class="characters">{tiles}</div>
  </div></section></div>
</section>
</div>
</foreignObject>
</svg>
"""
    (ROOT / OUTPUT).write_text(svg)
    print(f"{OUTPUT}: {len(panels)} panels, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
