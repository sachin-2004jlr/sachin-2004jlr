import json
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime


USERNAME = "sachin-2004jlr"

URL = f"https://github.com/users/{USERNAME}/contributions"

OUTPUT_FILE = Path("data/contributions.json")


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}


def parse_contribution_count(text):
    """
    Extract contribution count from GitHub tooltip text.

    Examples:

    "No contributions on October 5th."
        -> 0

    "1 contribution on January 5th."
        -> 1

    "12 contributions on February 8th."
        -> 12
    """

    text = text.strip()

    if not text:
        return 0

    if "No contributions" in text:
        return 0

    match = re.search(
        r"([\d,]+)\s+contributions?",
        text,
        re.IGNORECASE
    )

    if match:
        return int(match.group(1).replace(",", ""))

    return 0


def calculate_streaks(contributions):
    """
    Calculate current and longest contribution streak.
    """

    sorted_days = sorted(
        contributions,
        key=lambda x: x["date"]
    )

    # Only count days where contribution count > 0
    active_dates = {
        datetime.strptime(day["date"], "%Y-%m-%d").date()
        for day in sorted_days
        if day["count"] > 0
    }

    if not active_dates:
        return 0, 0

    # Longest streak
    longest_streak = 0
    current_streak_length = 0

    previous_date = None

    for date in sorted(active_dates):

        if previous_date is not None:
            difference = (date - previous_date).days

            if difference == 1:
                current_streak_length += 1
            else:
                current_streak_length = 1
        else:
            current_streak_length = 1

        longest_streak = max(
            longest_streak,
            current_streak_length
        )

        previous_date = date

    # Current streak
    today = datetime.now().date()

    current_streak = 0
    check_date = today

    # GitHub may contain today's cell even if there are
    # no contributions yet.

    while check_date in active_dates:
        current_streak += 1
        check_date = check_date.fromordinal(
            check_date.toordinal() - 1
        )

    # If today has no contribution, check yesterday.
    if current_streak == 0:
        yesterday = today.fromordinal(
            today.toordinal() - 1
        )

        if yesterday in active_dates:
            current_streak = 1
            check_date = yesterday.fromordinal(
                yesterday.toordinal() - 1
            )

            while check_date in active_dates:
                current_streak += 1
                check_date = check_date.fromordinal(
                    check_date.toordinal() - 1
                )

    return current_streak, longest_streak


def main():

    print(f"Fetching contributions for @{USERNAME}...")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # --------------------------------------------------
    # Find contribution cells
    # --------------------------------------------------

    cells = soup.select(
        "td.ContributionCalendar-day"
    )

    print(
        f"Found {len(cells)} contribution cells."
    )

    if not cells:
        raise RuntimeError(
            "Could not find GitHub contribution cells."
        )

    # --------------------------------------------------
    # Build tooltip lookup
    #
    # GitHub stores the contribution count in a
    # separate <tool-tip> element.
    #
    # Example:
    #
    # <tool-tip for="contribution-day-component-0-0">
    #     No contributions on October 5th.
    # </tool-tip>
    # --------------------------------------------------

    tooltip_map = {}

    tooltips = soup.find_all("tool-tip")

    print(
        f"Found {len(tooltips)} contribution tooltips."
    )

    for tooltip in tooltips:

        cell_id = tooltip.get("for")

        if not cell_id:
            continue

        tooltip_text = tooltip.get_text(
            " ",
            strip=True
        )

        tooltip_map[cell_id] = tooltip_text

    # --------------------------------------------------
    # Extract contribution data
    # --------------------------------------------------

    contributions = []

    for cell in cells:

        date_string = cell.get("data-date")

        level_string = cell.get(
            "data-level",
            "0"
        )

        cell_id = cell.get("id")

        if not date_string:
            continue

        # Convert GitHub level into integer
        try:
            level = int(level_string)
        except ValueError:
            level = 0

        # Find matching tooltip
        tooltip_text = tooltip_map.get(
            cell_id,
            ""
        )

        # Extract actual contribution count
        count = parse_contribution_count(
            tooltip_text
        )

        contributions.append(
            {
                "date": date_string,
                "count": count,
                "level": level
            }
        )

    # --------------------------------------------------
    # Sort by date
    # --------------------------------------------------

    contributions.sort(
        key=lambda x: x["date"]
    )

    # --------------------------------------------------
    # Calculate statistics
    # --------------------------------------------------

    total_contributions = sum(
        day["count"]
        for day in contributions
    )

    current_streak, longest_streak = (
        calculate_streaks(contributions)
    )

    best_day = max(
        contributions,
        key=lambda x: x["count"]
    )

    # --------------------------------------------------
    # Build final JSON
    # --------------------------------------------------

    output = {
        "username": USERNAME,
        "generated_at": datetime.now().isoformat(),
        "total_contributions": total_contributions,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "contributions": contributions
    }

    # --------------------------------------------------
    # Create data directory
    # --------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # Save JSON
    # --------------------------------------------------

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2
        )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    print()
    print("=" * 40)
    print("Contribution data successfully saved!")
    print("=" * 40)

    print(
        f"Contribution days : {len(contributions)}"
    )

    print(
        f"Total contributions: {total_contributions}"
    )

    print(
        f"Current streak    : {current_streak} days"
    )

    print(
        f"Longest streak    : {longest_streak} days"
    )

    print(
        "Best day          : "
        f"{best_day['date']} "
        f"({best_day['count']} contributions)"
    )

    print(
        f"Output            : {OUTPUT_FILE}"
    )

    # --------------------------------------------------
    # Extra verification
    # --------------------------------------------------

    non_zero_days = [
        day
        for day in contributions
        if day["count"] > 0
    ]

    print()
    print("=" * 40)
    print("Verification")
    print("=" * 40)

    print(
        f"Days with contributions: "
        f"{len(non_zero_days)}"
    )

    print()

    print("Sample contribution days:")

    for day in non_zero_days[:10]:

        print(
            f"  {day['date']} "
            f"-> {day['count']} contributions "
            f"(level {day['level']})"
        )


if __name__ == "__main__":
    main()