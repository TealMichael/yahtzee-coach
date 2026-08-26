from pathlib import Path

from exact_mode import (
    EXPECTED_EXACT_POLICY_SHA256,
    ExactPolicyTable,
    build_exact_report,
    exact_policy_sha256,
)
from retro_podium import personal_medal_moment_html


ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def ceremony(board, player_id="gold"):
    return personal_medal_moment_html(
        board,
        active_player_id=player_id,
        active_player_name="Viewer",
        group_name="Who is the Yahtzee Master?",
        date_label="August 25, 2026",
        avatar_config={},
        medal_totals={"gold": 2, "silver": 3, "bronze": 3},
    )


def test_yesterday_podium_names():
    html = ceremony([
        {"player_id": "gold", "display_name": "Jonas", "rank": 1},
        {"player_id": "silver", "display_name": "Jenny", "rank": 2},
        {"player_id": "bronze", "display_name": "Michael", "rank": 3},
        {"player_id": "fourth", "display_name": "Will", "rank": 4},
    ])
    assert "YESTERDAY'S PODIUM" in html
    assert all(name in html for name in ("Jonas", "Jenny", "Michael"))
    assert "Will" not in html
    assert all(label in html for label in ("GOLD", "SILVER", "BRONZE"))
    assert "podium-name-cell" in html
    assert ".moment{position:relative;height:560px" in html
    print("PASS yesterday's gold, silver, and bronze names appear beneath their medals")


def test_tied_podium_names_and_html_safety():
    html = ceremony([
        {"player_id": "gold", "display_name": "Jonas", "rank": 1},
        {"player_id": "gold2", "display_name": "Jenny", "rank": 1},
        {"player_id": "bronze", "display_name": "<Michael>", "rank": 3},
    ])
    assert "Jonas / Jenny" in html
    assert "&lt;Michael&gt;" in html
    assert "<Michael>" not in html
    assert "<b>—</b>" in html
    print("PASS tied podiums preserve competition ranking and escape player names")


def test_reported_endgame_has_optional_detailed_math():
    scorecard = {
        "ones": 3, "twos": None, "threes": 9, "fours": 4,
        "fives": 15, "sixes": 12, "three_of_a_kind": 20,
        "four_of_a_kind": 16, "full_house": 25, "small_straight": 30,
        "large_straight": None, "yahtzee": 0, "chance": 20,
    }
    report, meta = build_exact_report(
        POLICY,
        dice=[1, 1, 3, 5, 6],
        scorecard=scorecard,
        user_hold=[3, 5, 6],
        roll_number=1,
    )
    detail = meta["math_detail"]
    assert "12 of 216" in detail and "2 of 36" in detail
    assert "18.4% versus 16.4%" in detail
    assert "0.82 expected Large Straight points" in detail
    assert "43 plus at most 10 in Twos is 53" in detail
    assert "Math detail:" in report
    assert meta["points_lost"] > 0.87
    print("PASS reported straight puzzle includes the full optional calculation")


def test_ui_and_release_guards():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'APP_RELEASE = "v43B Phase 2K.13.4"' in app
    assert 'components.html(ceremony, height=560, scrolling=False)' in app
    assert 'with st.expander("📐 See the math", expanded=False):' in app
    assert '**Detailed calculation:**' in app
    assert exact_policy_sha256(ROOT / "exact_policy.npz") == EXPECTED_EXACT_POLICY_SHA256
    print("PASS Daily and Practice expose optional math while the exact policy stays frozen")


def main():
    test_yesterday_podium_names()
    test_tied_podium_names_and_html_safety()
    test_reported_endgame_has_optional_detailed_math()
    test_ui_and_release_guards()
    print("ALL PHASE 2K.13.4 MEDAL-NAME + MATH-DETAIL TESTS PASSED")


if __name__ == "__main__":
    main()
