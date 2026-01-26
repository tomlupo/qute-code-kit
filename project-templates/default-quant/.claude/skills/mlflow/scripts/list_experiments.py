#!/usr/bin/env python3
"""
List MLflow experiments with run counts and timestamps.

Usage:
    python list_experiments.py
    python list_experiments.py --pattern "fund_ratings/*"
    python list_experiments.py --with-runs --sort runs
    python list_experiments.py --json
"""

import argparse
import fnmatch
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml


def list_experiments(
    mlruns_dir: Path,
    pattern: str | None = None,
    with_runs_only: bool = False,
    sort_by: str = "name",
) -> list[dict]:
    """List all MLflow experiments with metadata."""
    results = []

    for exp_dir in mlruns_dir.iterdir():
        if not exp_dir.is_dir():
            continue
        if exp_dir.name.startswith(".") or exp_dir.name == "models":
            continue

        meta_file = exp_dir / "meta.yaml"
        if not meta_file.exists():
            continue

        with open(meta_file) as f:
            meta = yaml.safe_load(f)

        name = meta.get("name", "Unknown")

        if pattern and not fnmatch.fnmatch(name, pattern):
            continue

        runs = [
            d for d in exp_dir.iterdir()
            if d.is_dir() and (d / "meta.yaml").exists()
        ]

        run_times = []
        for run_dir in runs:
            run_meta = run_dir / "meta.yaml"
            if run_meta.exists():
                with open(run_meta) as f:
                    rm = yaml.safe_load(f)
                    if rm and "start_time" in rm:
                        run_times.append(rm["start_time"])

        if with_runs_only and not runs:
            continue

        if run_times:
            oldest_ts = min(run_times)
            newest_ts = max(run_times)
            oldest = datetime.fromtimestamp(oldest_ts / 1000)
            newest = datetime.fromtimestamp(newest_ts / 1000)
        else:
            oldest = newest = None
            oldest_ts = newest_ts = 0

        results.append({
            "name": name,
            "experiment_id": exp_dir.name,
            "runs": len(runs),
            "oldest": oldest,
            "newest": newest,
            "oldest_ts": oldest_ts,
            "newest_ts": newest_ts,
        })

    # Sort
    sort_keys = {
        "name": lambda x: x["name"].lower(),
        "runs": lambda x: (-x["runs"], x["name"].lower()),
        "oldest": lambda x: (x["oldest_ts"] or 0, x["name"].lower()),
        "newest": lambda x: (-x["newest_ts"], x["name"].lower()),
    }
    results.sort(key=sort_keys.get(sort_by, sort_keys["name"]))

    return results


def format_table(experiments: list[dict]) -> str:
    """Format as ASCII table."""
    if not experiments:
        return "No experiments found."

    lines = []
    header = f"{'Experiment':<55} {'Runs':>5} {'Oldest':>17} {'Newest':>17}"
    lines.append(header)
    lines.append("-" * len(header))

    total_runs = 0
    for exp in experiments:
        oldest_str = exp["oldest"].strftime("%Y-%m-%d %H:%M") if exp["oldest"] else "-"
        newest_str = exp["newest"].strftime("%Y-%m-%d %H:%M") if exp["newest"] else "-"
        lines.append(f"{exp['name']:<55} {exp['runs']:>5} {oldest_str:>17} {newest_str:>17}")
        total_runs += exp["runs"]

    lines.append("-" * len(header))
    lines.append(f"Total: {len(experiments)} experiments, {total_runs} runs")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="List MLflow experiments")
    parser.add_argument("--mlruns", type=Path, default=Path("mlruns"))
    parser.add_argument("--pattern", type=str, default=None)
    parser.add_argument("--with-runs", action="store_true")
    parser.add_argument("--sort", choices=["name", "runs", "oldest", "newest"], default="name")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if not args.mlruns.exists():
        print(f"Error: {args.mlruns} not found", file=sys.stderr)
        sys.exit(1)

    experiments = list_experiments(args.mlruns, args.pattern, args.with_runs, args.sort)

    if args.json:
        output = [{
            "name": e["name"],
            "experiment_id": e["experiment_id"],
            "runs": e["runs"],
            "oldest": e["oldest"].isoformat() if e["oldest"] else None,
            "newest": e["newest"].isoformat() if e["newest"] else None,
        } for e in experiments]
        print(json.dumps(output, indent=2))
    else:
        print(format_table(experiments))


if __name__ == "__main__":
    main()
