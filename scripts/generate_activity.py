#!/usr/bin/env python3
"""Generate a self-hosted contribution stat card SVG.

Fetches the contribution calendar via GitHub's GraphQL API and renders a
single card: total contributions + a smooth sparkline on the left, active
days / best week stacked on the right.
"""
import json
import os
import sys
import urllib.request

USERNAME = os.environ.get("GITHUB_USER", "gupta-builds")

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
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return calendar["totalContributions"], calendar["weeks"]


def compute_stats(weeks):
    days = [d for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    active_days = sum(1 for d in days if d["contributionCount"] > 0)
    best_week = max(
        (sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks),
        default=0,
    )
    sparkline = [d["contributionCount"] for d in days]
    return active_days, best_week, sparkline


def catmull_rom_path(points):
    """Smooth curve through points via uniform Catmull-Rom -> cubic Bezier."""
    if len(points) < 2:
        return ""
    d = f"M {points[0][0]:.2f},{points[0][1]:.2f} "
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6
        d += f"C {c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f} "
    return d


def smoothed(counts, window=7):
    """Trailing-window moving average, used only to shape the curve visually."""
    n = len(counts)
    out = []
    for i in range(n):
        lo = max(0, i - window + 1)
        out.append(sum(counts[lo:i + 1]) / (i - lo + 1))
    return out


def sparkline_svg(counts, x0, y0, w, h):
    shaped = smoothed(counts)
    peak = max(shaped) or 1
    n = len(shaped)
    baseline = y0 + h
    points = [
        (x0 + w * i / (n - 1), y0 + h - (c / peak) * h * 0.9)
        for i, c in enumerate(shaped)
    ]
    line_d = catmull_rom_path(points)
    fill_d = line_d + f"L {points[-1][0]:.2f},{baseline:.2f} L {points[0][0]:.2f},{baseline:.2f} Z"
    approx_len = sum(
        ((points[i + 1][0] - points[i][0]) ** 2 + (points[i + 1][1] - points[i][1]) ** 2) ** 0.5
        for i in range(n - 1)
    ) * 1.15

    return f"""
    <defs>
      <linearGradient id="sparkfill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#a78bfa" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path d="{fill_d}" fill="url(#sparkfill)" stroke="none">
      <animate attributeName="opacity" from="0" to="1" dur="1.2s" begin="0.4s" fill="freeze"/>
    </path>
    <path d="{line_d}" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round"
          stroke-dasharray="{approx_len:.0f}" stroke-dashoffset="{approx_len:.0f}">
      <animate attributeName="stroke-dashoffset" from="{approx_len:.0f}" to="0" dur="1.4s"
                begin="0s" fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
    </path>"""


def render(total, active_days, best_week, sparkline):
    width, height = 760, 200
    pad = 32

    left_w = 460
    spark = sparkline_svg(sparkline, pad, 100, left_w - pad, 68)

    right_x = width - pad

    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
  <rect width='{width}' height='{height}' rx='10' fill='#0d1117' stroke='#21262d' stroke-width='1'/>

  <text x='{pad}' y='54' font-family='"Segoe UI", Ubuntu, sans-serif' font-weight='700'
        font-size='34px' fill='#e6e6e6'>{total:,}</text>
  <text x='{pad}' y='76' font-family='"Segoe UI", Ubuntu, sans-serif' font-weight='400'
        font-size='13px' fill='#8b949e'>contributions in the last year</text>

  {spark}

  <text x='{right_x}' y='60' text-anchor='end' font-family='"Segoe UI", Ubuntu, sans-serif'
        font-weight='700' font-size='24px' fill='#e6e6e6'>{active_days}</text>
  <text x='{right_x}' y='79' text-anchor='end' font-family='"Segoe UI", Ubuntu, sans-serif'
        font-weight='400' font-size='12px' fill='#a78bfa'>active days</text>

  <text x='{right_x}' y='128' text-anchor='end' font-family='"Segoe UI", Ubuntu, sans-serif'
        font-weight='700' font-size='24px' fill='#e6e6e6'>{best_week}</text>
  <text x='{right_x}' y='147' text-anchor='end' font-family='"Segoe UI", Ubuntu, sans-serif'
        font-weight='400' font-size='12px' fill='#a78bfa'>best week</text>
</svg>"""


def main():
    total, weeks = fetch_calendar()
    active_days, best_week, sparkline = compute_stats(weeks)
    svg = render(total, active_days, best_week, sparkline)
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "activity-stats.svg"), "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
