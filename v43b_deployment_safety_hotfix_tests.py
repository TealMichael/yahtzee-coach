from pathlib import Path

import exact_runtime as runtime

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "exact_policy.npz"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


checks = 0

def check(condition, message):
    global checks
    require(condition, message)
    checks += 1


app = (ROOT / "app.py").read_text(encoding="utf-8")
bridge = (ROOT / "exact_runtime.py").read_text(encoding="utf-8")

check('APP_RELEASE = "v43B Phase 2K.6.1.1"' in app, "release label updated")
check("from exact_runtime import" in app, "app uses deployment-safe exact bridge")
check("from exact_mode import (" not in app, "app does not directly import new exact_mode helper names")
check("legacy heuristic" in bridge, "bridge documents exact-only behavior")
check("build_live_report_with_fallback" not in bridge, "bridge never invokes heuristic fallback router")
check(runtime.verify_exact_policy_fingerprint(POLICY) == runtime.EXPECTED_EXACT_POLICY_SHA256, "policy fingerprint remains locked")

# Simulate a mixed deploy where the newer helper is missing from exact_mode.py.
original_native = getattr(runtime.exact_math, "build_exact_live_report_from_loader", None)
original_builder = runtime.exact_math.build_exact_report
try:
    runtime.exact_math.build_exact_live_report_from_loader = None
    runtime.exact_math.build_exact_report = lambda policy, **kwargs: (
        "EXACT ONLY",
        {"source": "exact", "available": True},
    )
    report, meta = runtime.build_exact_live_report_from_loader(
        lambda: object(), dice=(1, 2, 3, 4, 5), scorecard={}, user_hold=(1,), roll_number=1
    )
    check(report == "EXACT ONLY", "stale-module compatibility still uses exact report builder")
    check(meta.get("source") == "exact", "stale-module compatibility remains exact-sourced")
finally:
    if original_native is not None:
        runtime.exact_math.build_exact_live_report_from_loader = original_native
    else:
        try:
            delattr(runtime.exact_math, "build_exact_live_report_from_loader")
        except AttributeError:
            pass
    runtime.exact_math.build_exact_report = original_builder

# A policy load failure must fail closed rather than return heuristic coaching.
report, meta = runtime.build_exact_live_report_from_loader(
    lambda: (_ for _ in ()).throw(RuntimeError("missing policy")),
    dice=(1, 2, 3, 4, 5), scorecard={}, user_hold=(1,), roll_number=1,
)
check(report == "", "policy load failure produces no coaching report")
check(meta.get("source") == "exact_unavailable", "policy load failure is explicitly exact-unavailable")
check(meta.get("available") is False, "policy load failure is unavailable")

print(f"PASS: {checks}/{checks} deployment-safety hotfix checks")
