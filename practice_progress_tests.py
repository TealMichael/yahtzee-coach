from practice_progress import build_practice_progress, newly_unlocked_badges


def rec(loss, lesson="Build the Sixes box"):
    return {"source": "exact", "points_lost": loss, "lesson_title": lesson}


# Empty session.
p = build_practice_progress([])
assert p["rounds"] == 0 and p["avg_points_lost"] is None and p["badges"] == []
print("PASS: empty session")

# First exact play unlocks Bullseye.
p = build_practice_progress([rec(0)])
assert p["current_exact_streak"] == 1
assert "bullseye" in p["badge_ids"]
print("PASS: first exact badge")

# Three exact plays unlock the three-straight achievement.
p = build_practice_progress([rec(0), rec(0), rec(0)])
assert p["current_exact_streak"] == 3 and p["best_exact_streak"] == 3
assert "three_straight" in p["badge_ids"]
print("PASS: exact streak")

# A miss resets the current exact streak but preserves the best streak.
p = build_practice_progress([rec(0), rec(0), rec(0), rec(1.2)])
assert p["current_exact_streak"] == 0 and p["best_exact_streak"] == 3
print("PASS: streak reset and best streak preserved")

# Five strong examples of the same skill can earn conservative session mastery.
p = build_practice_progress([
    rec(0.0, "Protect four matching dice"),
    rec(0.1, "Build from the triple"),
    rec(0.2, "Keep both pairs alive"),
    rec(0.0, "Keep the best matching base"),
    rec(0.3, "Build from the triple"),
])
mastered = [row for row in p["mastery"] if row["skill"] == "Matching-dice structures"]
assert mastered and mastered[0]["level"] == "Session Mastery"
assert "session_mastery" in p["badge_ids"]
print("PASS: session mastery")

# Sharp Session requires a real sample, not a few easy rounds.
p = build_practice_progress([rec(0.5) for _ in range(10)])
assert "sharp_session" in p["badge_ids"]
print("PASS: sharp session")

# Newly unlocked badge helper only reports the delta.
before = [rec(0), rec(0)]
after = before + [rec(0)]
new = newly_unlocked_badges(before, after)
assert [badge["id"] for badge in new] == ["three_straight"]
print("PASS: new badge delta")

# Legacy fallback records are ignored.
p = build_practice_progress([rec(0), {"source": "legacy_fallback", "points_lost": 0}])
assert p["rounds"] == 1
print("PASS: fallback ignored")

print("\n8 PASS / 0 FAIL")
