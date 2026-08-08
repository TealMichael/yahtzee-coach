"""Published-strategy audit for Yahtzee Coach v22.

Run:
    python published_strategy_tests.py

These tests are benchmarks, not blind authority. Each test records the source and
scope. The app still uses scorecard-aware math outside the empty-card opening.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import yahtzee_engine as yc


@dataclass(frozen=True)
class PublishedCase:
    name: str
    source: str
    dice: List[int]
    roll_number: int
    scorecard: Dict[str, Any]
    expected: List[int]
    principle: str


def empty():
    return yc.create_empty_scorecard()


def cases():
    e = empty()
    return [
        PublishedCase("Verhoeff 11346", "Verhoeff", [1,1,3,4,6], 2, dict(e), [3,4], "Clean straight skeleton beats loose 6."),
        PublishedCase("Opening four of a kind", "Ballpark Figures", [2,4,4,4,4], 1, dict(e), [4,4,4,4], "Keep any four identical dice."),
        PublishedCase("Opening triple", "Ballpark Figures", [1,3,5,5,5], 1, dict(e), [5,5,5], "Keep any triple on first reroll."),
        PublishedCase("Opening 2345", "Ballpark Figures", [2,3,4,5,6], 1, dict(e), [2,3,4,5,6], "Made Large Straight is kept."),
        PublishedCase("Opening open-ended straight", "Ballpark Figures", [1,2,3,4,5], 1, dict(e), [1,2,3,4,5], "Made Large Straight is kept."),
        PublishedCase("Opening 11345 exception", "Ballpark Figures", [1,1,3,4,5], 1, dict(e), [3,4,5], "Never keep pair of 1s here; keep 345."),
        PublishedCase("Opening 11236 exception", "Ballpark Figures", [1,1,2,3,6], 1, dict(e), [6], "Avoid pair of 1s; lone 6 exception."),
        PublishedCase("Opening highest strong pair", "Ballpark Figures", [3,3,5,5,6], 1, dict(e), [5,5], "Among pairs 3-6, keep highest pair."),
        PublishedCase("Second reroll made small straight", "Ballpark Figures", [1,2,3,4,6], 2, dict(e), [1,2,3,4], "Keep a made Small Straight."),
        PublishedCase("Second reroll high triple over FH", "Ballpark Figures", [2,2,4,4,4], 2, dict(e), [4,4,4], "Break high-triple Full House."),
        PublishedCase("Second reroll low Full House", "Ballpark Figures", [2,2,2,6,6], 2, dict(e), [2,2,2,6,6], "Keep lower-value made Full House."),
        PublishedCase("Second reroll 234 draw", "Ballpark Figures", [1,2,3,4,6], 2, dict(e), [1,2,3,4], "Made straight outranks draw."),
        PublishedCase("Second reroll 12356 exception", "Ballpark Figures", [1,2,3,5,6], 2, dict(e), [2,3,5], "Published exceptional no-pair hold."),
        PublishedCase("Second reroll 12456 exception", "Ballpark Figures", [1,2,4,5,6], 2, dict(e), [4,5,6], "Published exceptional no-pair hold."),
        PublishedCase("Yahtzee bonus beats near straight", "Ballpark Figures", [1,2,3,3,3], 2,
            {**{k:0 for k in yc.YAHTZEE_CATEGORIES}, "large_straight":None, "yahtzee":50, "threes":9},
            [3,3,3], "With 100-point bonus live, triple can beat near Large Straight."),
    ]


def run(verbose=True):
    results=[]
    for case in cases():
        ranked=yc.analyze_all_holds_by_roll_number(case.dice, case.scorecard, case.roll_number)
        best=sorted(ranked[0]["hold"])
        expected=sorted(case.expected)
        ok=best==expected
        results.append((case,ok,best,[(r["hold"],round(float(r["strategy_value"]),2)) for r in ranked[:4]]))
    passed=sum(ok for _,ok,_,_ in results)
    if verbose:
        print("PUBLISHED STRATEGY AUDIT")
        print("="*64)
        for case,ok,best,top in results:
            print(("PASS" if ok else "FAIL")+f": [{case.source}] {case.name}")
            print("  Best:",best,"Expected:",case.expected)
            print("  Principle:",case.principle)
            if not ok: print("  Top:",top)
        print("="*64)
        print(f"Total: {passed} PASS / {len(results)-passed} FAIL")
        print("Scope:",yc.v22_strategy_model_info()["scope"])
        print("Not claimed:",yc.v22_strategy_model_info()["not_claimed"])
    return {"passed":passed,"failed":len(results)-passed,"details":results}


if __name__=="__main__":
    outcome=run(True)
    raise SystemExit(1 if outcome["failed"] else 0)
