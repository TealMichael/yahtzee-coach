"""Real Streamlit widget interaction for the optional Daily Spotlight."""
from copy import deepcopy

from streamlit.testing.v1 import AppTest


def button(at, label):
    return next(item for item in at.button if item.label == label)


def main():
    at = AppTest.from_file("qa_spotlight_app.py", default_timeout=30).run()
    assert not at.exception
    assert [item.label for item in at.button] == ["Explore this decision"]
    official = deepcopy(at.session_state["daily_answers"])

    button(at, "Explore this decision").click().run()
    assert not at.exception and button(at, "Close spotlight")
    assert not button(at, "Change one thing").disabled
    assert not at.get("button_group")

    button(at, "Change one thing").click().run()
    assert not at.exception
    dice = at.get("button_group")[0]
    assert len(dice.options) == 5 and len(set(dice.options)) == 5
    # The sample has duplicate 3s. Select both physical dice independently.
    dice.set_value([dice.options[1], dice.options[2]]).run()
    selected = at.get("button_group")[0]
    assert len(selected.value) == 2
    held_key = next(key for key in at.session_state.filtered_state if key.endswith("_held"))
    assert at.session_state[held_key] == [1, 2]

    button(at, "See what changes").click().run()
    at.run()  # Verify settled disabled/revealed state, not the click transient.
    assert not at.exception
    assert button(at, "Change one thing").disabled
    assert button(at, "See what changes").disabled
    assert len(at.table) == 1
    assert any(item.label == "Why this hold on the changed card?" for item in at.expander)
    visible = "\n".join(item.value for item in at.markdown)
    assert "The original best hold still works." in visible
    assert "Originally, keep 2, 3, 4, 5 led keep 3, 3 by 3.58 expected points." in visible
    assert "On the changed card, keep 2, 3, 4, 5 leads keep 3, 3 by 6.60." in visible
    assert at.session_state["daily_answers"] == official

    button(at, "Close spotlight").click().run()
    at.run()
    assert not at.exception
    assert not any(item.label == "Change one thing" for item in at.button)
    assert at.session_state["daily_answers"] == official
    print("PASS real Streamlit open/change/select-duplicate/reveal/close flow")
    print("PASS optional learning never mutates the official ten answers")


if __name__ == "__main__":
    main()
