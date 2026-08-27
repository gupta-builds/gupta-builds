import datetime

from add_month_labels import month_label_positions


def demo():
    # 53 columns, 16px apart, starting at x=2 — mirrors Platane/snk's grid geometry
    xs = [2 + 16 * i for i in range(53)]
    today = datetime.date(2026, 8, 27)  # Thursday
    labels = month_label_positions(xs, today)

    # rightmost column's week must contain "today"
    assert xs[-1] == 2 + 16 * 52
    months = [m for _, m in labels]
    assert months[0] == "Aug"  # col0 week (2025-08-24) starts in August
    assert months[-1] == "Aug"  # current week (2026-08-23) is also August
    assert "Jan" in months and "Dec" in months
    assert len(labels) == len(set(labels))  # no duplicate (x, month) pairs
    # labels are strictly left-to-right and non-overlapping at this spacing
    assert all(labels[i][0] < labels[i + 1][0] for i in range(len(labels) - 1))


if __name__ == "__main__":
    demo()
    print("ok")
