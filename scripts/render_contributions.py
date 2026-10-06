"""Render data/contributions.json as the animated per-year heatmap panel.

Runs every few hours in .github/workflows/update-contributions.yml.

    python scripts/render_contributions.py
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from svgkit import C, DESKTOP, MOBILE, command, cw, fade, spans, text, window

INPUT_FILE = Path("data/contributions.json")
OUT = Path("assets")

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def fmt_day(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def year_grid(year, x, y, step, cell, today, start, small):
    """One calendar year, Sunday-start columns like GitHub. Returns (svg, height)."""
    jan1 = date(year["year"], 1, 1)
    origin = jan1 - timedelta(days=(jan1.weekday() + 1) % 7)
    gx = x + (26 if small else 36)
    label = 8.5 if small else 10.5
    out = []
    for row, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        out.append(text(x, y + 16 + row * step + cell - 1, name, label, C["muted"]))
    for month in range(1, 13):
        first = date(year["year"], month, 1)
        week = (first - origin).days // 7
        out.append(text(gx + week * step, y + 10, first.strftime("%b"), label, C["muted"]))
    for d in year["days"]:
        day = date.fromisoformat(d["date"])
        offset = (day - origin).days
        week, weekday = offset // 7, offset % 7
        cx, cy = gx + week * step, y + 16 + weekday * step
        delay = f"animation-delay:{start + week * 0.022:.3f}s"
        if day > today:
            out.append(f'<rect class="cell" x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="{cell / 5:.1f}" '
                       f'fill="none" stroke="{C["border"]}" stroke-width=".8" style="{delay}"/>')
            continue
        level = max(0, min(int(d.get("level", 0)), len(PALETTE) - 1))
        out.append(f'<rect class="cell" x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" rx="{cell / 5:.1f}" '
                   f'fill="{PALETTE[level]}" style="{delay}"><title>{d["count"]} on {d["date"]}</title></rect>')
    return "\n".join(out), 16 + 7 * step


def render(data, w):
    small = w < 800
    X = 30
    parts = []
    cmd, t = command(X, 76, "gh contributions --all-years", 0.2)
    parts.append(cmd)

    best = data["best_day"]
    stats = [
        (f"{data['total_contributions']:,}", "all-time contributions"),
        (f"{data['active_days']}", "active days"),
        (f"{data['current_streak']}d", "current streak"),
        (f"{data['longest_streak']}d", "longest streak"),
        (f"{best['count']}", f"best day · {fmt_day(best['date'])}"),
    ]
    per_row = 2 if small else 5
    col_w = (w - 2 * X) / per_row
    y = 100
    for i, (value, label) in enumerate(stats):
        sx = X + (i % per_row) * col_w
        sy = y + (i // per_row) * 56
        parts.append(fade(t + 0.08 * i, text(sx, sy + 28, value, 26, C["green_hi"], weight=700)
                          + text(sx, sy + 48, label, 11, C["muted"]), "rise"))
    rows = -(-len(stats) // per_row)
    y += rows * 56 + 18
    t += 0.5

    today = datetime.fromisoformat(data["generated_at"]).date()
    if small:
        step = (w - 2 * X - 26) / 54
        cell = round(step - 1.4, 1)
    else:
        step, cell = 16, 13
    for k, year in enumerate(data["years"]):
        parts.append(f'<rect x="{X}" y="{y:.1f}" width="{w - 2 * X}" height="1" fill="{C["border"]}"/>')
        y += 30
        head = [(str(year["year"]), C["text"], 700), ("  ", C["muted"]),
                (f"{year['total']:,} contributions", C["green_hi"])]
        if year["year"] == today.year:
            head.append(("  · tracking daily", C["muted"]))
        parts.append(fade(t, spans(X, y, head, 14)))
        y += 14
        grid, gh = year_grid(year, X, y, step, cell, today, t, small)
        parts.append(grid)
        y += gh + 24
        t += 0.9

    synced = datetime.fromisoformat(data["generated_at"]).strftime("%Y-%m-%d %H:%M UTC")
    y += 6
    parts.append(fade(t, spans(X, y, [("● ", C["green"]), (f"synced {synced}", C["muted"])], 11)))
    if small:
        y += 22
        lx = X + 34
    else:
        parts.append(fade(t, text(X + 32 * cw(11), y, "· auto-refreshed by GitHub Actions", 11, C["dim"])))
        lx = w - X - 5 * 16 - 30
    legend = [text(lx - 34, y, "less", 11, C["muted"])]
    for i, color in enumerate(PALETTE):
        legend.append(f'<rect x="{lx + i * 16}" y="{y - 10}" width="12" height="12" rx="2.5" fill="{color}"/>')
    legend.append(text(lx + 5 * 16 + 4, y, "more", 11, C["muted"]))
    parts.append(fade(t, "".join(legend)))

    css = """
  .cell { animation: pop .35s ease-out both; transform-box: fill-box; transform-origin: center; }
  @keyframes pop { from { opacity: 0; transform: scale(.4); } to { opacity: 1; transform: none; } }
"""
    years = ", ".join(f"{y['year']}: {y['total']}" for y in data["years"])
    label = (f"{data['total_contributions']} GitHub contributions all-time ({years}); "
             f"current streak {data['current_streak']} days, longest {data['longest_streak']} days.")
    # One element per line, so CI can diff away timestamp-only changes.
    return window(w, y + 28, "~/activity — live", "\n".join(parts), css, label)


def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    for suffix, width in (("", DESKTOP), ("-mobile", MOBILE)):
        path = OUT / f"contributions{suffix}.svg"
        path.write_text(render(data, width), encoding="utf-8")
        print(f"Created {path}")


if __name__ == "__main__":
    main()
