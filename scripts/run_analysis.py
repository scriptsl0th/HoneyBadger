"""Re-run the analysis notebooks and check their results against the reference values.

Usage (from the repository root):
    pip install -r requirements-analysis.txt
    python scripts/run_analysis.py              # run Pair 1, 2 and 3, then check
    python scripts/run_analysis.py --check-only # only compare the saved results/*.json files

The notebooks live in notebooks/ and run from that folder. Train_data.csv and
Test_data.csv should sit in data/. If they are missing, each notebook tries to download them from Kaggle and verifies their
SHA-256 checksums.

Each notebook saves its settings and measured results to results/<pair>_results.json
and its test-file predictions to results/predictions/.
This script compares the key numbers with scripts/expected_results.json. Rates must
match within 0.002 and counts exactly. Exit code 0 means every check passed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = Path(__file__).resolve().parent / "expected_results.json"
NOTEBOOKS = {
    "pair1": ("notebooks/pair1_attack_classification.ipynb", "results/pair1_results.json"),
    "pair2": ("notebooks/pair2_anomaly_detection.ipynb", "results/pair2_results.json"),
    "pair3": ("notebooks/pair3_attack_profiling.ipynb", "results/pair3_results.json"),
}
RATE_TOLERANCE = 0.002


def execute(notebook: Path, timeout: int, kernel: str) -> float:
    import nbformat
    from nbclient import NotebookClient

    nb = nbformat.read(notebook, as_version=4)
    start = time.time()
    NotebookClient(nb, timeout=timeout, kernel_name=kernel,
                   resources={"metadata": {"path": str(notebook.parent)}}).execute()
    nbformat.write(nb, notebook)  # keep the fresh outputs in the notebook
    return time.time() - start


def lookup(record: dict, dotted: str):
    value = record
    for part in dotted.split("|"):
        value = value[part]
    return value


def compare(pair: str, record: dict, expected: dict) -> list[tuple[str, object, object, bool]]:
    rows = []
    for key, want in expected.items():
        try:
            got = lookup(record, key)
        except (KeyError, TypeError):
            rows.append((key, want, "missing", False))
            continue
        if isinstance(want, float):
            ok = isinstance(got, (int, float)) and abs(got - want) <= RATE_TOLERANCE
        else:
            ok = got == want
        rows.append((key, want, got, ok))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check-only", action="store_true", help="do not execute the notebooks")
    parser.add_argument("--only", choices=sorted(NOTEBOOKS), help="run a single notebook")
    parser.add_argument("--timeout", type=int, default=900, help="seconds allowed per notebook cell")
    parser.add_argument("--kernel", default="python3", help="Jupyter kernel to run the notebooks with")
    args = parser.parse_args(argv)

    expected_all = json.loads(EXPECTED.read_text())
    failures = 0
    for pair, (notebook, result_file) in NOTEBOOKS.items():
        if args.only and pair != args.only:
            continue
        if not (ROOT / notebook).exists():
            print(f"{pair}: {notebook} is not in this checkout yet, skipped")
            continue
        if not args.check_only:
            print(f"Running {notebook} ...", flush=True)
            try:
                seconds = execute(ROOT / notebook, args.timeout, args.kernel)
            except Exception as error:  # report and keep going with the next notebook
                print(f"  FAILED to run: {type(error).__name__}: {str(error).splitlines()[0] if str(error) else ''}")
                failures += 1
                continue
            print(f"  finished in {seconds:.0f} s")
        path = ROOT / result_file
        if not path.exists():
            print(f"  {result_file} not found: run the notebook first")
            failures += 1
            continue
        record = json.loads(path.read_text())
        rows = compare(pair, record, expected_all[pair])
        print(f"{pair}: {sum(ok for *_, ok in rows)}/{len(rows)} checks passed "
              f"(scikit-learn {record['environment']['scikit-learn']}, pandas {record['environment']['pandas']})")
        for key, want, got, ok in rows:
            if not ok:
                print(f"  MISMATCH {key}: expected {want}, got {got}")
        failures += sum(not ok for *_, ok in rows)
    print("All checks passed." if failures == 0 else f"{failures} problem(s) found.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
