"""Render the same deck content as slide files for the online Slides artifact.

`scripts/slides_content.py` is the single source of truth; `05_build_pptx.py`
renders it to PowerPoint and this renders it to the artifact's inline-style
HTML subset, so the two decks cannot drift apart.

The artifact canvas is 1920x1080 px against PowerPoint's 13.333x7.5 in, so
every dimension here is the PPTX one multiplied by 144.

Usage: python scripts/06_build_web_deck.py --out <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from slides_content import DECK  # noqa: E402

BG, INK, SUB = "#FFFFFF", "#111111", "#6B6B6B"
RULE, BLUE, ORANGE, PANEL = "#E4E4E4", "#2A78D6", "#EB6834", "#F6F6F4"
COLORS = {"INK": INK, "SUB": SUB, "BLUE": BLUE, "ORANGE": ORANGE,
          "PANEL": PANEL, "RULE": RULE}

SANS = "'Noto Sans TC', Arial, sans-serif"
MARGIN, TOP = 122, 104
CONTENT_W = 1920 - 2 * MARGIN

# Uploaded asset urls, keyed by the repo path used in slides_content.
ASSETS = {
    "outputs/figures/fig1_speed_profile.png":
        "/_blob/7fa453801f93c4f75c2a188288d91d09",
    "outputs/figures/fig2_cost_by_regime.png":
        "/_blob/9aae5f643d22085e69d5a537d3f9355c",
    "outputs/figures/fig3_truck_penalty.png":
        "/_blob/62b61e757d7c84b97f8ec3409b22a158",
}

SECTION = (f"background:{BG}; color:{INK}; font-family:{SANS}; padding:0; "
           "display:flex; flex-direction:column")


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rich(text: str) -> str:
    """Render the **bold** / @@blue@@ / ##orange## markup as inline HTML."""
    out, i = [], 0
    marks = {"**": ("<b>", "</b>"),
             "@@": (f'<b><span style="color:{BLUE}">', "</span></b>"),
             "##": (f'<b><span style="color:{ORANGE}">', "</span></b>")}
    while i < len(text):
        for mark, (open_t, close_t) in marks.items():
            if text.startswith(mark, i):
                end = text.find(mark, i + 2)
                if end != -1:
                    out.append(open_t + esc(text[i + 2:end]) + close_t)
                    i = end + 2
                    break
        else:
            out.append(esc(text[i]))
            i += 1
    return "".join(out)


def pin(content: str, **kw) -> str:
    style = "; ".join(f"{k.replace('_', '-')}:{v}" for k, v in kw.items())
    return f'<div style="position:absolute; {style}">{content}</div>'


def p(text, size, color=INK, *, bold=False, line=1.5, width=None, top=None,
      left=None) -> str:
    style = [f"font-size:{size}px", f"color:{color}", f"line-height:{line}"]
    if bold:
        style.append("font-weight:700")
    if width:
        style.append(f"width:{width}px")
    if top is not None:
        style += ["position:absolute", f"top:{top}px", f"left:{left}px"]
    return f'<p style="{"; ".join(style)}">{rich(text)}</p>'


def box(inner, left, top, width, height, *, fill=PANEL, border=None,
        pad=32, center=False) -> str:
    style = [f"position:absolute", f"left:{left}px", f"top:{top}px",
             f"width:{width}px", f"height:{height}px", f"padding:{pad}px",
             "display:flex", "flex-direction:column"]
    style.append(f"background:{fill}" if fill else "background:#FFFFFF")
    if border:
        style.append(f"border:2px solid {border}")
    if center:
        style.append("justify-content:center")
    return f'<div style="{"; ".join(style)}">{inner}</div>'


def rule(left, top, width, color=RULE, h=1) -> str:
    return (f'<div style="position:absolute; left:{left}px; top:{top}px; '
            f'width:{width}px; height:{h}px; background:{color}"></div>')


def title_el(text) -> str:
    return p(text, 44, INK, bold=True, line=1.15, top=TOP + 60, left=MARGIN,
             width=CONTENT_W)


def lead_el(text) -> str:
    return p(text, 19, SUB, line=1.45, top=TOP + 147, left=MARGIN,
             width=CONTENT_W)


def foot_el(text) -> str:
    return p(text, 16, SUB, top=980, left=MARGIN, width=CONTENT_W - 120)


def page_el(n) -> str:
    return (f'<p style="position:absolute; right:{MARGIN}px; top:980px; '
            f'font-size:16px; color:{SUB}; text-align:right">{n}</p>')


BODY, BODY_LEAD = TOP + 166, TOP + 256


# --------------------------------------------------------------------------- #
def L_cover(d):
    return "".join([
        p(d["eyebrow"], 17, SUB, bold=True, top=295, left=MARGIN, width=800),
        p(d["title"], 76, INK, bold=True, line=1.1, top=340, left=MARGIN,
          width=CONTENT_W),
        "".join(p(ln, 23, SUB, line=1.5, top=576 + i * 40, left=MARGIN,
                  width=1240)
                for i, ln in enumerate(d["sub"].split("\n"))),
        rule(MARGIN, 806, 346, INK, 3),
        foot_el(d["foot"]),
    ])


def L_closing(d):
    return "".join([
        p(d["title"], 58, INK, bold=True, line=1.1, top=418, left=MARGIN,
          width=CONTENT_W),
        p(d["sub"], 22, SUB, top=562, left=MARGIN, width=CONTENT_W),
        rule(MARGIN, 677, 346, INK, 3),
        foot_el(d["foot"]),
    ])


def L_section(d):
    return "".join([
        p(d["num"], 22, BLUE, bold=True, top=360, left=MARGIN, width=400),
        p(d["title"], 66, INK, bold=True, line=1.1, top=425, left=MARGIN,
          width=CONTENT_W),
        p(d["sub"], 23, SUB, line=1.45, top=598, left=MARGIN, width=1150),
    ])


def L_statement(d):
    lines = d["title"].split("\n")
    return "".join([
        p(d["eyebrow"], 17, SUB, bold=True, top=274, left=MARGIN, width=800),
        "".join(p(ln, 60, INK, bold=True, line=1.18, top=331 + i * 82,
                  left=MARGIN, width=1512)
                for i, ln in enumerate(lines)),
        p(d["sub"], 23, SUB, line=1.55, top=684, left=MARGIN, width=1440),
    ])


def L_agenda(d):
    rows = []
    for num, name, desc in d["items"]:
        cells = (
            f'<div style="width:100px">{p(num, 20, BLUE, bold=True)}</div>'
            f'<div style="width:330px">{p(name, 24, INK, bold=True)}</div>'
            f'<div style="flex:1">{p(desc, 19, SUB, line=1.35)}</div>'
        )
        rows.append(
            f'<div style="display:flex; gap:44px; align-items:center; '
            f'height:106px; border-bottom:1px solid {RULE}">{cells}</div>'
        )
    return title_el(d["title"]) + pin(
        "".join(rows), left=f"{MARGIN}px", top=f"{BODY}px",
        width=f"{CONTENT_W}px", display="flex", flex_direction="column")


def L_split(d):
    left_w = 950
    body = "".join(p(t, s + 3, COLORS[c], line=1.55) for t, s, c in d["left"])
    out = [title_el(d["title"]),
           pin(body, left=f"{MARGIN}px", top=f"{BODY}px", width=f"{left_w}px",
               display="flex", flex_direction="column", gap="18px")]
    rx = MARGIN + left_w + 86
    rw = CONTENT_W - left_w - 86
    cards = d["cards"]
    gap, total = 40, 533
    h = (total - gap * (len(cards) - 1)) // len(cards)
    top = BODY
    for head, bodytext, tone in cards:
        accent = tone in ("BLUE", "ORANGE")
        inner = (p(head, 20, COLORS[tone] if accent else INK, bold=True) +
                 p(bodytext, 17, SUB, line=1.4))
        out.append(box(inner, rx, top, rw, h,
                       fill=None if accent else PANEL,
                       border=COLORS[tone] if accent else None, center=True))
        top += h + gap
    if d.get("note"):
        out.append(foot_el(d["note"]))
    return "".join(out)


def L_cards3(d):
    out = [title_el(d["title"])]
    top = BODY
    if d.get("lead"):
        out.append(lead_el(d["lead"]))
        top = BODY_LEAD
    cards, gap = d["cards"], 43
    w = (CONTENT_W - gap * (len(cards) - 1)) // len(cards)
    for i, (head, sub_line, bodytext) in enumerate(cards):
        inner = (p(head, 29, INK, bold=True) +
                 p(sub_line, 17, BLUE, bold=True) +
                 p(bodytext, 19, SUB, line=1.45))
        out.append(box(inner, MARGIN + i * (w + gap), top + 14, w, 482,
                       pad=37))
    if d.get("note"):
        out.append(foot_el(d["note"]))
    return "".join(out)


def L_metrics(d):
    out = [title_el(d["title"])]
    top = BODY
    if d.get("lead"):
        out.append(lead_el(d["lead"]))
        top = BODY_LEAD
    cards, gap = d["cards"], 43
    w = (CONTENT_W - gap * (len(cards) - 1)) // len(cards)
    for i, (value, label, note) in enumerate(cards):
        accent = note.startswith("##")
        inner = (p(label, 19, SUB) + p(value, 49, INK, bold=True) +
                 p(note, 17, SUB))
        out.append(box(inner, MARGIN + i * (w + gap), top + 43, w, 396,
                       fill=None if accent else PANEL,
                       border=ORANGE if accent else None, pad=37, center=True))
    if d.get("note"):
        out.append(foot_el(d["note"]))
    return "".join(out)


def L_table(d):
    out = [title_el(d["title"])]
    top = BODY
    if d.get("lead"):
        out.append(lead_el(d["lead"]))
        top = BODY_LEAD
    rows, cw = d["rows"], d["col_w"]
    total = sum(cw)
    size = 19 if len(rows) > 6 else 21
    cells = []
    for r, row in enumerate(rows):
        tds = []
        for c, text in enumerate(row):
            align = "right" if text.startswith(">") else "left"
            text = text[1:] if text.startswith(">") else text
            tag = "th" if r == 0 else "td"
            style = f"text-align:{align}"
            if r == 0:
                style += f"; width:{cw[c] / total * 100:.1f}%; font-weight:700"
            tds.append(f'<{tag} style="{style}">{rich(text)}</{tag}>')
        bg = f' style="background:{PANEL}"' if r == 0 else ""
        cells.append(f"<tr{bg}>{''.join(tds)}</tr>")
    table = (f'<table style="font-family:{SANS}; font-size:{size}px; '
             f'color:{INK}; padding:18px 22px; border:1px solid {RULE}">'
             f'{"".join(cells)}</table>')
    out.append(pin(table, left=f"{MARGIN}px", top=f"{top}px",
                   width=f"{CONTENT_W}px"))
    if d.get("note"):
        out.append(foot_el(d["note"]))
    return "".join(out)


def _img(path, left, top, w, h):
    src = ASSETS[path]
    return (f'<div style="position:absolute; left:{left}px; top:{top}px; '
            f'width:{w}px; height:{h}px; background:{PANEL}">'
            f'<img src="{src}" alt="分析圖表" style="width:{w}px; '
            f'height:{h}px; object-fit:contain"></div>')


def L_image(d):
    left_w = 763
    body = "".join(p(t, s + 3, COLORS[c], line=1.55) for t, s, c in d["left"])
    out = [title_el(d["title"]),
           pin(body, left=f"{MARGIN}px", top=f"{BODY + 29}px",
               width=f"{left_w}px", display="flex", flex_direction="column",
               gap="14px"),
           _img(d["image"], MARGIN + left_w + 72, BODY,
                CONTENT_W - left_w - 72, 619)]
    if d.get("note"):
        out.append(foot_el(d["note"]))
    return "".join(out)


def L_image_wide(d):
    body = "".join(p(t, s + 3, COLORS[c], line=1.5) for t, s, c in d["left"])
    out = [title_el(d["title"]),
           _img(d["image"], MARGIN, BODY, CONTENT_W, 446),
           pin(body, left=f"{MARGIN}px", top=f"{BODY + 482}px",
               width=f"{CONTENT_W}px", display="flex",
               flex_direction="column", gap="12px")]
    if d.get("note"):
        out.append(foot_el(d["note"]))
    return "".join(out)


def _flow(title_text, steps, note, *, num_color=BLUE, name_size=24,
          body_size=16, height=338, top_pad=101):
    out = [title_el(title_text)]
    gap, arrow_w = 32, 43
    step_w = (CONTENT_W - (gap * 2 + arrow_w) * (len(steps) - 1)) // len(steps)
    x, top = MARGIN, BODY + top_pad
    for i, (num, name, bodytext) in enumerate(steps):
        inner = (p(num, 17, num_color, bold=True) +
                 p(name, name_size, INK, bold=True) +
                 "".join(p(ln, body_size, SUB, line=1.3)
                         for ln in bodytext.split("\n")))
        out.append(box(inner, x, top, step_w, height, pad=28))
        x += step_w
        if i < len(steps) - 1:
            out.append(
                f'<x-shape kind="arrow-right" style="position:absolute; '
                f'left:{x + gap}px; top:{top + height // 2 - 13}px; '
                f'width:{arrow_w}px; height:26px; background:{RULE}">'
                f'</x-shape>')
            x += gap * 2 + arrow_w
    if note:
        out.append(foot_el(note))
    return "".join(out)


def L_pipeline(d):
    return _flow(d["title"], d["steps"], d.get("note"))


def L_arch(d):
    stages = [
        ("資料來源", "NGSIM 公開 API", "Socrata 端點\n無需驗證\n1,180 萬列", True),
        ("取得與清理", "01 · src/ngsim", "鍵集分頁下載\n去重與批次切分\n速度平滑", False),
        ("事件與對照組", "02_detect_events", "換道偵測\n四道過濾\n最近鄰配對", False),
        ("統計與產出", "03 · 04", "Bootstrap 區間\nOLS 迴歸\n圖表與結果表", False),
    ]
    out = [title_el(d["title"])]
    gap = 37
    w = (CONTENT_W - gap * (len(stages) - 1)) // len(stages)
    top, h = BODY + 14, 432
    for i, (name, tool, items, accent) in enumerate(stages):
        inner = (p(name, 24, BLUE if accent else INK, bold=True) +
                 p(tool, 16, SUB) +
                 '<div style="height:14px"></div>' +
                 "".join(p("·  " + it, 18, INK, line=1.5)
                         for it in items.split("\n")))
        out.append(box(inner, MARGIN + i * (w + gap), top, w, h, pad=32,
                       fill=None if accent else PANEL,
                       border=BLUE if accent else None))
        if i < len(stages) - 1:
            out.append(
                f'<x-shape kind="arrow-right" style="position:absolute; '
                f'left:{MARGIN + i * (w + gap) + w + 6}px; '
                f'top:{top + h // 2 - 12}px; width:26px; height:24px; '
                f'background:{RULE}"></x-shape>')
    band = top + h + 46
    outs = ["公開資料集", "data/raw · 126 MB Parquet",
            "data/processed · 事件與對照組", "outputs · 圖表、結果表、日誌"]
    out.append(rule(MARGIN, band - 20, CONTENT_W))
    for i, text in enumerate(outs):
        out.append(p(text, 16, SUB, line=1.35, top=band,
                     left=MARGIN + i * (w + gap), width=w))
    out.append(foot_el("每個階段都有獨立的輸出與日誌，任何一步都可以單獨重跑，"
                       "不需要重跑整條流程。"))
    return "".join(out)


LAYOUTS = {"cover": L_cover, "closing": L_closing, "section": L_section,
           "statement": L_statement, "agenda": L_agenda, "split": L_split,
           "cards3": L_cards3, "metrics": L_metrics, "table": L_table,
           "image": L_image, "image_wide": L_image_wide,
           "pipeline": L_pipeline, "arch": L_arch}

NO_NUMBER = {"cover", "closing", "section"}
SECTION_STARTS = {"01": "研究問題", "02": "資料來源", "03": "技術架構",
                  "04": "分析結果", "05": "商業價值", "06": "工程品質"}


def slide_id(i, d) -> str:
    base = d["layout"].replace("_", "-")
    if d["layout"] == "section":
        return f"sec-{d['num']}"
    return f"s{i:02d}-{base}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out)
    (out_dir / "project" / "slides").mkdir(parents=True, exist_ok=True)

    order, sections = [], {}
    for i, d in enumerate(DECK, start=1):
        sid = slide_id(i, d)
        order.append(sid)
        body = LAYOUTS[d["layout"]](d)
        if d["layout"] not in NO_NUMBER:
            body += page_el(i)
        html = (f'<section id="{sid}" style="{SECTION}; padding:0">'
                f'{body}</section>')
        (out_dir / "project" / "slides" / f"{sid}.html").write_text(
            html, encoding="utf-8")
        if d["layout"] == "section":
            sections[f"s{d['num']}"] = {"description": d["sub"], "start": sid}

    sections = {"intro": {"description": "專案概述與簡報架構",
                          "start": order[0]}, **sections}
    deck = {
        "v": 4,
        "createdOnFiles": {"v": 1, "at": "2026-09-19T09:30:00Z"},
        "title": "變換車道的外部成本",
        "order": order,
        "cover": order[0],
        "sections": sections,
        "faces": {"noto-sans-tc": {
            "family": "Noto Sans TC",
            "href": "https://fonts.googleapis.com/css2?family=Noto+Sans+TC"
                    ":wght@400;500;700&display=swap"}},
        "designSystems": [],
    }
    (out_dir / "project" / "deck.json").write_text(
        json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(order)} slides + deck.json to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
