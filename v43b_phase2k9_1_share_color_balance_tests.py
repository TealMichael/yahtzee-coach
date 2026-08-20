from __future__ import annotations

"""Phase 2K.9.1 spoiler-free share color balance regression."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_share_square():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_share_square"
    )
    module = ast.Module(body=[fn], type_ignores=[])
    namespace = {}
    exec(compile(module, str(ROOT / "app.py"), "exec"), namespace)
    return namespace["_share_square"]


def main():
    square = _load_share_square()

    checks = [
        (0.00, "🟩"),
        (0.0000000001, "🟩"),
        (0.01, "🟨"),
        (0.10, "🟨"),
        (0.14, "🟨"),
        (0.25, "🟨"),
        (0.2501, "🟧"),
        (0.75, "🟧"),
        (1.00, "🟧"),
        (1.50, "🟧"),
        (1.5001, "🟥"),
        (4.00, "🟥"),
    ]

    failed = []
    for loss, expected in checks:
        actual = square(loss)
        ok = actual == expected
        print(("PASS" if ok else "FAIL"), f"{loss:.4f} -> {actual} (expected {expected})")
        if not ok:
            failed.append((loss, expected, actual))

    # The real-world case that exposed the imbalance: two old-orange tiny misses
    # totaling 0.39 should no longer automatically produce two orange squares.
    sample = [0.14, 0.25]
    sample_squares = [square(v) for v in sample]
    ok = sample_squares == ["🟨", "🟨"]
    print(("PASS" if ok else "FAIL"), f"0.14 + 0.25 sample -> {sample_squares}")
    if not ok:
        failed.append(("sample", ["🟨", "🟨"], sample_squares))

    if failed:
        raise SystemExit(f"{len(failed)} failed: {failed}")
    print("ALL PHASE 2K.9.1 SHARE COLOR BALANCE TESTS PASSED")


if __name__ == "__main__":
    main()
