from generate_activity import (
    catmull_rom_path,
    catmull_rom_segments,
    compute_stats,
    compute_streak_stats,
    path_length,
    smoothed,
)


def demo():
    weeks = [
        {"contributionDays": [{"date": "2026-01-01", "contributionCount": 1},
                               {"date": "2026-01-02", "contributionCount": 0}]},
        {"contributionDays": [{"date": "2026-01-03", "contributionCount": 5},
                               {"date": "2026-01-04", "contributionCount": 3}]},
    ]
    active_days, best_streak, sparkline = compute_stats(weeks)
    assert active_days == 3
    assert best_streak == 2  # current streak (5,3) ties the longest, so it wins
    assert sparkline == [1, 0, 5, 3]

    # frozen-peak case: current streak is shorter than the historical longest
    frozen_days = [{"date": str(i), "contributionCount": c}
                   for i, c in enumerate([5, 5, 5, 0, 0, 1, 0])]
    assert compute_streak_stats(frozen_days) == 3

    assert smoothed([1, 0, 5, 3]) == [1.0, 0.5, 2.0, 2.25]

    path = catmull_rom_path([(0, 0), (1, 1), (2, 0)])
    assert path.startswith("M 0.00,0.00")
    assert "C " in path

    # sampled arc length must never undershoot the straight chord distance,
    # else the line-draw animation stops short of the path's true end
    points = [(0, 0), (10, 0), (20, 10), (30, 0)]
    segs = catmull_rom_segments(points)
    chord = sum(
        ((segs[i][3][0] - segs[i][0][0]) ** 2 + (segs[i][3][1] - segs[i][0][1]) ** 2) ** 0.5
        for i in range(len(segs))
    )
    assert path_length(segs) >= chord


if __name__ == "__main__":
    demo()
    print("ok")
