import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# SETTINGS
# ============================================================

USERNAME = "sachin-2004jlr"

CONTRIBUTIONS_URL = (
    f"https://github.com/users/{USERNAME}/contributions"
)

OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "contributions.json"


# ============================================================
# FETCH GITHUB CONTRIBUTION PAGE
# ============================================================

def fetch_page():
    print(f"Fetching contributions for @{USERNAME}...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    response = requests.get(
        CONTRIBUTIONS_URL,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# PARSE CONTRIBUTION DATA
# ============================================================

def parse_contributions(html):
    soup = BeautifulSoup(html, "html.parser")

    days = []

    cells = soup.select("td.ContributionCalendar-day")

    print(f"Found {len(cells)} contribution cells.")

    for cell in cells:

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        date = cell.get("data-date")

        if not date:
            continue

        # ----------------------------------------------------
        # CONTRIBUTION LEVEL
        # ----------------------------------------------------

        level_raw = cell.get("data-level", "0")

        try:
            level = int(level_raw)
        except ValueError:
            level = 0

        # ----------------------------------------------------
        # CONTRIBUTION COUNT
        # ----------------------------------------------------

        count = 0

        # GitHub may expose the exact number through
        # data-count.
        data_count = cell.get("data-count")

        if data_count is not None:

            try:
                count = int(data_count)

            except (ValueError, TypeError):
                count = 0

        # ----------------------------------------------------
        # FALLBACK: ARIA LABEL
        # ----------------------------------------------------

        if data_count is None:

            aria_label = cell.get("aria-label", "")

            match = re.search(
                r"(\d[\d,]*)\s+contributions?",
                aria_label,
                re.IGNORECASE,
            )

            if match:

                try:
                    count = int(
                        match.group(1).replace(",", "")
                    )

                except ValueError:
                    count = 0

        # ----------------------------------------------------
        # SAVE DAY
        # ----------------------------------------------------

        days.append(
            {
                "date": date,
                "count": count,
                "level": level,
            }
        )

    return days


# ============================================================
# CALCULATE STATISTICS
# ============================================================

def calculate_statistics(days):

    total_contributions = sum(
        day["count"]
        for day in days
    )

    # --------------------------------------------------------
    # BEST DAY
    # --------------------------------------------------------

    best_day = None

    if days:

        best_day = max(
            days,
            key=lambda day: day["count"],
        )

    # --------------------------------------------------------
    # CURRENT STREAK
    # --------------------------------------------------------

    current_streak = 0

    sorted_days = sorted(
        days,
        key=lambda day: day["date"],
        reverse=True,
    )

    for day in sorted_days:

        if day["count"] > 0:
            current_streak += 1

        else:
            break

    # --------------------------------------------------------
    # LONGEST STREAK
    # --------------------------------------------------------

    longest_streak = 0
    running_streak = 0

    for day in sorted(
        days,
        key=lambda day: day["date"],
    ):

        if day["count"] > 0:

            running_streak += 1

            longest_streak = max(
                longest_streak,
                running_streak,
            )

        else:

            running_streak = 0

    # --------------------------------------------------------
    # RETURN STATISTICS
    # --------------------------------------------------------

    return {
        "total_contributions": total_contributions,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
    }


# ============================================================
# SAVE JSON
# ============================================================

def save_data(days, statistics):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "username": USERNAME,

        "generated_at": (
            datetime.now(timezone.utc)
            .isoformat()
        ),

        "statistics": statistics,

        "contributions": days,
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
        )

    print()
    print("========================================")
    print("Contribution data successfully saved!")
    print("========================================")
    print(
        f"Contribution days : {len(days)}"
    )
    print(
        f"Total contributions: "
        f"{statistics['total_contributions']}"
    )
    print(
        f"Current streak    : "
        f"{statistics['current_streak']} days"
    )
    print(
        f"Longest streak    : "
        f"{statistics['longest_streak']} days"
    )

    if statistics["best_day"]:

        print(
            f"Best day          : "
            f"{statistics['best_day']['date']} "
            f"({statistics['best_day']['count']} contributions)"
        )

    print(
        f"Output            : {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        html = fetch_page()

        days = parse_contributions(html)

        if not days:

            raise RuntimeError(
                "No contribution cells were found."
            )

        statistics = calculate_statistics(
            days
        )

        save_data(
            days,
            statistics
        )

    except requests.RequestException as error:

        print()
        print("ERROR: Could not access GitHub.")
        print(error)

        raise SystemExit(1)

    except Exception as error:

        print()
        print("ERROR:")
        print(error)

        raise SystemExit(1)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
