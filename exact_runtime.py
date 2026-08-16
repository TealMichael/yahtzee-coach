from __future__ import annotations

"""Deployment-safe exact-policy runtime bridge for Yahtzee Coach.

The app intentionally imports only the long-lived exact_mode module itself here,
not newer helper names directly. This prevents a partially propagated deploy
from crashing at module import while preserving the fail-closed exact-only rule.
"""

import hashlib
from pathlib import Path

import exact_mode as exact_math

ExactPolicyTable = exact_math.ExactPolicyTable
EXPECTED_EXACT_POLICY_SHA256 = getattr(
    exact_math,
    "EXPECTED_EXACT_POLICY_SHA256",
    "cdb704537146aed438cf7f6b8f8a9d6ec9ac5e97d505bd50af1702bb5935b39b",
)


def verify_exact_policy_fingerprint(path, expected=EXPECTED_EXACT_POLICY_SHA256):
    """Verify the audited exact-policy artifact without depending on a new symbol."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != str(expected).lower():
        raise RuntimeError(
            "Exact policy integrity check failed. "
            f"Expected {expected}, got {actual}."
        )
    return actual


def build_exact_live_report_from_loader(policy_loader, **kwargs):
    """Build player-facing coaching from exact policy only, including mixed deploys."""
    native = getattr(exact_math, "build_exact_live_report_from_loader", None)
    if callable(native):
        return native(policy_loader, **kwargs)

    # Compatibility path for a stale exact_mode.py. This deliberately calls only
    # its established exact report builder and never the legacy heuristic router.
    try:
        policy = policy_loader()
    except Exception as exc:
        return "", {
            "source": "exact_unavailable",
            "available": False,
            "error": f"policy_load_error: {type(exc).__name__}: {exc}",
        }
    try:
        return exact_math.build_exact_report(policy, **kwargs)
    except Exception as exc:
        return "", {
            "source": "exact_unavailable",
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
