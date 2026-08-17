from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def require(text: str, message: str):
    if text not in APP:
        raise AssertionError(message)


def between(start: str, end: str) -> str:
    left = APP.index(start)
    right = APP.index(end, left)
    return APP[left:right]


def main():
    tests = []

    require('APP_RELEASE = "v43B Phase 2K.8"', "release label should advance while preserving the autofill fix")
    tests.append("release label")

    returning = between('with return_tab:', 'with create_tab:')
    if 'key="returning_player_name",\n                autocomplete="username",' not in returning:
        raise AssertionError("returning display name should identify itself as username")
    tests.append("returning username autocomplete")
    if 'key="returning_player_pin",\n                autocomplete="current-password",' not in returning:
        raise AssertionError("returning PIN must use current-password, not Streamlit's new-password default")
    tests.append("returning PIN current-password")
    if 'autocomplete="new-password"' in returning:
        raise AssertionError("returning-player form must not advertise a new-password field")
    tests.append("no new-password in returning form")

    creating = between('with create_tab:', 'def render_player_status')
    if 'key="create_player_name",\n                autocomplete="username",' not in creating:
        raise AssertionError("create-player display name should identify itself as username")
    tests.append("create username autocomplete")
    if 'key="create_player_pin",\n                autocomplete="new-password",' not in creating:
        raise AssertionError("new PIN should remain semantically marked as a new password")
    tests.append("new PIN autocomplete")
    if 'key="create_player_pin_confirm",\n                autocomplete="new-password",' not in creating:
        raise AssertionError("confirm PIN should remain semantically marked as a new password")
    tests.append("confirm PIN autocomplete")

    # Persistent-login implementation must remain present.
    require('Keep me signed in on this device for 30 days', "remember-device UI must remain")
    require('_remember_storage_component', "browser remembered-login bridge must remain")
    require('create_device_session', "server-side device session creation must remain")
    tests.extend(["remember UI preserved", "browser bridge preserved", "device session preserved"])

    print(f"PASS: {len(tests)}/{len(tests)} login-autofill hotfix checks")
    for test in tests:
        print(f" - {test}")


if __name__ == "__main__":
    main()
