from generate_activity import catmull_rom_path, compute_stats, smoothed


def demo():
    weeks = [
        {"contributionDays": [{"date": "2026-01-01", "contributionCount": 1},
                               {"date": "2026-01-02", "contributionCount": 0}]},
        {"contributionDays": [{"date": "2026-01-03", "contributionCount": 5},
                               {"date": "2026-01-04", "contributionCount": 3}]},
    ]
    active_days, best_week, sparkline = compute_stats(weeks)
    assert active_days == 3
    assert best_week == 8
    assert sparkline == [1, 0, 5, 3]

    assert smoothed([1, 0, 5, 3]) == [1.0, 0.5, 2.0, 2.25]

    path = catmull_rom_path([(0, 0), (1, 1), (2, 0)])
    assert path.startswith("M 0.00,0.00")
    assert "C " in path


if __name__ == "__main__":
    demo()
    print("ok")
