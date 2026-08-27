#!/usr/bin/env python3
"""Overlay calendar month labels below the Platane/snk contribution bar, in place."""
import datetime
import re
import sys


def month_label_positions(xs, today):
    """xs: sorted x-coords of the grid's weekly columns, oldest week first."""
    days_since_sunday = (today.weekday() + 1) % 7
    this_sunday = today - datetime.timedelta(days=days_since_sunday)
    col0_sunday = this_sunday - datetime.timedelta(weeks=len(xs) - 1)

    labels = []
    prev_month = None
    for i, x in enumerate(xs):
        sunday = col0_sunday + datetime.timedelta(weeks=i)
        if sunday.month != prev_month:
            labels.append((x, sunday.strftime("%b")))
            prev_month = sunday.month
    return labels


def add_month_labels(path, today=None):
    today = today or datetime.date.today()
    with open(path) as f:
        content = f.read()

    xs = sorted(set(
        float(x) for x in re.findall(r'<rect class="c[^"]*"[^>]*\sx="([-\d.]+)"', content)
    ))
    if not xs:
        return

    labels = month_label_positions(xs, today)
    color = "#8b949e" if "-dark" in path else "#57606a"
    label_y = 144 + 12 + 11  # just below the u-bar (y=144, height=12)
    text_els = "".join(
        f'<text x="{x:.1f}" y="{label_y}" font-size="9" '
        f'font-family="sans-serif" fill="{color}">{month}</text>'
        for x, month in labels
    )

    svg_open = re.search(
        r'<svg viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)" width="([\d.]+)" height="([\d.]+)"',
        content,
    )
    min_x, min_y, vb_w, vb_h, width, height = svg_open.groups()
    extra = 20  # room for the label row below the bar
    new_tag = (
        f'<svg viewBox="{min_x} {min_y} {vb_w} {float(vb_h) + extra}" '
        f'width="{width}" height="{float(height) + extra}"'
    )
    content = content.replace(svg_open.group(0), new_tag, 1)
    content = content.replace("</svg>", text_els + "</svg>")

    with open(path, "w") as f:
        f.write(content)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        add_month_labels(p)
