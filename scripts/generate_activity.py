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


def catmull_rom_segments(points):
    """Uniform Catmull-Rom -> cubic Bezier control points, one 4-tuple per span."""
    segments = []
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segments.append((p1, c1, c2, p2))
    return segments


def segments_to_path(segments):
    if not segments:
        return ""
    d = f"M {segments[0][0][0]:.2f},{segments[0][0][1]:.2f} "
    for p1, c1, c2, p2 in segments:
        d += f"C {c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f} "
    return d


def bezier_point(p1, c1, c2, p2, t):
    mt = 1 - t
    x = mt ** 3 * p1[0] + 3 * mt ** 2 * t * c1[0] + 3 * mt * t ** 2 * c2[0] + t ** 3 * p2[0]
    y = mt ** 3 * p1[1] + 3 * mt ** 2 * t * c1[1] + 3 * mt * t ** 2 * c2[1] + t ** 3 * p2[1]
    return (x, y)


def path_length(segments, samples_per_segment=8):
    """Numeric arc length (not the chord distance between endpoints, which
    undershoots on curved spans and truncates the line-draw animation)."""
    total = 0.0
    for seg in segments:
        prev = seg[0]
        for i in range(1, samples_per_segment + 1):
            cur = bezier_point(*seg, i / samples_per_segment)
            total += ((cur[0] - prev[0]) ** 2 + (cur[1] - prev[1]) ** 2) ** 0.5
            prev = cur
    return total


def catmull_rom_path(points):
    """Smooth curve through points via uniform Catmull-Rom -> cubic Bezier."""
    return segments_to_path(catmull_rom_segments(points))


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
    segments = catmull_rom_segments(points)
    line_d = segments_to_path(segments)
    fill_d = line_d + f"L {points[-1][0]:.2f},{baseline:.2f} L {points[0][0]:.2f},{baseline:.2f} Z"
    approx_len = path_length(segments) * 1.05  # small safety margin over the sampled estimate

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


FONT = '"JetBrains Mono", ui-monospace, monospace'


def render(total, active_days, best_week, sparkline):
    width, height = 760, 200
    pad = 32

    top_band_bottom = 82  # baseline of the small label row + descender clearance
    spark_gap = 18        # clearance between the label row and the sparkline's peak
    spark_y0 = top_band_bottom + spark_gap

    left_w = 460
    spark = sparkline_svg(sparkline, pad, spark_y0, left_w - pad, height - pad - spark_y0)

    right_x = width - pad
    best_x = right_x
    active_x = right_x - 110

    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
  <text x='{pad}' y='54' font-family='{FONT}' font-weight='700'
        font-size='34px' fill='#e6e6e6'>{total:,}</text>
  <text x='{pad}' y='76' font-family='{FONT}' font-weight='400'
        font-size='13px' fill='#8b949e'>Contributions in the last year</text>

  {spark}

  <text x='{active_x}' y='54' text-anchor='end' font-family='{FONT}'
        font-weight='700' font-size='22px' fill='#e6e6e6'>{active_days}</text>
  <text x='{active_x}' y='76' text-anchor='end' font-family='{FONT}'
        font-weight='400' font-size='12px' fill='#a78bfa'>Active days</text>

  <text x='{best_x}' y='54' text-anchor='end' font-family='{FONT}'
        font-weight='700' font-size='22px' fill='#e6e6e6'>{best_week}</text>
  <text x='{best_x}' y='76' text-anchor='end' font-family='{FONT}'
        font-weight='400' font-size='12px' fill='#a78bfa'>Best week</text>
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
