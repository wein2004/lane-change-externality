"""Assemble the deck's slide files into one printable HTML page.

The slides are written in the Slides artifact's inline-style subset, which is
plain HTML and CSS, so a browser renders them as-is. Two things have to be
added for a standalone print:

  * `position:relative` on each section, so the pinned footers resolve against
    their own slide rather than the page.
  * a @page box of exactly 1920x1080px, so one slide is one PDF page with no
    scaling or margins.

Speaker notes (<aside>) are hidden - they are for the presenter, not the export.
"""
from pathlib import Path
import json
import re

HERE = Path(__file__).parent
DECK = HERE / "deck" / "project"

deck = json.loads((DECK / "deck.json").read_text(encoding="utf-8"))
order = deck["order"]

# Google Fonts links, one per declared face.
links = "\n  ".join(
    f'<link rel="stylesheet" href="{f["href"]}">'
    for f in deck["faces"].values() if "href" in f
)

# `/_blob/<id>` resolves only inside the artifact. For a standalone print the
# images have to point at the local PNGs the figures were uploaded from.
FIGURES = Path("D:/港中大2026數據黑克松/outputs/figures")
BLOBS = {
    "/_blob/7fa453801f93c4f75c2a188288d91d09": "fig1_speed_profile.png",
    "/_blob/3f23918b07a9953506e359fb845da941": "fig2_cost_by_regime.png",
    "/_blob/62b61e757d7c84b97f8ec3409b22a158": "fig3_truck_penalty.png",
}

sections = []
for sid in order:
    html = (DECK / "slides" / f"{sid}.html").read_text(encoding="utf-8")
    # Pin context for the absolutely positioned footers.
    html = html.replace(
        f'<section id="{sid}"', f'<section data-slide="{sid}"', 1
    )
    html = re.sub(r'(<section[^>]*style=")', r'\1position:relative; ', html, count=1)
    for blob, name in BLOBS.items():
        html = html.replace(blob, (FIGURES / name).resolve().as_uri())
    sections.append(html)

page = f'''<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>{deck["title"]}</title>
  {links}
  <style>
    @page {{ size: 1920px 1080px; margin: 0; }}
    html, body {{ margin: 0; padding: 0; background: #FFFFFF; }}
    section {{
      width: 1920px; height: 1080px; overflow: hidden;
      box-sizing: border-box; break-after: page; page-break-after: always;
    }}
    section:last-of-type {{ break-after: auto; page-break-after: auto; }}
    section * {{ box-sizing: border-box; }}
    h1, h2, h3, p, ul, ol {{ margin: 0; }}
    aside {{ display: none; }}
    img {{ display: block; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #E4E4E4; }}
    hr {{ border: 0; margin: 0; }}
  </style>
</head>
<body>
{chr(10).join(sections)}
</body>
</html>'''

out = HERE / "deck_print.html"
out.write_text(page, encoding="utf-8")
print(f"wrote {out} ({len(order)} slides, {len(page):,} bytes)")
