"""Shared drawing helpers for the terminal-style profile SVGs.

Every panel is a self-contained SVG: GitHub strips CSS/JS from Markdown but
keeps CSS animations inside images. Text widths are pinned with textLength so
layouts are identical whatever monospace font the viewer has installed.
"""

import hashlib
import re
from html import escape
from pathlib import Path

DESKTOP, MOBILE = 960, 480
README = Path("README.md")
RAW = "https://raw.githubusercontent.com/sachin-2004jlr/sachin-2004jlr/main/"
FONT = (
    "'JetBrains Mono','SF Mono','Cascadia Code',Menlo,Consolas,"
    "'DejaVu Sans Mono','Liberation Mono',monospace"
)
CHAR_RATIO = 0.6  # advance width of a monospace glyph, in em

C = {
    # Neon terminal: near-black base with GitHub-style syntax accents.
    "bg": "#0a0d12",
    "card": "#0d1117",
    "bar": "#141920",
    "border": "#262c36",
    "text": "#e6edf3",
    "soft": "#b1bac4",
    "muted": "#7d8590",
    "dim": "#484f58",
    "accent": "#3fb950",      # green: prompts, bullets
    "accent_hi": "#7ee787",   # bright green: highlights, big numbers, roles
    "accent_alt": "#56d4dd",  # teal: gradient partner
    "warm": "#e3b341",        # amber: commit hashes, field names
    "info": "#79c0ff",        # blue: organisations, paths
    "tag": "#d2a8ff",         # purple: tech tags
    "key": "#ff7b72",         # red: yaml keys
}

BASE_CSS = f"""
  text {{ font-family: {FONT}; white-space: pre; }}
  .in   {{ animation: fadein .45s ease-out both; }}
  .rise {{ animation: rise .6s cubic-bezier(.2,.7,.2,1) both; }}
  .blink {{ animation: blink 1.05s steps(1) infinite; }}
  .sweep {{ animation: sweep 7s linear infinite; }}
  @keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
  /* Runs to -100% over 2n steps: Chromium never paints the final step of a
     stepped clip-path, so every character is revealed by step n of 2n. */
  @keyframes type {{
    from {{ -webkit-clip-path: inset(-30% 100% -30% 0); clip-path: inset(-30% 100% -30% 0); }}
    to   {{ -webkit-clip-path: inset(-30% -100% -30% 0); clip-path: inset(-30% -100% -30% 0); }}
  }}
  @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
  @keyframes sweep {{ from {{ transform: translateY(-60px); }} to {{ transform: translateY(var(--h)); }} }}
  @media (prefers-reduced-motion: reduce) {{
    * {{ animation: none !important; }}
  }}
"""


def cw(size):
    """Character advance for a font size."""
    return size * CHAR_RATIO


def fits(width, size):
    """How many characters fit in a pixel width."""
    return int(width / cw(size))


def attrs(**kw):
    return " ".join(
        f'{key.rstrip("_").replace("_", "-")}="{value}"'
        for key, value in kw.items()
        if value is not None
    )


def text(x, y, s, size=14, fill=C["text"], weight=None, cls=None,
         style=None, squeeze=False, anchor=None):
    """A single line of monospace text with a pinned width."""
    if not s:
        return ""
    length = len(s) * cw(size)
    return (
        f'<text {attrs(x=f"{x:.1f}", y=f"{y:.1f}", font_size=size, fill=fill, font_weight=weight, class_=cls, style=style, text_anchor=anchor)} '
        f'textLength="{length:.1f}" lengthAdjust="{"spacingAndGlyphs" if squeeze else "spacing"}">'
        f"{escape(s)}</text>"
    )


def spans(x, y, parts, size=14, cls=None, style=None):
    """One line built from (string, color[, weight]) runs laid end to end."""
    out = [f'<g {attrs(class_=cls, style=style)}>']
    col = 0
    for part in parts:
        s, fill = part[0], part[1]
        weight = part[2] if len(part) > 2 else None
        if s.strip():
            out.append(text(x + col * cw(size), y, s, size, fill, weight))
        col += len(s)
    out.append("</g>")
    return "".join(out)


def type_style(n, dur, start):
    """Animation revealing n characters over dur seconds (see @keyframes type)."""
    return f"animation: type {dur * 2:.2f}s steps({n * 2}, end) {start:.2f}s both"


def typed(x, y, parts, start, size=14, cps=40):
    """A line that types itself out character by character.

    Returns (svg, end_time) so callers can chain the next line.
    """
    if isinstance(parts, str):
        parts = [(parts, C["text"])]
    n = sum(len(p[0]) for p in parts)
    dur = max(n / cps, 0.15)
    # Browsers size a <text> bbox from the font's natural advance, not the
    # textLength, so an invisible box pins the clip to the real width.
    box = f'<rect x="{x:.1f}" y="{y - size:.1f}" width="{n * cw(size):.1f}" height="{size * 1.3:.1f}" fill="none"/>'
    line = spans(x, y, parts, size, style=type_style(n, dur, start))
    return line.replace(">", ">" + box, 1), start + dur


def fade(start, inner, cls="in"):
    return f'<g class="{cls}" style="animation-delay:{start:.2f}s">{inner}</g>'


def prompt(path="~"):
    return [
        ("sachin", C["accent"], 700),
        ("@", C["muted"]),
        ("budhhi", C["accent"], 700),
        (" ", C["muted"]),
        (path, C["info"]),
        (" $ ", C["muted"]),
    ]


def command(x, y, cmd, start, path="~", size=14, cps=32):
    """A prompt that appears, then a command typed after it."""
    p = prompt(path)
    plen = sum(len(s[0]) for s in p)
    head = fade(start, spans(x, y, p, size))
    body, end = typed(x + plen * cw(size), y, [(cmd, C["text"])], start + 0.25, size, cps)
    return head + body, end + 0.2


def cursor(x, y, size=14, start=0.0, fill=C["accent_hi"]):
    return fade(start, f'<rect class="blink" x="{x:.1f}" y="{y - size * 0.82:.1f}" width="{cw(size):.1f}" height="{size * 1.02:.1f}" fill="{fill}"/>')


def window(w, h, title, body, extra_css="", label=""):
    """Wrap body in a terminal window with chrome, scanlines and vignette."""
    h = int(round(h))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label or title)}">
<title>{escape(label or title)}</title>
<defs>
  <clipPath id="frame"><rect width="{w}" height="{h}" rx="14"/></clipPath>
  <pattern id="scanlines" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#ffffff" opacity=".025"/>
  </pattern>
  <radialGradient id="vignette" cx="50%" cy="45%" r="75%">
    <stop offset="62%" stop-color="#000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000" stop-opacity=".45"/>
  </radialGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{C["accent"]}" stop-opacity="0"/>
    <stop offset="100%" stop-color="{C["accent"]}" stop-opacity=".06"/>
  </linearGradient>
  <style>{BASE_CSS}{extra_css}</style>
</defs>
<g clip-path="url(#frame)">
  <rect width="{w}" height="{h}" fill="{C["bg"]}"/>
  <rect width="{w}" height="38" fill="{C["bar"]}"/>
  <rect y="38" width="{w}" height="1" fill="{C["border"]}"/>
  <circle cx="22" cy="19" r="6" fill="#ff5f57"/>
  <circle cx="42" cy="19" r="6" fill="#febc2e"/>
  <circle cx="62" cy="19" r="6" fill="#28c840"/>
  {text(w / 2 + 30, 24, title, 12, C["muted"], anchor="middle")}
{body}
  <rect class="sweep" style="--h:{h + 60}px" y="0" width="{w}" height="60" fill="url(#beam)"/>
  <rect width="{w}" height="{h}" fill="url(#scanlines)"/>
  <rect width="{w}" height="{h}" fill="url(#vignette)"/>
</g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{C["border"]}"/>
</svg>
"""


def stamp_readme(paths):
    """Point README.md at each asset by absolute URL plus a content hash.

    GitHub's /raw/ redirect drops query strings and raw files are cached for
    five minutes, so plain relative links can show a stale panel after an
    update. A new ?v= per change gives every version its own cache entry.
    """
    text = README.read_text(encoding="utf-8")
    for path in paths:
        name = Path(path).as_posix()
        digest = hashlib.sha1(Path(path).read_bytes()).hexdigest()[:10]
        pattern = r"(?:" + re.escape(RAW) + r")?" + re.escape(name) + r"(?:\?v=[0-9a-f]+)?"
        text = re.sub(pattern, f"{RAW}{name}?v={digest}", text)
    README.write_bytes(text.encode("utf-8"))
