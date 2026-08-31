"""Run each standalone regression suite in isolation and retain complete logs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs", required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    logs = Path(args.logs).resolve()
    logs.mkdir(parents=True, exist_ok=True)
    suites = [path for path in sorted(root.glob("*_tests.py")) if path.name != Path(__file__).name]
    def run(path):
        started = perf_counter()
        try:
            result = subprocess.run([sys.executable, str(path)], cwd=root, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            output, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as exc:
            output, code = str(exc), 124
        (logs / (path.stem + ".log")).write_text(output)
        return {"suite": path.name, "returncode": code, "seconds": round(perf_counter()-started, 3)}
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(run, path) for path in suites]):
            result = future.result()
            results.append(result)
            print(("PASS" if result["returncode"] == 0 else "FAIL"), result["suite"], flush=True)
    report = {"passed": sum(r["returncode"] == 0 for r in results), "total": len(results),
              "results": sorted(results, key=lambda r: r["suite"])}
    (logs / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['passed']}/{report['total']} suites passed", flush=True)
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
