"""Render the animated terminal panels used by README.md.

    python scripts/render_profile.py

Content comes from data/profile.json and the portrait from data/portrait.json
(see make_portrait.py). Each panel is written twice: assets/<name>.svg for
desktop and assets/<name>-mobile.svg for narrow screens.
"""

import json
import random
import re
import textwrap
from pathlib import Path

from svgkit import (C, DESKTOP, MOBILE, command, cursor, cw, fade, fits,
                    spans, text, type_style, typed, window)

OUT = Path("assets")
PROFILE = json.loads(Path("data/profile.json").read_text(encoding="utf-8"))
PORTRAIT = json.loads(Path("data/portrait.json").read_text(encoding="utf-8"))

# ANSI Shadow figlet glyphs.
GLYPHS = {
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "H": ["██╗  ██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    " ": ["  "] * 6,
}
GLITCH = "01<>/|{}[]#$%&*+=?!"
STROKES = {  # box-drawing glyph -> segments from the cell centre, in half-cells
    "═": [(-1, 0, 1, 0)], "║": [(0, -1, 0, 1)],
    "╗": [(-1, 0, 0, 0), (0, 0, 0, 1)], "╔": [(0, 0, 1, 0), (0, 0, 0, 1)],
    "╝": [(-1, 0, 0, 0), (0, -1, 0, 0)], "╚": [(0, 0, 1, 0), (0, -1, 0, 0)],
}


def gradient(gid, x1, x2):
    return (f'<defs><linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x1:.0f}" y1="0" x2="{x2:.0f}" y2="0">'
            f'<stop offset="0%" stop-color="{C["green_hi"]}"/><stop offset="100%" stop-color="{C["teal"]}"/>'
            "</linearGradient></defs>")


def banner_svg(word, x, y, width, start, gid="name"):
    """ANSI Shadow lettering drawn as crisp blocks plus hairline shadows.

    Shapes rather than text: box-drawing glyphs vary wildly between fonts.
    """
    rows = [" ".join(GLYPHS[ch][r] for ch in word) for r in range(6)]
    bw = width / len(rows[0])
    bh = bw * 1.9
    hw, hh = bw / 2, bh / 2
    out = [gradient(gid, x, x + width)]
    for r, row in enumerate(rows):
        blocks, lines = [], []
        for c, ch in enumerate(row):
            cx, cy = x + c * bw, y + r * bh
            if ch == "█":
                blocks.append(f"M{cx:.1f} {cy:.1f}h{bw + .4:.1f}v{bh + .4:.1f}h{-bw - .4:.1f}z")
            for dx1, dy1, dx2, dy2 in STROKES.get(ch, []):
                mx, my = cx + hw, cy + hh
                lines.append(f"M{mx + dx1 * hw:.1f} {my + dy1 * hh:.1f}L{mx + dx2 * hw:.1f} {my + dy2 * hh:.1f}")
        box = f'<rect x="{x:.1f}" y="{y + r * bh:.1f}" width="{width:.1f}" height="{bh:.1f}" fill="none"/>'
        out.append(
            f'<g style="{type_style(len(row), 0.5, start + r * 0.07)}">{box}'
            f'<path d="{"".join(lines)}" stroke="#2ea043" stroke-width="1.5" opacity=".55" fill="none"/>'
            f'<path d="{"".join(blocks)}" fill="url(#{gid})"/></g>'
        )
    return "".join(out), 6 * bh


def wrap(s, width):
    return textwrap.wrap(s, max(width, 10))


# ---------------------------------------------------------------- hero

def portrait_svg(x, y, width):
    cols, rows, palette = PORTRAIT["cols"], PORTRAIT["rows"], PORTRAIT["palette"]
    rng = random.Random(7)  # deterministic, so re-renders don't churn the diff
    step = width / cols / 0.6  # font size == line height keeps the 0.6 cell
    out = []
    for r, (line, shade) in enumerate(zip(PORTRAIT["lines"], PORTRAIT["shades"])):
        runs, start = [], 0
        for c in range(1, cols + 1):
            if c == cols or shade[c] != shade[start] or (line[c] == " ") != (line[start] == " "):
                chunk = line[start:c]
                if chunk.strip():
                    runs.append(text(x + start * width / cols, y + (r + 1) * step, chunk,
                                     round(step, 2), palette[int(shade[start], 36)],
                                     weight=700, squeeze=True))
                start = c
        delay = 0.15 + r * 0.022
        # Scrambled glyphs flash in the same cells first, then the real row resolves.
        noise = "".join(" " if ch == " " else rng.choice(GLITCH) for ch in line)
        glitch = [text(x + m.start() * width / cols, y + (r + 1) * step, m.group(), round(step, 2),
                       C["green"], weight=700, squeeze=True) for m in re.finditer(r"\S+", noise)]
        out.append(f'<g class="scramble" style="animation-delay:{delay:.3f}s">{"".join(glitch)}</g>')
        out.append(f'<g class="decode" style="animation-delay:{delay + 0.22:.3f}s">{"".join(runs)}</g>')
    return "".join(out), rows * step


def hud(x0, y0, x1, y1):
    out = []
    for cx, cy, dx, dy in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        out.append(f'<path d="M{cx:.1f} {cy + 14 * dy:.1f}V{cy:.1f}H{cx + 14 * dx:.1f}" fill="none" stroke="{C["green"]}" stroke-width="1.5" opacity=".8"/>')
    label = f"subject: sachin_s · ascii {PORTRAIT['cols']}x{PORTRAIT['rows']} · bg removed"
    out.append(text(x0, y1 + 20, label, 11, C["muted"]))
    return fade(0.1, "".join(out))


def roles_svg(x, y, start, size=13, slot=3.0):
    """Cycle through PROFILE["roles"], typing each in and erasing it, forever."""
    roles = PROFILE["roles"]
    out = [fade(start, spans(x, y, [("~/roles ", C["muted"]), ("▸ ", C["green"])], size))]
    rx = x + 10 * cw(size)
    cycle = slot * len(roles)
    for i, role in enumerate(roles):
        box = f'<rect x="{rx:.1f}" y="{y - size:.1f}" width="{len(role) * cw(size):.1f}" height="{size * 1.3:.1f}" fill="none"/>'
        style = (f"animation: role {cycle:.1f}s steps({len(role) * 2}, end) {start + i * slot:.2f}s infinite both")
        cls = "role" if i == 0 else "role role-alt"
        out.append(f'<g class="{cls}" style="{style}">{box}{text(rx, y, role, size, C["green_hi"], weight=700)}</g>')
    return "".join(out)


def hero(w):
    mobile = w < 800
    if mobile:
        pw = w - 64
        px, py = (w - pw) / 2, 64
        X, col_w = 26, w - 52
    else:
        px, py, pw = 30, 62, 404
        X, col_w = 466, w - 466 - 26
    portrait, ph = portrait_svg(px, py, pw)
    parts = [portrait, hud(px - 8, py - 8, px + pw + 8, py + ph + 10)]

    size = 13
    t = 0.4
    y = py + ph + 76 if mobile else 80
    cmd, t = command(X, y, "./boot --profile sachin", t)
    parts.append(cmd)
    for label in ["mounting vector store", "warming up LLM context", "linking full-stack runtime"]:
        y += 22
        t += 0.18
        parts.append(fade(t, spans(X, y, [("[  ", C["muted"]), ("OK", C["green_hi"], 700),
                                          ("  ] ", C["muted"]), (label, C["soft"])], size)))

    y += 26
    t += 0.35
    name_svg, bh = banner_svg("SACHIN S", X, y, min(col_w, 444), t)
    parts.append(name_svg)
    y += bh + 38
    t += 0.8

    parts.append(fade(t, text(X, y, PROFILE["role"], 17, C["text"], weight=700), "rise"))
    y += 22
    company = f"{PROFILE['company']} · {PROFILE['company_location']}"
    parts.append(fade(t + 0.15, text(X, y, company, 12, C["muted"]), "rise"))
    t += 0.6

    y += 26
    parts.append(roles_svg(X, y, t))
    t += 0.3

    y += 36
    cmd, t = command(X, y, "cat focus.txt", t)
    parts.append(cmd)
    for item in PROFILE["focus"]:
        y += 22
        line, t = typed(X, y, [("▸ ", C["green"]), (item, C["soft"])], t, size, cps=70)
        parts.append(line)

    y += 36
    cmd, t = command(X, y, "status", t)
    parts.append(cmd)
    y += 22
    status = [("● ", C["green_hi"]), (PROFILE["status"].upper(), C["green_hi"], 700),
              (f"  · {PROFILE['based']}", C["soft"])]
    n = sum(len(s[0]) for s in status)
    parts.append(fade(t, spans(X, y, status, size)))
    parts.append(cursor(X + n * cw(size) + 6, y, size, t))

    # tmux-style status bar.
    H = max(y + 58, py + ph + 84)  # clear both the text and the portrait caption
    sb = H - 28
    tabs = [("0:boot* ", C["text"])]
    if not mobile:
        tabs.append(("1:about  2:career  3:projects  4:stack  5:activity", C["muted"]))
    parts.append(
        f'<rect y="{sb}" width="{w}" height="28" fill="{C["bar"]}"/>'
        f'<rect y="{sb}" width="{w}" height="1" fill="{C["border"]}"/>'
        f'<rect x="0" y="{sb}" width="96" height="28" fill="{C["green"]}"/>'
        + text(14, sb + 18, "PORTFOLIO", 12, "#06110a", weight=700)
        + spans(110, sb + 18, tabs, 12)
        + text(w - 16, sb + 18, "Bengaluru, IN", 12, C["muted"], anchor="end")
    )

    css = """
  .decode { animation: decode .5s steps(4) both; }
  @keyframes decode { 0% { opacity: 0; } 50% { opacity: .35; } 100% { opacity: 1; } }
  .scramble { opacity: 0; animation: scramble .5s steps(3) both; }
  @keyframes scramble { 0% { opacity: 0; } 30% { opacity: .85; } 100% { opacity: 0; } }
  /* Each role owns one slot of the cycle: type in, hold, erase, stay hidden.
     Overshooting to -100% sidesteps Chromium skipping a stepped animation's last frame. */
  @keyframes role {
    0%     { clip-path: inset(-30% 100% -30% 0); -webkit-clip-path: inset(-30% 100% -30% 0); }
    9%     { clip-path: inset(-30% -100% -30% 0); -webkit-clip-path: inset(-30% -100% -30% 0); }
    27%    { clip-path: inset(-30% -100% -30% 0); -webkit-clip-path: inset(-30% -100% -30% 0); }
    33.3%  { clip-path: inset(-30% 100% -30% 0); -webkit-clip-path: inset(-30% 100% -30% 0); }
    100%   { clip-path: inset(-30% 100% -30% 0); -webkit-clip-path: inset(-30% 100% -30% 0); }
  }
  @media (prefers-reduced-motion: reduce) { .role-alt { display: none; } }
"""
    return window(w, H, "sachin@budhhi: ~/portfolio — zsh", "".join(parts), css,
                  label=f"{PROFILE['name']}, {PROFILE['role']} at {PROFILE['company']}. Animated terminal with an ASCII portrait.")


# --------------------------------------------------------------- about

def about(w):
    mobile = w < 800
    X = 30
    parts = []
    cmd, t = command(X, 76, "neofetch", 0.2)
    parts.append(cmd)
    t += 0.1

    if mobile:
        ix, top = X, 112
    else:
        logo, _ = banner_svg("S", X + 30, 128, 118, t, gid="logo")
        parts.append(logo)
        ix, top = 230, 104

    certs = sum(len(items) for _, items in PROFILE["certifications"])
    projects = len(PROFILE["featured_projects"]) + len(PROFILE["more_projects"])
    rows = [
        ("role", PROFILE["role"]),
        ("company", f"{PROFILE['company']} ({PROFILE['company_location']})"),
        ("based", PROFILE["based"]),
        ("education", "B.E. AI & Data Science · CGPA 9.07"),
        ("focus", "Generative AI · RAG · agents · MCP"),
        ("ships", "React · Next.js · Flask · FastAPI · MongoDB"),
        ("certs", f"{certs} (12 Anthropic · 7 Google)"),
        ("projects", str(projects)),
        ("status", PROFILE["status"]),
    ]
    size = 13
    y = top
    parts.append(fade(t, spans(ix, y, [("sachin", C["green_hi"], 700), ("@", C["muted"]), ("budhhi", C["green_hi"], 700)], 14)))
    y += 10
    parts.append(fade(t, f'<rect x="{ix}" y="{y}" width="{13 * cw(14):.1f}" height="1" fill="{C["dim"]}"/>'))
    key_w = 11
    room = fits(w - ix - 26, size) - key_w
    for key, value in rows:
        for i, line in enumerate(wrap(value, room)):
            y += 21
            t += 0.06
            head = (f"{key}:".ljust(key_w), C["amber"], 700) if i == 0 else (" " * key_w, C["muted"])
            parts.append(fade(t, spans(ix, y, [head, (line, C["text"])], size)))
    y += 18
    swatches = [C["red"], C["amber"], C["green"], C["teal"], C["blue"], C["purple"], C["soft"], C["text"]]
    parts.append(fade(t + 0.1, "".join(
        f'<rect x="{ix + i * 26}" y="{y}" width="24" height="14" fill="{c}"/>' for i, c in enumerate(swatches))))
    y += 14

    y += 30
    parts.append(fade(t + 0.2, f'<rect x="{X}" y="{y - 14}" width="{w - 2 * X}" height="1" fill="{C["border"]}"/>'))
    y += 8
    for line in wrap(PROFILE["statement"], fits(w - 2 * X, size)):
        y += 21
        t += 0.05
        parts.append(fade(t + 0.2, text(X, y, line, size, C["soft"])))
    return window(w, y + 32, "~ — neofetch", "".join(parts),
                  label=f"About: {PROFILE['statement']}")


# ---------------------------------------------------------- experience

def experience(w):
    X, size, step = 30, 13, 21
    parts = []
    y = 76
    cmd, t = command(X, y, "git log --graph --career", 0.2)
    parts.append(cmd)
    gx = X + 6
    tx = X + 26
    room = fits(w - tx - 26, size) - 2
    y += 14
    rail_top = y + 16
    last_node = rail_top
    for n, job in enumerate(PROFILE["experience"]):
        y += 30
        t += 0.2
        last_node = y - 5
        node = (f'<circle cx="{gx}" cy="{y - 5}" r="6" fill="{C["bg"]}" stroke="{C["amber"]}" stroke-width="2"/>'
                f'<circle cx="{gx}" cy="{y - 5}" r="2.5" fill="{C["amber"]}"/>')
        ref_color = C["green_hi"] if n == 0 else (C["purple"] if "tag" in job["ref"] else C["blue"])
        head = [("commit ", C["amber"]), (job["hash"], C["amber"], 700), (" (", C["amber"]),
                (job["ref"], ref_color, 700), (")", C["amber"])]
        parts.append(fade(t, node + spans(tx, y, head, 12)))
        if job["when"]:
            if w < 800:
                y += 20
                parts.append(fade(t, text(tx, y, job["when"], 12, C["muted"])))
            else:
                parts.append(fade(t, text(w - 30, y, job["when"], 12, C["muted"], anchor="end")))
        y += 26
        t += 0.12
        for line in wrap(job["title"], fits(w - tx - 26, 16)):
            parts.append(fade(t, text(tx, y, line, 16, C["text"], weight=700), "rise"))
            y += 20
        for line in wrap(job["org"], fits(w - tx - 26, 12.5)):
            parts.append(fade(t + 0.1, text(tx, y, line, 12.5, C["blue"]), "rise"))
            y += 18
        y -= 18
        for p in job["points"]:
            for i, line in enumerate(wrap(p, room)):
                y += step
                lead = "+ " if i == 0 else "  "
                piece, t = typed(tx, y, [(lead, C["green"]), (line, C["soft"])], t, size, cps=160)
                parts.append(piece)
        if job["stack"]:
            y += step + 2
            parts.append(fade(t, spans(tx, y, [("stack: ", C["muted"]), (job["stack"], C["purple"])], 12)))
        y += 6
    rail = (f'<rect x="{gx - 1}" y="{rail_top}" width="2" height="{last_node - rail_top:.0f}" '
            f'fill="{C["dim"]}" class="grow"/>')
    css = """
  .grow { transform-box: fill-box; transform-origin: top; animation: grow 2.4s ease-out .3s both; }
  @keyframes grow { from { transform: scaleY(0); } to { transform: scaleY(1); } }
"""
    return window(w, y + 28, "~/career — git log", rail + "".join(parts), css,
                  label="Experience: Junior Full Stack AI Engineer at Budhhi Technologies (Aug 2026 – present); Associate Software Developer intern at Budhhi (Feb – Aug 2026); Machine Learning Intern at Acmegrade (Apr – Jun 2025); B.E. AI & Data Science, CGPA 9.07.")


# ------------------------------------------------------------ projects

def card(p, cx, top, cwid, h, lines, start):
    live = p["status"] == "ONGOING"
    accent = C["green_hi"] if live else C["blue"]
    g = [f'<rect x="{cx:.1f}" y="{top:.1f}" width="{cwid:.1f}" height="{h:.1f}" rx="10" fill="{C["card"]}" stroke="{C["border"]}"/>',
         f'<rect x="{cx:.1f}" y="{top:.1f}" width="3" height="{h:.1f}" rx="1.5" fill="{accent}"/>',
         text(cx + 20, top + 32, p["name"], 18, C["text"], weight=700),
         text(cx + 20, top + 52, p["tag"], 12, C["blue"]),
         text(cx + cwid - 16, top + 52, p["visibility"], 11, C["muted"], anchor="end")]
    badge_w = len(p["status"]) * cw(11) + 20
    bx = cx + cwid - 16 - badge_w
    g.append(f'<rect x="{bx:.1f}" y="{top + 17:.1f}" width="{badge_w:.1f}" height="22" rx="11" fill="none" stroke="{accent}" opacity=".7"/>')
    if live:
        g.append(f'<circle class="pulse" cx="{bx - 10:.1f}" cy="{top + 28:.1f}" r="3.5" fill="{accent}"/>')
    g.append(text(bx + 10, top + 32, p["status"], 11, accent, weight=700))
    ly = top + 80
    for line in lines:
        g.append(text(cx + 20, ly, line, 12.5, C["soft"]))
        ly += 19
    g.append(text(cx + 20, top + h - 18, p["stack"], 11.5, C["purple"]))
    return fade(start, "".join(g), "rise")


def projects(w):
    mobile = w < 800
    X = 30
    parts = []
    y = 76
    cmd, t = command(X, y, "ls ~/projects --featured", 0.2)
    parts.append(cmd)
    t += 0.1
    ncol, gap = (1, 16) if mobile else (2, 20)
    cwid = (w - 2 * X - gap * (ncol - 1)) / ncol
    room = fits(cwid - 40, 12.5)
    feats = PROFILE["featured_projects"]
    wrapped = [wrap(p["desc"], room) for p in feats]
    top = y + 26
    for r in range(0, len(feats), ncol):
        row = list(range(r, min(r + ncol, len(feats))))
        h = 112 + max(len(wrapped[i]) for i in row) * 19
        for k, i in enumerate(row):
            parts.append(card(feats[i], X + k * (cwid + gap), top, cwid, h, wrapped[i], t + i * 0.15))
        top += h + gap
    t += len(feats) * 0.15 + 0.2

    y = top + 26
    cmd, t = command(X, y, "ls ~/projects --more", t)
    parts.append(cmd)
    y += 8
    name_w = max(len(p["name"]) for p in PROFILE["more_projects"]) + 2
    for p in PROFILE["more_projects"]:
        y += 22
        t += 0.05
        if mobile:
            parts.append(fade(t, spans(X, y, [("▸ ", C["green"]), (p["name"], C["text"], 700), ("  " + p["year"], C["muted"])], 12.5)))
            y += 18
            parts.append(fade(t, text(X + 2 * cw(12.5), y, p["desc"], 12, C["soft"])))
        else:
            parts.append(fade(t, spans(X, y, [("▸ ", C["green"]), (p["name"].ljust(name_w), C["text"], 700),
                                              (p["year"] + "   ", C["muted"]), (p["desc"], C["soft"])], 12.5)))
    css = """
  .pulse { animation: pulse 1.8s ease-in-out infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
"""
    names = ", ".join(p["name"] for p in feats + PROFILE["more_projects"])
    return window(w, y + 32, "~/projects — ls", "".join(parts), css, label=f"Projects: {names}.")


# --------------------------------------------------------------- stack

def yaml_block(X, y, entries, t, w, size=13, step=22):
    """key: [ a, b, c ] lines wrapped to width, typed in sequence."""
    parts = []
    key_w = max(len(k) for k, _ in entries) + 2
    room = fits(w - X - 26, size) - key_w - 4
    for key, items in entries:
        y += step + 6
        lines, cur = [], ""
        for item in items:
            add = (", " if cur else "") + item
            if cur and len(cur) + len(add) > room:
                lines.append(cur + ",")
                cur = item
            else:
                cur += add
        lines.append(cur)
        for i, line in enumerate(lines):
            if i:
                y += step
            runs = ([(key, C["red"]), (":", C["muted"]), (" " * (key_w - len(key) - 1) + "[ ", C["muted"])]
                    if i == 0 else [(" " * (key_w + 2), C["muted"])])
            runs.append((line, C["text"]))
            if i == len(lines) - 1:
                runs.append((" ]", C["muted"]))
            piece, t = typed(X, y, runs, t, size, cps=150)
            parts.append(piece)
    return "".join(parts), y, t


def stack(w):
    X = 30
    cmd, t = command(X, 76, "cat stack.yaml", 0.2)
    size = 13 if w >= 800 else 12
    body, y, t = yaml_block(X, 84, PROFILE["stack"], t, w, size)
    return window(w, y + 34, "~/stack.yaml — less", cmd + body,
                  label="Tech stack: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in PROFILE["stack"]))


# -------------------------------------------------------------- certs

def certs(w):
    X, size = 30, 12.5
    parts = []
    total = sum(len(items) for _, items in PROFILE["certifications"])
    cmd, t = command(X, 76, "tree ~/certifications", 0.2)
    parts.append(cmd)
    y = 76
    y += 26
    parts.append(fade(t, spans(X, y, [("certifications/", C["blue"], 700), (f"  {total} verified", C["muted"])], size)))
    groups = PROFILE["certifications"]
    for g, (issuer, items) in enumerate(groups):
        last = g == len(groups) - 1
        y += 24
        t += 0.12
        parts.append(fade(t, spans(X, y, [("└── " if last else "├── ", C["dim"]), (issuer + "/", C["blue"], 700),
                                          (f"  ({len(items)})", C["muted"])], size)))
        pipe = "    " if last else "│   "
        room = fits(w - X - 26, size) - 8
        lines, cur = [], ""
        for item in items:
            add = ("  ·  " if cur else "") + item
            if cur and len(cur) + len(add) > room:
                lines.append(cur)
                cur = item
            else:
                cur += add
        lines.append(cur)
        for line in lines:
            y += 20
            piece, t = typed(X, y, [(pipe, C["dim"]), ("  " + line, C["soft"])], t, size, cps=220)
            parts.append(piece)

    y += 44
    cmd, t = command(X, y, 'echo "$NEXT_MISSION"', t + 0.2)
    parts.append(cmd)
    y += 32
    big = 20 if w >= 800 else 17
    msg = "let's build something intelligent."
    line, t = typed(X, y, [(msg, C["green_hi"])], t, big, cps=26)
    parts.append(line)
    parts.append(cursor(X + len(msg) * cw(big) + 6, y, big, t))
    return window(w, y + 34, "~/certifications — tree", "".join(parts),
                  label="Certifications: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in groups) + ". Let's build something intelligent.")


PANELS = {"hero": hero, "about": about, "experience": experience,
          "projects": projects, "stack": stack, "certifications": certs}


def main():
    OUT.mkdir(exist_ok=True)
    for name, fn in PANELS.items():
        for suffix, width in (("", DESKTOP), ("-mobile", MOBILE)):
            path = OUT / f"{name}{suffix}.svg"
            path.write_text(fn(width), encoding="utf-8")
            print(f"Created {path}")


if __name__ == "__main__":
    main()
