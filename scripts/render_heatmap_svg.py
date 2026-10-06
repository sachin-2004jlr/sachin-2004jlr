import json
import math
from datetime import datetime
from pathlib import Path


INPUT_FILE = Path("data/contributions.json")
OUTPUT_FILE = Path("contrib-heatmap.svg")


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

WIDTH = 860
HEIGHT = 210

CELL_SIZE = 12
CELL_GAP = 4

LEFT = 35
TOP = 42

BACKGROUND = "#0d1117"
TEXT = "#c9d1d9"
MUTED = "#8b949e"

PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
]


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

with INPUT_FILE.open("r", encoding="utf-8") as file:
    data = json.load(file)


contributions = data["contributions"]


# ---------------------------------------------------------
# PREPARE LAST 365 DAYS
# ---------------------------------------------------------

contributions = contributions[-365:]


# ---------------------------------------------------------
# CALCULATE TOTAL
# ---------------------------------------------------------

total = sum(day["count"] for day in contributions)


# ---------------------------------------------------------
# CREATE SVG
# ---------------------------------------------------------

svg = []

svg.append(
    f'''<svg xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}"
    height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}">

    <rect width="100%" height="100%" rx="16" fill="{BACKGROUND}"/>

    <style>
        .cell {{
            animation: reveal 0.45s ease-out forwards;
            opacity: 0;
        }}

        @keyframes reveal {{
            from {{
                opacity: 0;
                transform: translateY(-8px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .title {{
            font-family: monospace;
            font-size: 16px;
            font-weight: bold;
            fill: {TEXT};
        }}

        .label {{
            font-family: monospace;
            font-size: 11px;
            fill: {MUTED};
        }}
    </style>

    <text x="{LEFT}" y="24" class="title">
        sachin@github ~ $ contributions
    </text>

    <text x="{LEFT}" y="38" class="label">
        {total:,} contributions in the last year
    </text>
'''
)


# ---------------------------------------------------------
# DRAW CONTRIBUTION CELLS
# ---------------------------------------------------------

for index, day in enumerate(contributions):

    week = index // 7
    weekday = index % 7

    x = LEFT + week * (CELL_SIZE + CELL_GAP)
    y = TOP + weekday * (CELL_SIZE + CELL_GAP)

    level = int(day.get("level", 0))

    level = max(0, min(level, len(PALETTE) - 1))

    fill = PALETTE[level]

    delay = index * 0.012

    svg.append(
        f'''
        <rect
            class="cell"
            x="{x}"
            y="{y}"
            width="{CELL_SIZE}"
            height="{CELL_SIZE}"
            rx="3"
            fill="{fill}"
            style="animation-delay:{delay:.3f}s"
        />
        '''
    )


# ---------------------------------------------------------
# LEGEND
# ---------------------------------------------------------

legend_x = WIDTH - 170
legend_y = 190

svg.append(
    f'''
    <text
        x="{legend_x - 35}"
        y="{legend_y + 10}"
        class="label">
        Less
    </text>
    '''
)

for i, color in enumerate(PALETTE):

    x = legend_x + i * 20

    svg.append(
        f'''
        <rect
            x="{x}"
            y="{legend_y}"
            width="12"
            height="12"
            rx="3"
            fill="{color}"
        />
        '''
    )

svg.append(
    f'''
    <text
        x="{legend_x + 110}"
        y="{legend_y + 10}"
        class="label">
        More
    </text>
    '''
)


svg.append("</svg>")


# ---------------------------------------------------------
# WRITE FILE
# ---------------------------------------------------------

OUTPUT_FILE.write_text(
    "".join(svg),
    encoding="utf-8"
)

print(f"Created {OUTPUT_FILE}")
