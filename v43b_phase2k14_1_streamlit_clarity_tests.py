"""Real Streamlit rendering for the reported rank-eight review."""
from streamlit.testing.v1 import AppTest


def main():
    at = AppTest.from_file("qa_winner_first_app.py", default_timeout=30).run()
    assert not at.exception
    visible = "\n".join(str(item.value) for item in at.markdown)

    assert "Your hold: #8 of 24" in visible
    assert "Crowded decision" in visible
    assert "Keep 5 wins" in visible
    assert "Expected upper box" in visible and "Bonus benchmark" in visible
    assert "2.92" in visible and "11.11" in visible
    assert "66.5%" in visible and "35.8%" in visible
    assert "SS 26.9% · LS 6.0%" in visible
    assert "SS 39.4% · LS 14.6%" in visible
    assert "8.60 pts" in visible and "13.10 pts" in visible
    assert "about 4.50 more expected straight points" in visible
    assert "See the exact math and hold rankings" in visible
    print("PASS real Streamlit Daily review renders the turn-aware comparison card in one open review")


if __name__ == "__main__":
    main()
