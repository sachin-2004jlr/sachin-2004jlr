from PIL import Image, ImageOps, ImageEnhance
from pathlib import Path
import html

INPUT_FILE = Path("source-photo.jpg")
OUTPUT_FILE = Path("sachin-ascii.svg")

CHARS = " .,:;irsXA253hMHGS#9B&@"
COLS = 92
ROWS = 58

img = Image.open(INPUT_FILE).convert("RGB")

w, h = img.size
crop = img.crop((int(w * 0.11), int(h * 0.03), int(w * 0.96), int(h * 0.83)))

gray = ImageOps.grayscale(crop)
gray = ImageEnhance.Contrast(gray).enhance(1.25)
gray = ImageEnhance.Sharpness(gray).enhance(1.15)

small = gray.resize((COLS, ROWS), Image.Resampling.LANCZOS)
pixels = list(small.getdata())

lines = []
for y in range(ROWS):
    line = []
    for x in range(COLS):
        value = pixels[y * COLS + x]
        index = int((255 - value) / 255 * (len(CHARS) - 1))
        line.append(CHARS[index])
    lines.append("".join(line).rstrip())

svg = '''<svg xmlns="http://www.w3.org/2000/svg"
    width="860" height="620" viewBox="0 0 860 620"
    role="img" aria-label="Animated ASCII portrait of Sachin">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="1.4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <linearGradient id="terminalText" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f0f6fc"/>
      <stop offset="55%" stop-color="#c9d1d9"/>
      <stop offset="100%" stop-color="#8b949e"/>
    </linearGradient>

    <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="50%" stop-color="#ffffff" stop-opacity=".12"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>

    <style>
      .ascii {
        font-family: "Courier New", "Liberation Mono", monospace;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.35px;
        fill: url(#terminalText);
        filter: url(#glow);
      }
      .row {
        opacity: 0;
        animation: reveal 0.7s ease-out forwards;
      }
      @keyframes reveal {
        0% { opacity: 0; transform: translateX(-12px); }
        65% { opacity: 1; transform: translateX(2px); }
        100% { opacity: .94; transform: translateX(0); }
      }
      .scan {
        animation: scan 4s ease-in-out infinite;
      }
      @keyframes scan {
        0%, 100% { transform: translateY(0); opacity: 0; }
        12% { opacity: .75; }
        50% { opacity: .35; }
        88% { opacity: .75; }
        100% { transform: translateY(500px); opacity: 0; }
      }
      .cursor {
        animation: blink 1s steps(2, start) infinite;
      }
      @keyframes blink {
        50% { opacity: 0; }
      }
    </style>
  </defs>

  <rect width="860" height="620" rx="18" fill="#0d1117"/>
  <rect x="1" y="1" width="858" height="618" rx="17"
        fill="none" stroke="#30363d" stroke-width="2"/>

  <circle cx="27" cy="24" r="4" fill="#8b949e"/>
  <circle cx="41" cy="24" r="4" fill="#8b949e"/>
  <circle cx="55" cy="24" r="4" fill="#8b949e"/>

  <text x="32" y="30" font-family="monospace" font-size="14"
        font-weight="700" fill="#c9d1d9">
    sachin@github ~ $ ./sachin-ascii.sh
  </text>

  <g transform="translate(18, 52)">
'''

for i, line in enumerate(lines):
    y = i * 9.0 + 9
    delay = i * 0.018
    svg += f'''    <text class="ascii row" x="10" y="{y:.1f}"
        style="animation-delay:{delay:.3f}s">{html.escape(line)}</text>
'''

svg += '''  </g>

  <rect class="scan" x="18" y="52" width="824" height="2"
        fill="url(#scan)"/>

  <text x="32" y="603" font-family="monospace" font-size="11"
        fill="#8b949e">
    AI &amp; Data Science Engineer  •  Full Stack AI  •  RAG  •  LLMs
  </text>

  <text x="806" y="603" font-family="monospace" font-size="12"
        fill="#c9d1d9" class="cursor">█</text>
</svg>
'''

OUTPUT_FILE.write_text(svg, encoding="utf-8")
print(f"Created {OUTPUT_FILE}")
