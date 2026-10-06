"""Fetch the GitHub contribution calendar for every year since the account
was created into data/contributions.json.

Runs every few hours in .github/workflows/update-contributions.yml.

    python scripts/fetch_contributions.py
"""

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "sachin-2004jlr"
FIRST_YEAR = 2025  # account created April 2025
URL = f"https://github.com/users/{USERNAME}/contributions"
OUTPUT_FILE = Path("data/contributions.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}


def parse_count(label):
    """'12 contributions on Feb 8th.' -> 12, 'No contributions ...' -> 0."""
    match = re.search(r"([\d,]+)\s+contributions?", label or "", re.IGNORECASE)
    return int(match.group(1).replace(",", "")) if match else 0


def fetch_year(year):
    """Return (days, reported_total) for one calendar year."""
    response = requests.get(
        URL,
        params={"from": f"{year}-01-01", "to": f"{year}-12-31"},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    tooltips = {
        tip.get("for"): tip.get_text(" ", strip=True)
        for tip in soup.find_all("tool-tip")
        if tip.get("for")
    }
    days = {}
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        if cell["data-date"].startswith(str(year)):
            days[cell["data-date"]] = {
                "date": cell["data-date"],
                "count": parse_count(tooltips.get(cell.get("id"))),
                "level": int(cell.get("data-level", 0)),
            }
    if not days:
        raise RuntimeError(f"No contribution cells found for {year}.")

    heading = soup.find(id="js-contribution-activity-description")
    reported = parse_count(heading.get_text(" ", strip=True)) if heading else None
    return [days[k] for k in sorted(days)], reported


def streaks(days, today):
    """Current and longest daily streak, up to and including today."""
    active = {date.fromisoformat(d["date"]) for d in days if d["count"] > 0}
    longest = run = 0
    prev = None
    for day in sorted(active):
        run = run + 1 if prev and (day - prev).days == 1 else 1
        longest = max(longest, run)
        prev = day

    # Contributors ahead of UTC (IST is +5:30) may already have "tomorrow";
    # an empty today still leaves yesterday's streak alive.
    cursor = today + timedelta(days=1)
    while cursor not in active and cursor >= today:
        cursor -= timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def main():
    now = datetime.now(timezone.utc)
    today = now.date()

    years, all_days = [], []
    for year in range(now.year, FIRST_YEAR - 1, -1):
        print(f"Fetching {year}...")
        days, reported = fetch_year(year)
        total = sum(d["count"] for d in days)
        if reported is not None and reported != total:
            raise RuntimeError(f"{year}: GitHub reports {reported} but day cells sum to {total}")
        years.append({"year": year, "total": total, "days": days})
        all_days.extend(days)
        print(f"  {total} contributions")

    all_days.sort(key=lambda d: d["date"])
    past = [d for d in all_days if date.fromisoformat(d["date"]) <= today + timedelta(days=1)]
    current, longest = streaks(past, today)
    best = max(past, key=lambda d: (d["count"], d["date"]))

    output = {
        "username": USERNAME,
        "generated_at": now.isoformat(timespec="seconds"),
        "total_contributions": sum(y["total"] for y in years),
        "active_days": sum(1 for d in past if d["count"] > 0),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best,
        "years": years,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=1), encoding="utf-8")

    print(f"all-time {output['total_contributions']} · active days {output['active_days']} · "
          f"streak {current} (longest {longest}) · best day {best['date']} ({best['count']})")
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
