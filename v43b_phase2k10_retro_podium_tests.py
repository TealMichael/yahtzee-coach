from pathlib import Path

from retro_podium import medal_moment_copy, personal_medal_moment_html

ROOT = Path(__file__).parent


def require(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        raise AssertionError(message)


def run():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    retro = (ROOT / "retro_podium.py").read_text(encoding="utf-8")
    normal = [
        {"player_id": "a", "display_name": "Gold", "rank": 1, "total_ev_loss": 1.11},
        {"player_id": "b", "display_name": "Silver", "rank": 2, "total_ev_loss": 2.22},
        {"player_id": "c", "display_name": "Bronze", "rank": 3, "total_ev_loss": 3.33},
        {"player_id": "d", "display_name": "Fourth", "rank": 4, "total_ev_loss": 3.75},
    ]
    tied = [
        {"player_id": "a", "display_name": "Jenny", "rank": 1, "total_ev_loss": 1.766},
        {"player_id": "b", "display_name": "Stephanie", "rank": 1, "total_ev_loss": 1.774},
        {"player_id": "c", "display_name": "Paul", "rank": 3, "total_ev_loss": 2.72},
    ]
    require('APP_RELEASE = "v43B Phase 2K.12.2"' in app, "later release preserves and simplifies the retro celebration")
    require("from retro_podium import personal_medal_moment_html" in app, "app now uses personal medal moment renderer")
    require("components.html(ceremony, height=510, scrolling=False)" in app, "personal moment stays lightweight")
    require("mark_yesterday_ceremony_seen_now(today)" in app, "once-per-day behavior remains")
    require(medal_moment_copy(normal, "a") == ("YOU WON YESTERDAY!", "Can you defend the title?", 1), "gold hook is preserved")
    require(medal_moment_copy(normal, "b")[2] == 2 and medal_moment_copy(normal, "c")[2] == 3, "silver and bronze remain personal medal moments")
    require(medal_moment_copy(tied, "a")[0] == "TIED FOR GOLD!", "tie-aware gold survives the simplification")
    html = personal_medal_moment_html(
        tied,
        active_player_id="a",
        active_player_name="Mike <Coach>",
        group_name="Friends & Family",
        date_label="August 20, 2026",
        avatar_config={"hair":"curly","outfit":"red_tee","skin":"warm","accessory":"none","shoes":"blue"},
        medal_totals={"gold":4,"silver":2,"bronze":1},
    )
    require("PIXEL MIKE" in html and "ALL-TIME MEDALS" in html, "simple version keeps Pixel Mike plus lifetime medals")
    require(".stadium-light" not in retro and ".podium-step" not in retro, "busy 2K.10 podium production is intentionally removed")
    require("SKIP ›" in html and "prefers-reduced-motion" in html, "skip/reduced motion protections survive")
    require("Mike &lt;Coach&gt;" in html and "Friends &amp; Family" in html, "dynamic text remains escaped")
    print("Phase 2K.10 celebration concept regression checks passed under 2K.11 simplification")


if __name__ == "__main__":
    run()
