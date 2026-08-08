from session_learning import build_session_learning_summary, lesson_to_skill


def rec(title, loss):
    return {"source": "exact", "lesson_title": title, "points_lost": loss}


def run():
    tests = []

    s = build_session_learning_summary([rec("Build from the triple", 0.0)] * 4)
    tests.append(("waits for five rounds", not s["ready"] and s["rounds_needed"] == 1))

    s = build_session_learning_summary([
        rec("Build from the triple", 0.0),
        rec("Protect four matching dice", 0.1),
        rec("Keep the best matching base", 0.4),
        rec("Protect the straight core", 0.0),
        rec("Preserve the useful straight fragment", 0.2),
    ])
    strength_names = [x["skill"] for x in s["strengths"]]
    tests.append(("finds repeated strengths", s["ready"] and "Matching-dice structures" in strength_names and "Straight structure" in strength_names))

    s = build_session_learning_summary([
        rec("Protect the straight core", 3.5),
        rec("Preserve the useful straight fragment", 2.5),
        rec("Build from the triple", 0.0),
        rec("Build from the triple", 0.0),
        rec("Protect a made hand", 0.0),
    ])
    tests.append(("finds exact-value focus area", s["focus_areas"][0]["skill"] == "Straight structure"))

    tests.append(("groups upper boxes", lesson_to_skill("Build the Sixes box") == "Upper-section targeting" and lesson_to_skill("Build the Twos box") == "Upper-section targeting"))

    s = build_session_learning_summary([
        rec("Build from the triple", 0.0),
        rec("Protect four matching dice", 0.0),
        rec("Protect the straight core", 0.0),
        rec("Preserve the useful straight fragment", 0.0),
        rec("Protect a made hand", 0.0),
    ])
    tests.append(("perfect session has no focus area", not s["focus_areas"] and s["optimal_rate"] == 1.0))

    s = build_session_learning_summary([
        rec("Build from the triple", 3.0),
        rec("Protect the straight core", 2.0),
        rec("Build the Sixes box", 1.5),
        rec("Build from the triple", 0.0),
        rec("Protect the straight core", 0.0),
        rec("Build the Sixes box", 0.0),
    ])
    tests.append(("detects improving trend", s["trend"].startswith("Trending better")))

    s = build_session_learning_summary([
        {"source": "legacy_fallback", "lesson_title": "Protect the straight core", "points_lost": 99},
        rec("Build from the triple", 0.0), rec("Build from the triple", 0.0),
        rec("Protect a made hand", 0.0), rec("Protect a made hand", 0.0), rec("Build the Sixes box", 0.0),
    ])
    tests.append(("ignores fallback records", s["rounds"] == 5 and s["avg_points_lost"] == 0.0))

    passed = 0
    for name, ok in tests:
        if ok:
            print(f"PASS: {name}")
            passed += 1
        else:
            print(f"FAIL: {name}")
    print(f"\n{passed} PASS / {len(tests) - passed} FAIL")
    if passed != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    run()
