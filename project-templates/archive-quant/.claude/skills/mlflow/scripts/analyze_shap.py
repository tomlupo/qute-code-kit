"""
Generic SHAP feature importance and direction analysis.

Analyzes SHAP values from cached parquet features to understand:
1. Which features are most important
2. Feature effect direction (positive/negative)
3. Direction consistency across time

Works with any cached feature parquet files.

Usage:
    # Basic usage with cache file
    python analyze_shap.py --cache-file data/cache/features.parquet --transform perc

    # Single window (fastest)
    python analyze_shap.py --cache-file data/cache/features.parquet --single-window

    # Specify target column
    python analyze_shap.py --cache-file data/cache/features.parquet --target-col raw_return_12m
"""

import argparse
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import shap
import lightgbm as lgb
from sklearn.metrics import roc_auc_score


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Analyze SHAP feature importance and direction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--cache-file',
        type=str,
        required=True,
        help='Path to cached features parquet file',
    )

    parser.add_argument(
        '--transform',
        type=str,
        default='perc',
        help='Feature transform prefix to filter (e.g., perc, zscore, raw). Default: perc',
    )

    parser.add_argument(
        '--target-col',
        type=str,
        help='Column to use for creating target. Auto-detected if not specified.',
    )

    parser.add_argument(
        '--date-col',
        type=str,
        default='date',
        help='Date column name. Default: date',
    )

    parser.add_argument(
        '--single-window',
        action='store_true',
        help='Run single window analysis (fastest)',
    )

    parser.add_argument(
        '--train-start',
        type=str,
        default='2018-01-01',
        help='Training start date. Default: 2018-01-01',
    )

    parser.add_argument(
        '--test-start',
        type=str,
        default='2024-01-01',
        help='Test start date. Default: 2024-01-01',
    )

    parser.add_argument(
        '--quantile',
        type=float,
        default=0.75,
        help='Quantile threshold for binary target. Default: 0.75 (top 25%%)',
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file path',
    )

    return parser.parse_args()


def load_features(cache_file: str, transform: str) -> tuple[pd.DataFrame, list]:
    """Load features from cache file and filter by transform."""
    print(f"Loading features from: {cache_file}")
    df = pd.read_parquet(cache_file)

    # Filter to transform prefix
    prefix = f'{transform}_'
    feature_cols = [c for c in df.columns if c.startswith(prefix)]

    if not feature_cols:
        available = set(c.split('_')[0] for c in df.columns if '_' in c)
        raise ValueError(f"Transform '{transform}' not found. Available prefixes: {available}")

    print(f"  Found {len(feature_cols)} {transform} features")
    return df, feature_cols


def find_target_column(df: pd.DataFrame, target_col: str = None) -> str:
    """Find or validate target column."""
    if target_col and target_col in df.columns:
        return target_col

    # Auto-detect: look for raw return columns
    candidates = [
        'raw_total_return_12m',
        'raw_return_12m',
        'total_return_12m',
        'return_12m',
    ]

    for col in candidates:
        if col in df.columns:
            print(f"  Using target column: {col}")
            return col

    # Try any column with 'return' and '12' in name
    return_cols = [c for c in df.columns if 'return' in c.lower() and '12' in c]
    if return_cols:
        col = return_cols[0]
        print(f"  Using target column: {col}")
        return col

    raise ValueError(
        f"Could not find target column. Specify with --target-col. "
        f"Available columns: {[c for c in df.columns if 'return' in c.lower()]}"
    )


def create_binary_target(df: pd.DataFrame, target_col: str, date_col: str, quantile: float) -> pd.Series:
    """Create binary target: top quantile within each date = 1."""
    df = df.dropna(subset=[target_col])
    target = df.groupby(date_col)[target_col].transform(
        lambda x: (x >= x.quantile(quantile)).astype(int)
    )
    return target


def analyze_shap(
    df: pd.DataFrame,
    feature_cols: list,
    date_col: str,
    train_start: str,
    test_start: str,
) -> pd.DataFrame:
    """Run SHAP analysis and return results."""

    # Prepare data
    X = df[feature_cols]
    y = df['target']
    dates = df[date_col]

    train_mask = (dates >= train_start) & (dates < test_start)
    test_mask = dates >= test_start

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    print(f"  Train: {len(X_train):,}, Test: {len(X_test):,}")

    if len(X_train) < 100 or len(X_test) < 50:
        raise ValueError("Insufficient data for analysis")

    # Train model
    print("  Training LightGBM model...")
    model = lgb.LGBMClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.05,
        num_leaves=31, random_state=42, verbose=-1
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    print(f"  Test AUC: {auc:.4f}")

    # Compute SHAP values
    print("  Computing SHAP values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    # For binary classification
    if isinstance(shap_values, list):
        shap_vals = shap_values[1]
    else:
        shap_vals = shap_values

    mean_shap = np.mean(shap_vals, axis=0)
    abs_shap = np.mean(np.abs(shap_vals), axis=0)

    # Create results
    results = pd.DataFrame({
        'feature': feature_cols,
        'mean_shap': mean_shap,
        'abs_shap': abs_shap,
        'auc': auc,
    })

    results['direction'] = results['mean_shap'].apply(
        lambda x: 'POSITIVE' if x > 0.005 else ('NEGATIVE' if x < -0.005 else 'MIXED')
    )

    return results.sort_values('abs_shap', ascending=False)


def print_results(results: pd.DataFrame):
    """Print formatted results."""
    print()
    print("=" * 80)
    print("SHAP FEATURE IMPORTANCE WITH DIRECTION")
    print("=" * 80)

    auc = results['auc'].iloc[0]
    print(f"Model: LightGBM | Test AUC: {auc:.4f}")
    print()
    print(f"{'#':<3} {'Feature':<40} {'Importance':>10} {'Direction':>10} {'Mean SHAP':>12}")
    print("-" * 77)

    for i, (_, row) in enumerate(results.iterrows(), 1):
        print(f"{i:<3} {row['feature']:<40} {row['abs_shap']:>10.4f} {row['direction']:>10} {row['mean_shap']:>+12.4f}")

    # Summary
    pos_count = (results['direction'] == 'POSITIVE').sum()
    neg_count = (results['direction'] == 'NEGATIVE').sum()
    mixed_count = (results['direction'] == 'MIXED').sum()

    print()
    print("=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print()
    print("DIRECTION KEY:")
    print("  POSITIVE: Higher feature value -> higher probability of target=1")
    print("  NEGATIVE: Higher feature value -> LOWER probability of target=1")
    print("  MIXED:    Effect varies across samples")
    print()
    print(f"Direction summary: POSITIVE={pos_count}, NEGATIVE={neg_count}, MIXED={mixed_count}")

    # Top features by direction
    print()
    print("KEY FEATURES:")

    neg_features = results[results['direction'] == 'NEGATIVE'].head(3)
    if len(neg_features) > 0:
        print("\nNEGATIVE direction (higher value = lower target probability):")
        for _, row in neg_features.iterrows():
            print(f"  - {row['feature']}: importance={row['abs_shap']:.4f}")

    pos_features = results[results['direction'] == 'POSITIVE'].head(3)
    if len(pos_features) > 0:
        print("\nPOSITIVE direction (higher value = higher target probability):")
        for _, row in pos_features.iterrows():
            print(f"  - {row['feature']}: importance={row['abs_shap']:.4f}")


def main():
    """Main entry point."""
    args = parse_args()

    print("=" * 80)
    print("SHAP FEATURE DIRECTION ANALYSIS")
    print("=" * 80)

    # Load features
    df, feature_cols = load_features(args.cache_file, args.transform)

    # Find target column
    target_col = find_target_column(df, args.target_col)

    # Create binary target
    print(f"\nCreating target (top {int(args.quantile*100)}% within each {args.date_col})...")
    df['target'] = create_binary_target(df, target_col, args.date_col, args.quantile)
    df = df.dropna(subset=['target'] + feature_cols)

    # Filter date range
    df = df[df[args.date_col] >= args.train_start]
    print(f"  Filtered to {len(df):,} rows from {args.train_start}")

    # Run analysis
    print("\nRunning SHAP analysis...")
    results = analyze_shap(
        df, feature_cols, args.date_col,
        args.train_start, args.test_start
    )

    # Print results
    print_results(results)

    # Save if output specified
    if args.output:
        results.to_csv(args.output, index=False)
        print(f"\nResults saved to: {args.output}")

    return results


if __name__ == '__main__':
    main()
