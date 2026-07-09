"""
Yahtzee Coach strategy regression tests.

Run from the repo folder with:

    python strategy_tests.py

This file is intentionally separate from the Streamlit app. Streamlit does not need
it to run the app, but keeping it in GitHub gives us a stable checklist before any
future strategy patch.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Iterable, List, Dict, Any

import yahtzee_engine as yc


Hold = List[int]
Scorecard = Dict[str, Any]


UPPER_CHANCE_BASE: Scorecard = {
    "ones": 3,
    "twos": 6,
    "threes": 9,
    "fours": None,
    "fives": None,
    "sixes": None,
    "three_of_a_kind": None,
    "four_of_a_kind": None,
    "full_house": None,
    "small_straight": 30,
    "large_straight": 40,
    "yahtzee": None,
    "chance": None,
}


@dataclass(frozen=True)
class StrategyCase:
    name: str
    dice: List[int]
    roll_number: int
    scorecard: Scorecard
    acceptable_best_holds: List[Hold]
    note: str = ""


def sorted_hold(hold: Iterable[int]) -> Hold:
    return sorted(list(hold))


def normalize_holds(holds: Iterable[Iterable[int]]) -> List[Hold]:
    return [sorted_hold(h) for h in holds]


def best_holds_for_case(case: StrategyCase):
    results = yc.analyze_all_holds_by_roll_number(
        case.dice,
        case.scorecard,
        case.roll_number,
    )
    if not results:
        raise AssertionError(f"{case.name}: engine returned no hold results")
    return results


def check_case(case: StrategyCase) -> Dict[str, Any]:
    results = best_holds_for_case(case)
    best_hold = sorted_hold(results[0]["hold"])
    acceptable = normalize_holds(case.acceptable_best_holds)
    passed = best_hold in acceptable
    return {
        "name": case.name,
        "passed": passed,
        "best_hold": best_hold,
        "acceptable": acceptable,
        "top_5": [
            (sorted_hold(r["hold"]), round(float(r["strategy_value"]), 2))
            for r in results[:5]
        ],
        "note": case.note,
    }


def build_strategy_cases() -> List[StrategyCase]:
    empty = yc.create_empty_scorecard()

    return [
        # Verhoeff/article-inspired correction
        StrategyCase(
            name="Verhoeff Roll 2 article case prefers clean 3,4 skeleton",
            dice=[1, 1, 3, 4, 6],
            roll_number=2,
            scorecard=dict(empty),
            acceptable_best_holds=[[3, 4]],
            note="Protects straight flexibility; should not over-keep the loose 6.",
        ),

        # Original smoke-test protections
        StrategyCase(
            name="Roll 2 pair of fours chases Fours",
            dice=[1, 4, 4, 5, 6],
            roll_number=2,
            scorecard=dict(UPPER_CHANCE_BASE),
            acceptable_best_holds=[[4, 4]],
        ),
        StrategyCase(
            name="Roll 2 single useful four keeps the 4",
            dice=[1, 1, 2, 2, 4],
            roll_number=2,
            scorecard=dict(UPPER_CHANCE_BASE),
            acceptable_best_holds=[[4]],
        ),
        StrategyCase(
            name="Roll 2 pair of sixes chases Sixes",
            dice=[2, 4, 5, 6, 6],
            roll_number=2,
            scorecard=dict(UPPER_CHANCE_BASE),
            acceptable_best_holds=[[6, 6]],
        ),
        StrategyCase(
            name="Roll 2 high loose dice still reasonable",
            dice=[1, 3, 4, 5, 6],
            roll_number=2,
            scorecard=dict(UPPER_CHANCE_BASE),
            acceptable_best_holds=[[5, 6], [6], [5]],
        ),
        StrategyCase(
            name="Roll 2 Full House two-pair with Chance open protects both pairs",
            dice=[2, 4, 4, 5, 5],
            roll_number=2,
            scorecard=dict(UPPER_CHANCE_BASE),
            acceptable_best_holds=[[4, 4, 5, 5]],
        ),
        StrategyCase(
            name="Roll 2 Full House two-pair with Chance used prefers 5s",
            dice=[2, 4, 4, 5, 5],
            roll_number=2,
            scorecard={**UPPER_CHANCE_BASE, "chance": 22},
            acceptable_best_holds=[[5, 5]],
        ),

        # Roll 1 protections
        StrategyCase(
            name="Roll 1 triple fives protected",
            dice=[2, 3, 5, 5, 5],
            roll_number=1,
            scorecard=dict(empty),
            acceptable_best_holds=[[5, 5, 5]],
        ),
        StrategyCase(
            name="Roll 1 triple ones protected when Yahtzee is open",
            dice=[1, 1, 1, 2, 6],
            roll_number=1,
            scorecard=dict(empty),
            acceptable_best_holds=[[1, 1, 1]],
        ),
        StrategyCase(
            name="Roll 1 article example avoids low pair of 1s",
            dice=[1, 1, 2, 5, 6],
            roll_number=1,
            scorecard=dict(empty),
            acceptable_best_holds=[[5], [6], [5, 6]],
        ),
        StrategyCase(
            name="Roll 1 triple sixes beats locking in Full House",
            dice=[1, 1, 6, 6, 6],
            roll_number=1,
            scorecard=dict(empty),
            acceptable_best_holds=[[6, 6, 6]],
            note="Guards against early Full House greed.",
        ),

        # v16 extra-Yahtzee / Joker awareness guardrail
        StrategyCase(
            name="Extra Yahtzee/Joker awareness values second Yahtzee path",
            dice=[6, 6, 6],
            roll_number=2,
            scorecard={
                "ones": 3,
                "twos": 6,
                "threes": 9,
                "fours": 12,
                "fives": 15,
                "sixes": 18,
                "three_of_a_kind": None,
                "four_of_a_kind": None,
                "full_house": None,
                "small_straight": None,
                "large_straight": None,
                "yahtzee": 50,
                "chance": None,
            },
            acceptable_best_holds=[[6, 6, 6]],
        ),
    ]


def run_strategy_regression_tests(verbose: bool = True) -> Dict[str, Any]:
    cases = build_strategy_cases()
    results = [check_case(case) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed

    if verbose:
        print("YAHTZEE COACH STRATEGY REGRESSION TESTS")
        print("=" * 60)
        for result in results:
            status = "PASS" if result["passed"] else "FAIL"
            print()
            print(f"{status}: {result['name']}")
            print(f"  Best hold: {result['best_hold']}")
            print(f"  Acceptable: {result['acceptable']}")
            if result["note"]:
                print(f"  Note: {result['note']}")
            if not result["passed"]:
                print(f"  Top 5: {result['top_5']}")

        print()
        print("=" * 60)
        print(f"Summary: {passed} PASS / {failed} FAIL")

    return {"passed": passed, "failed": failed, "details": results}


def run_coach_report_smoke_tests(verbose: bool = True) -> Dict[str, Any]:
    """Make sure classroom report generation still returns usable text."""
    empty = yc.create_empty_scorecard()
    samples = [
        ("Optimal Verhoeff-style hold", [1, 1, 3, 4, 6], [3, 4], 2, dict(empty)),
        ("Suboptimal low-pair choice", [1, 1, 2, 5, 6], [1, 1], 1, dict(empty)),
        ("Triple protection choice", [1, 1, 6, 6, 6], [6, 6, 6], 1, dict(empty)),
    ]

    failures = []
    for name, dice, user_hold, roll_number, scorecard in samples:
        try:
            report = yc.coach_report_for_user_hold_by_roll_number(
                dice=dice,
                scorecard=scorecard,
                user_hold=user_hold,
                roll_number=roll_number,
            )
            if not isinstance(report, str) or len(report.strip()) < 20:
                failures.append((name, "Report was missing or too short"))
        except Exception as exc:  # pragma: no cover - printed for manual use
            failures.append((name, repr(exc)))

    if verbose:
        print()
        print("COACH REPORT SMOKE TESTS")
        print("=" * 60)
        for name, failure in failures:
            print(f"FAIL: {name} — {failure}")
        if not failures:
            print("PASS: report generation returned usable text for all samples")

    return {"passed": len(samples) - len(failures), "failed": len(failures), "details": failures}


def run_scope_guard_tests(verbose: bool = True) -> Dict[str, Any]:
    """Confirm the app remains a Roll 1 / Roll 2 hold trainer, not Roll 3."""
    try:
        yc.analyze_all_holds_by_roll_number([1, 2, 3, 4, 5], yc.create_empty_scorecard(), 3)
    except ValueError:
        passed = True
    except Exception:
        passed = False
    else:
        passed = False

    if verbose:
        print()
        print("SCOPE GUARD TEST")
        print("=" * 60)
        print("PASS: Roll 3 is rejected as intended" if passed else "FAIL: Roll 3 was not rejected cleanly")

    return {"passed": int(passed), "failed": int(not passed)}


def run_all_tests(verbose: bool = True) -> Dict[str, Any]:
    strategy = run_strategy_regression_tests(verbose=verbose)
    reports = run_coach_report_smoke_tests(verbose=verbose)
    scope = run_scope_guard_tests(verbose=verbose)

    total_passed = strategy["passed"] + reports["passed"] + scope["passed"]
    total_failed = strategy["failed"] + reports["failed"] + scope["failed"]

    if verbose:
        print()
        print("OVERALL RESULT")
        print("=" * 60)
        print(f"Total: {total_passed} PASS / {total_failed} FAIL")

    return {
        "passed": total_passed,
        "failed": total_failed,
        "strategy": strategy,
        "reports": reports,
        "scope": scope,
    }


if __name__ == "__main__":
    summary = run_all_tests(verbose=True)
    sys.exit(1 if summary["failed"] else 0)
