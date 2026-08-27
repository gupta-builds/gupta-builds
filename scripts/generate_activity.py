#!/usr/bin/env python3
"""Generate a self-hosted contribution stat card SVG.

Fetches the contribution calendar via GitHub's GraphQL API and renders a
single card: total contributions + a smooth sparkline spanning the full
width, with active days / best streak stacked on the right.
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


def compute_streak_stats(days):
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

    # an ongoing streak that has reached the historical best should read as
    # the still-climbing current number, not a stale frozen peak
    return current if current >= longest else longest


def compute_stats(weeks):
    days = [d for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    active_days = sum(1 for d in days if d["contributionCount"] > 0)
    best_streak = compute_streak_stats(days)
    sparkline = [d["contributionCount"] for d in days]
    return active_days, best_streak, sparkline


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


def render(total, active_days, best_streak, sparkline):
    width, height = 760, 200
    pad = 32

    total_num_y, total_label_y = 54, 76
    left_block_bottom = total_label_y + 4  # descender clearance

    right_x = width - pad
    stat_line_gap = 15    # a group's number baseline -> its own label baseline
    stat_group_gap = 24   # a group's label baseline -> the next group's number baseline
    # (must clear both the label's descenders and the next number's cap-height)
    active_num_y = 46
    active_label_y = active_num_y + stat_line_gap
    best_num_y = active_label_y + stat_group_gap
    best_label_y = best_num_y + stat_line_gap
    right_block_bottom = best_label_y + 4

    spark_gap = 14  # clearance between the taller text block and the sparkline's peak
    spark_y0 = max(left_block_bottom, right_block_bottom) + spark_gap
    spark = sparkline_svg(sparkline, pad, spark_y0, width - 2 * pad, height - pad - spark_y0)

    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
  <text x='{pad}' y='{total_num_y}' font-family='{FONT}' font-weight='700'
        font-size='34px' fill='#e6e6e6'>{total:,}</text>
  <text x='{pad}' y='{total_label_y}' font-family='{FONT}' font-weight='400'
        font-size='13px' fill='#8b949e'>Contributions in the last year</text>

  {spark}

  <text x='{right_x}' y='{active_num_y}' text-anchor='end' font-family='{FONT}'
        font-weight='700' font-size='20px' fill='#e6e6e6'>{active_days}</text>
  <text x='{right_x}' y='{active_label_y}' text-anchor='end' font-family='{FONT}'
        font-weight='400' font-size='11px' fill='#a78bfa'>Active days</text>

  <text x='{right_x}' y='{best_num_y}' text-anchor='end' font-family='{FONT}'
        font-weight='700' font-size='20px' fill='#e6e6e6'>{best_streak}</text>
  <text x='{right_x}' y='{best_label_y}' text-anchor='end' font-family='{FONT}'
        font-weight='400' font-size='11px' fill='#a78bfa'>Best Streak</text>
</svg>"""


def main():
    total, weeks = fetch_calendar()
    active_days, best_streak, sparkline = compute_stats(weeks)
    svg = render(total, active_days, best_streak, sparkline)
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "activity-stats.svg"), "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
