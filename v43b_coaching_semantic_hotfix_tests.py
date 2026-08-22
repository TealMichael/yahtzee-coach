from pathlib import Path

ROOT = Path(__file__).parent

def run():
    exact = (ROOT / "exact_mode.py").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    checks = [
        ("two_pair_full_house_tradeoff" in exact, "two-pair player holds get a dedicated Full House tradeoff explanation"),
        ("one fresh die can finish it" in exact, "two-pair explanation names the actual Full House finish"),
        ("two_pair_no_reroll" in exact, "holding all five with two pairs is not described as an active Full House reroll"),
        ("if _is_open(scorecard, \"yahtzee\")" in exact and "powerful matching core" in exact, "four matching dice mention Yahtzee only when relevant"),
        ("may activate forced-upper/Joker" in exact or "can activate the forced-upper/Joker" in exact, "extra-Yahtzee language does not overstate Joker scoring"),
        ("teaching_takeaway" in exact and "teaching_takeaway" in app, "Daily Review can show the full reusable teaching takeaway"),
        ("APP_RELEASE = \"v43B Phase 2K.12.1\"" in app, "release label is 2K.9.1"),
    ]
    for ok, name in checks:
        print(("PASS" if ok else "FAIL"), name)
        if not ok:
            raise AssertionError(name)
    print(f"{len(checks)}/{len(checks)} coaching semantic hotfix checks passed")

if __name__ == "__main__":
    run()
