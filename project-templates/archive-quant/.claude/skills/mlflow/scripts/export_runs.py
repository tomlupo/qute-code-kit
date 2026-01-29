#!/usr/bin/env python3
"""Export MLflow experiment runs to CSV or Parquet for analysis.

Usage:
    python export_runs.py experiment_name output.csv
    python export_runs.py experiment_name output.parquet
    python export_runs.py experiment_name output.parquet --tracking-uri mlruns
    python export_runs.py --all output.parquet  # Export all experiments
"""

import argparse
from pathlib import Path

import mlflow
import pandas as pd


def export_runs(
    experiment_name: str | None = None,
    output_path: str = "mlflow_export.parquet",
    tracking_uri: str = "mlruns",
    export_all: bool = False,
) -> pd.DataFrame:
    """Export MLflow runs to file.

    Args:
        experiment_name: Name of experiment to export (None if export_all=True)
        output_path: Output file path (.csv or .parquet)
        tracking_uri: MLflow tracking URI
        export_all: If True, export all experiments

    Returns:
        DataFrame with exported runs
    """
    mlflow.set_tracking_uri(tracking_uri)

    if export_all:
        # Get all experiments
        experiments = mlflow.search_experiments()
        experiment_names = [e.name for e in experiments if e.name != "Default"]
        if not experiment_names:
            print("No experiments found")
            return pd.DataFrame()
        df = mlflow.search_runs(experiment_names=experiment_names)
    else:
        if experiment_name is None:
            raise ValueError("experiment_name required when export_all=False")
        df = mlflow.search_runs(experiment_names=[experiment_name])

    if df.empty:
        print(f"No runs found")
        return df

    # Clean up column names for easier analysis
    df.columns = [col.replace("params.", "p_").replace("metrics.", "m_").replace("tags.", "t_")
                  for col in df.columns]

    # Export
    output_path = Path(output_path)
    if output_path.suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    elif output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {output_path.suffix}")

    print(f"Exported {len(df)} runs to {output_path}")
    return df


def main():
    parser = argparse.ArgumentParser(description="Export MLflow runs")
    parser.add_argument("experiment", nargs="?", help="Experiment name")
    parser.add_argument("output", help="Output file (.csv or .parquet)")
    parser.add_argument("--tracking-uri", default="mlruns", help="MLflow tracking URI")
    parser.add_argument("--all", action="store_true", help="Export all experiments")

    args = parser.parse_args()

    if not args.all and not args.experiment:
        parser.error("Either experiment name or --all is required")

    export_runs(
        experiment_name=args.experiment,
        output_path=args.output,
        tracking_uri=args.tracking_uri,
        export_all=args.all,
    )


if __name__ == "__main__":
    main()
