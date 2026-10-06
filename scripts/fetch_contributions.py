import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "sachin-2004jlr"

URL = f"https://github.com/users/{USERNAME}/contributions"

OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "contributions.json"


def fetch_contributions():
    print(f"Fetching contributions for @{USERNAME}...")

    response = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    days = []

    for cell in soup.select("td.ContributionCalendar-day"):
        date = cell.get("data-date")
        level = cell.get("data-level")

        if not date:
            continue

        try:
            count_text = cell.get("aria-label", "")
            match = re.search(r"(\d[\d,]*) contribution", count_text)

            count = int(match.group(1).replace(",", "")) if match else 0

        except Exception:
            count = 0

        days.append(
            {
                "date": date,
                "count": count,
                "level": int(level or 0),
            }
        )

    if not days:
        raise RuntimeError(
            "No contribution data found. GitHub may have changed its HTML structure."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "username": USERNAME,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "contributions": days,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    print(f"Saved {len(days)} contribution days.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    fetch_contributions()
