#!/usr/bin/env python3
"""Generate a self-hosted activity stats SVG (replaces flaky third-party services).

Fetches the contribution calendar via GitHub's GraphQL API and renders three
stat panels (total / current streak / longest streak), each ringed by a
continuously rotating dashed ellipse.
"""
import json
import os
import sys
import urllib.request

USERNAME = os.environ.get("GITHUB_USER", "gupta-builds")
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_calendar():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    return calendar["totalContributions"], days


def compute_streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = cur_run = 0
    for c in counts:
        cur_run = cur_run + 1 if c > 0 else 0
        longest = max(longest, cur_run)

    idx = len(counts) - 1
    if idx >= 0 and counts[idx] == 0:
        idx -= 1  # today may not be over yet; don't count it as a break
    current = 0
    while idx >= 0 and counts[idx] > 0:
        current += 1
        idx -= 1
    return current, longest


def ring(cx, cy, rx, ry, rot_dur):
    return (
        f"<ellipse cx='{cx}' cy='{cy}' rx='{rx}' ry='{ry}' fill='none' "
        f"stroke='#a78bfa' stroke-width='9' stroke-linecap='butt' "
        f"stroke-dasharray='7 5' opacity='0.9'>"
        f"<animateTransform attributeName='transform' type='rotate' "
        f"from='0 {cx} {cy}' to='360 {cx} {cy}' dur='{rot_dur}s' repeatCount='indefinite'/>"
        f"</ellipse>"
    )


def panel(x, cx_offset, cy, number, label, sub):
    cx = x + cx_offset
    return f"""
    <g>
      {ring(cx, cy, 85, 55, 9)}
      <text x='{cx}' y='{cy - 6}' text-anchor='middle' font-family='"Segoe UI", Ubuntu, sans-serif'
            font-weight='700' font-size='30px' fill='#e6e6e6'>{number}</text>
      <text x='{cx}' y='{cy + 17}' text-anchor='middle' font-family='"Segoe UI", Ubuntu, sans-serif'
            font-weight='400' font-size='12px' fill='#a78bfa'>{label}</text>
      <text x='{cx}' y='{cy + 33}' text-anchor='middle' font-family='"Segoe UI", Ubuntu, sans-serif'
            font-weight='400' font-size='10px' fill='#8b949e'>{sub}</text>
    </g>"""


def render(total, current, longest):
    width, height = 840, 220
    cy = height / 2 + 4
    col = width / 3
    panels = [
        panel(0, col / 2, cy, total, "Total Contributions", "past 12 months"),
        panel(col, col / 2, cy, current, "Current Streak", "day" if current == 1 else "days"),
        panel(2 * col, col / 2, cy, longest, "Longest Streak", "day" if longest == 1 else "days"),
    ]
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
  <rect width='{width}' height='{height}' rx='6' fill='#0d1117'/>
  {''.join(panels)}
</svg>"""


def main():
    total, days = fetch_calendar()
    current, longest = compute_streaks(days)
    svg = render(total, current, longest)
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "activity-stats.svg"), "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
