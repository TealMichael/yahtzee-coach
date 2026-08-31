"""Read-only learning, exact counterfactuals, and unchanged Daily variety."""
import ast
from collections import Counter
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import random
from time import perf_counter

from daily_challenge import daily_challenges, challenge_set_id, summarize_attempt
from daily_spotlight import select_spotlight, build_what_if, evaluate_what_if, variety_snapshot
from exact_mode import ExactPolicyTable, build_exact_report, CATEGORIES, TIE_TOLERANCE
from puzzle_bank import _bank_break_day_plan

ROOT = Path(__file__).resolve().parent
POLICY = ExactPolicyTable(ROOT / "exact_policy.npz")


def answer_set(day, player="optimal"):
    answers = []
    for index, challenge in enumerate(daily_challenges(day)):
        rows = POLICY.analyze(challenge["scorecard"], challenge["dice"], challenge["roll_number"])
        rank = 0 if player == "optimal" or index % 3 == 0 else min(3, len(rows) - 1)
        hold = rows[rank]["hold"]
        report, meta = build_exact_report(
            POLICY, dice=challenge["dice"], scorecard=challenge["scorecard"],
            user_hold=hold, roll_number=challenge["roll_number"],
        )
        answers.append(dict(challenge=challenge, solver_record=meta, selected_hold=hold, report=report))
    return answers


def test_completion_and_quality_gates():
    answers = answer_set("2026-08-28")
    assert select_spotlight(answers, completed=False) is None
    assert select_spotlight(answers[:9], completed=True) is None
    wrong_source = deepcopy(answers)
    wrong_source[0]["solver_record"]["source"] = "fallback"
    assert select_spotlight(wrong_source, completed=True) is None
    mixed_date = deepcopy(answers)
    mixed_date[1]["challenge"]["daily_date"] = "2026-08-29"
    assert select_spotlight(mixed_date, completed=True) is None
    ties = deepcopy(answers)
    for answer in ties:
        answer["solver_record"]["points_lost"] = .03
    assert select_spotlight(ties, completed=True) is None
    generic = deepcopy(answers)
    for answer in generic:
        answer["solver_record"].update(simple_why="Good work.", coaching_family="generic", instructive_alternative_kind="runner_up")
    assert select_spotlight(generic, completed=True) is None
    spotlight = select_spotlight(answers, completed=True, policy=POLICY, seed="2026-08-28")
    assert spotlight and "You found the best hold" in spotlight["status"]
    assert spotlight["variant"] is not None
    print("PASS completion, exact-only, date, practical-tie, generic-prose and correct-answer gates")


def assert_exact_variation(variant, challenge):
    assert variant["dice"] == sorted(challenge["dice"])
    assert variant["roll_number"] == challenge["roll_number"]
    changes = [c for c in CATEGORIES if variant["scorecard"][c] != challenge["scorecard"][c]]
    assert changes == [variant["category"]]
    assert variant["category"] != "yahtzee"
    assert POLICY.state_index(variant["scorecard"]) is not None
    before = POLICY.analyze(challenge["scorecard"], challenge["dice"], challenge["roll_number"])
    after = POLICY.analyze(variant["scorecard"], variant["dice"], variant["roll_number"])
    ref, alt = variant["reference_hold"], variant["comparison_hold"]
    def value(rows, hold):
        return next(r["strategy_value"] for r in rows if r["hold"] == hold)
    before_margin = value(before, ref) - value(before, alt)
    after_margin = value(after, ref) - value(after, alt)
    assert abs(before_margin - variant["before_margin"]) < 1e-9
    assert abs(after_margin - variant["after_margin"]) < 1e-9
    changed = after[0]["strategy_value"] - value(after, ref) > TIE_TOLERANCE
    assert changed == variant["answer_changes"]
    assert before_margin > .10
    assert after_margin <= -.25 if changed else after_margin > .10
    if not changed:
        assert abs(before_margin - after_margin) >= .25
    for hold in (after[0]["hold"], ref, [], list(variant["dice"])):
        feedback = evaluate_what_if(POLICY, variant, hold)
        expected = after[0]["strategy_value"] - value(after, hold)
        assert abs(feedback["points_lost"] - expected) < 1e-9
        assert feedback["comparison_rows"][0]["Expected-point edge"] == f"{abs(before_margin):.2f}"
        assert feedback["comparison_rows"][1]["Expected-point edge"] == f"{abs(after_margin):.2f}"
        assert "within each scorecard" in feedback["note"]
        if expected <= TIE_TOLERANCE:
            assert feedback["choice_feedback"] == "You found a best hold."
    try:
        evaluate_what_if(POLICY, variant, [6] * 6)
        raise AssertionError("illegal hold accepted")
    except ValueError:
        pass


def test_42_day_learning_and_variety_audit():
    totals, family_counts, families, outcomes = Counter(), Counter(), Counter(), Counter()
    preparation_times = []
    for offset in range(42):
        day = (date(2026, 8, 28) + timedelta(days=offset)).isoformat()
        challenges = daily_challenges(day)
        snapshot = variety_snapshot(challenges)
        assert snapshot["unique_ids"] == 10
        assert snapshot["rolls"] == {1: 5, 2: 5}
        assert snapshot["stages"] == {"Opening": 2, "Midgame": 3, "Late Game": 3, "True Endgame": 2}
        assert 5 <= len(snapshot["families"]) <= 7
        assert len(snapshot["bank_break"]) <= 1
        assert snapshot["bank_break"] == ([_bank_break_day_plan(day)] if _bank_break_day_plan(day) else [])
        family_counts[len(snapshot["families"])] += 1
        families.update(snapshot["families"])
        outcomes.update(snapshot["bank_break"])
        for player in ("optimal", "mixed"):
            answers = answer_set(day, player)
            original = deepcopy(answers)
            summary = summarize_attempt([a["solver_record"] for a in answers])
            rng_state = random.getstate()
            started = perf_counter()
            spotlight = select_spotlight(answers, completed=True, policy=POLICY, seed=day)
            preparation_times.append(perf_counter() - started)
            assert spotlight == select_spotlight(answers, completed=True, policy=POLICY, seed=day)
            if spotlight:
                totals["spotlights"] += 1
                variant = spotlight["variant"]
                if variant:
                    totals["variations"] += 1
                    totals["changed" if variant["answer_changes"] else "unchanged"] += 1
                    challenge = answers[spotlight["index"]]["challenge"]
                    assert_exact_variation(variant, challenge)
                    assert variant == build_what_if(POLICY, challenge, seed=day)
                    # The caller can mutate a returned object without poisoning a shared cache.
                    variant["scorecard"]["ones"] = -999
                    assert build_what_if(POLICY, challenge, seed=day)["scorecard"]["ones"] != -999
            assert answers == original
            assert random.getstate() == rng_state
            assert summary == summarize_attempt([a["solver_record"] for a in answers])
            assert daily_challenges(day) == challenges
    assert totals["spotlights"] > 60 and totals["variations"] > 30
    assert totals["changed"] > 3 and totals["unchanged"] > 3
    assert abs(outcomes["BANK"] - outcomes["BREAK"]) <= 2
    assert .30 <= sum(outcomes.values()) / 42 <= .42
    print("PASS 42-day / 84-player-pattern audit:", dict(totals))
    print("PASS existing Daily variety:", dict(family_counts), "families per day; Bank/Break", dict(outcomes))
    print("PASS family exposure:", dict(families))
    print(f"PASS read-only preparation: max {max(preparation_times)*1000:.2f}ms; answers, scores, RNG and shared Daily unchanged")


def test_daily_baseline_fingerprints():
    # Captured from the literal 2K.13.4 package, not from this implementation.
    expected = {
        "2026-08-18": "3379f27e9b19404e0124c7e74646b179c8b63ab342738a95be801e0d74b723a7",
        "2026-08-28": "c48bc2b0a59d6fba736d12e86a710f2811715d68823c332896f15c9e2663b719",
        "2026-09-01": "d40cc985e4eabd95be535c3f721fb24d55b3687feec25341320e62671f03c64e",
        "2026-10-09": "340a7b288ddbae83669b2d005d353498abf008069835d902ed2721e1c0a9d899",
    }
    for day, fingerprint in expected.items():
        challenges = daily_challenges(day)
        assert sha256(json.dumps(challenges, sort_keys=True).encode()).hexdigest() == fingerprint
    assert challenge_set_id("2026-08-28", daily_challenges("2026-08-28")) == "2026-08-28-df3760e537"
    print("PASS historical, current and future Daily content/identities match 2K.13.4")


def test_ui_boundary():
    source = (ROOT / "app.py").read_text()
    tree = ast.parse(source)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    wrapper = ast.get_source_segment(source, funcs["render_daily_spotlight"])
    body = ast.get_source_segment(source, funcs["_render_daily_spotlight_content"])
    reveal = ast.get_source_segment(source, funcs["_reveal_daily_spotlight_answer"])
    results = ast.get_source_segment(source, funcs["render_daily_results"])
    assert "@st.fragment" in source and 'get("daily_completed")' in wrapper
    for banned in ("save_answer", "revise_answer", "complete_attempt", "load_daily_store", "build_live_report", "_set_app_mode"):
        assert banned not in body + wrapper
    assert "active_player_id" in body and "daily_set_id" in body and "daily_attempt_id" in body
    assert "prepared_key not in st.session_state" in body
    assert body.index("if not opened:") < body.index("_render_daily_review_body(answer)")
    assert body.index("if variant_key not in st.session_state:") < body.index('"**What if? · Unscored**"')
    assert '"See what changes"' in body and "on_click=_reveal_daily_spotlight_answer" in body
    assert "evaluate_what_if(load_exact_policy()" in reveal
    for banned in ("save_answer", "revise_answer", "complete_attempt", "load_daily_store"):
        assert banned not in reveal
    assert results.index("render_leaderboard_cards") < results.index("Your 10 Grades") < results.index("render_daily_spotlight()")
    assert results.index("render_daily_spotlight()") < results.index("_daily_review_item(answer)")
    for name in ("render_daily_question", "render_daily_submission_review", "render_daily_intro", "_render_friend_pick_peek"):
        assert "spotlight" not in ast.get_source_segment(source, funcs[name])
    assert 'startswith("daily_spotlight_")' in source
    print("PASS after-completion, own-player, unscored, lazy-detail, fragment and placement wiring")


if __name__ == "__main__":
    test_completion_and_quality_gates()
    test_daily_baseline_fingerprints()
    test_ui_boundary()
    test_42_day_learning_and_variety_audit()
    print("ALL PHASE 2K.14 DAILY SPOTLIGHT TESTS PASSED")
