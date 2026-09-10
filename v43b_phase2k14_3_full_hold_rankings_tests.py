"""Phase 2K.14.3 player-facing full-hold-ranking cleanup regressions."""
from hashlib import sha256
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parent


def file_sha(name):
    return sha256((ROOT / name).read_bytes()).hexdigest()


def test_daily_card_renders_rankings_first_with_player_copy():
    at = AppTest.from_file("qa_winner_first_app.py", default_timeout=30).run()
    assert not at.exception
    visible = "\n".join(str(item.value) for item in at.markdown)

    disclosure = "<details><summary>📐 See full hold rankings</summary>"
    rankings = "<div class='evidence-hold-spread'>"
    about = "<p class='evidence-about-math'><b>About the math:</b>"
    assert disclosure in visible
    assert visible.index(disclosure) < visible.index(rankings) < visible.index(about)
    assert "#1: keep 5 — Best" in visible
    assert "−" in visible and "expected points" in visible
    assert "The comparison above shows exact odds and expected values for individual scoring paths." in visible
    assert "The final hold ranking also considers the entire remaining scorecard." in visible
    assert "See the exact math and hold rankings" not in visible
    assert "Displayed plan statistics are exact category-specific calculations" not in visible
    assert "locked full-game policy" not in visible
    assert "locked exact policy" not in visible
    print("PASS Daily card reads Comparison → Why → Takeaway → Full hold rankings")


def test_shared_practice_and_daily_renderer_remain_intact():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    render_start = app.index("def render_comparison_card")
    render_end = app.index("def render_result", render_start)
    renderer = app[render_start:render_end]
    practice = app[app.index("def render_result"):app.index("# ---------------------------------------------------------------------------\n# v43B Phase 2E")]
    daily = app[app.index("def _render_daily_review_body"):app.index("def _daily_review_item")]

    assert "player_rank_line" in renderer
    assert 'esc(card.get("math_detail"))' not in renderer
    assert "See full hold rankings" in renderer
    assert "About the math:" in renderer
    assert "render_comparison_card(" in practice
    assert "top_holds=top_holds" in practice
    assert "render_comparison_card(" in daily
    assert 'top_holds=extract_section(report, "Top exact holds:")' in daily
    assert ".evidence-about-math" in app
    assert 'APP_RELEASE = "v43B Phase 2K.14.6"' in app
    print("PASS Practice and Daily reuse the unchanged shared comparison component")


def test_strategy_and_comparison_engine_are_byte_for_byte_unchanged():
    assert file_sha("exact_mode.py") == "b0d5395973a1b6918f298f21a951eac8c5f6e9d82a7b140749720811983524b5"
    assert file_sha("daily_spotlight.py") == "119c516ee9c82118b462619d63d00b87c93bd02883af34e7629e9aa929d4f274"
    assert file_sha("exact_policy.npz") == "cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b"
    print("PASS strategy, turn-aware evidence, Spotlight, rankings, and Points Lost are unchanged")


def main():
    test_daily_card_renders_rankings_first_with_player_copy()
    test_shared_practice_and_daily_renderer_remain_intact()
    test_strategy_and_comparison_engine_are_byte_for_byte_unchanged()
    print("ALL PHASE 2K.14.3 FULL HOLD RANKINGS TESTS PASSED")


if __name__ == "__main__":
    main()
