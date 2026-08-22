from pathlib import Path

from daily_store import rank_leaderboard_rows

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def run():
    # Raw values differ, but both display as 1.77. They must share gold.
    rows = [
        {"player_id": "j", "display_name": "Jenny", "total_ev_loss": 1.7664, "exact_count": 7, "worst_miss": 1.2},
        {"player_id": "s", "display_name": "Stephanie", "total_ev_loss": 1.7731, "exact_count": 10, "worst_miss": 0.2},
        {"player_id": "p", "display_name": "Paul", "total_ev_loss": 2.72, "exact_count": 7, "worst_miss": 1.0},
    ]
    rank_leaderboard_rows(rows)
    require([row["display_name"] for row in rows] == ["Jenny", "Stephanie", "Paul"], "ties are ordered only for display, not broken competitively")
    require([row["rank"] for row in rows] == [1, 1, 3], "competition ranking produces 1, 1, 3")

    # Same hundredth wins over old hidden tiebreakers.
    rows2 = [
        {"player_id": "a", "display_name": "Alpha", "total_ev_loss": 4.721, "exact_count": 3, "worst_miss": 4.0},
        {"player_id": "b", "display_name": "Beta", "total_ev_loss": 4.724, "exact_count": 10, "worst_miss": 0.1},
        {"player_id": "c", "display_name": "Gamma", "total_ev_loss": 4.73, "exact_count": 10, "worst_miss": 0.0},
    ]
    rank_leaderboard_rows(rows2)
    require([row["rank"] for row in rows2] == [1, 1, 3], "best holds and biggest miss do not break a displayed-score tie")

    rows3 = [
        {"player_id": "a", "display_name": "First", "total_ev_loss": 1.00, "exact_count": 1, "worst_miss": 1.0},
        {"player_id": "b", "display_name": "Second A", "total_ev_loss": 2.00, "exact_count": 1, "worst_miss": 1.0},
        {"player_id": "c", "display_name": "Second B", "total_ev_loss": 2.00, "exact_count": 9, "worst_miss": 0.1},
        {"player_id": "d", "display_name": "Fourth", "total_ev_loss": 3.00, "exact_count": 10, "worst_miss": 0.0},
    ]
    rank_leaderboard_rows(rows3)
    require([row["rank"] for row in rows3] == [1, 2, 2, 4], "competition ranking also handles a tie for second")

    app = (ROOT / "app.py").read_text(encoding="utf-8")
    supabase = (ROOT / "supabase_daily_store.py").read_text(encoding="utf-8")
    retro = (ROOT / "retro_podium.py").read_text(encoding="utf-8")
    require('APP_RELEASE = "v43B Phase 2K.12.1"' in app, "hotfix release label is current")
    require("Same score to the hundredth = a real tie" in app, "ranking explanation tells players the actual rule")
    require("You're tied for #{rank} of {completed} today." in app, "today banner is tie-aware")
    require('rank_value = f"T-{rank} of {len(board)}"' in app, "result card uses T-rank for a tie")
    require("Group rank right now: Tied for #" in app, "shared result is tie-aware")
    require("TIED FOR GOLD!" in retro and "_rank_tied" in retro, "personal medal moment celebrates tied gold medalists")
    require('prefix = "Tied for" if tied else "You finished"' in retro, "non-podium yesterday recap is tie-aware")
    require("rank_leaderboard_rows(board)" in supabase and "return rank_leaderboard_rows(rows)" in supabase, "Supabase uses the same tie-ranking contract")

    print("Phase 2K.9.1 tie-handling hotfix checks passed")


if __name__ == "__main__":
    run()
