#!/usr/bin/env python3
"""
prepare_assets.py - Simplified version for blog image sampling
Select representative image samples for UI grids and emit rsync file list.
"""

import argparse
import os
import re
import numpy as np
import pandas as pd


def to_tail(path: str) -> str:
    """Extract train/val/test relative path for rsync."""
    if not isinstance(path, str) or not path:
        return ""
    # Match train/val/test/... pattern
    m = re.search(r"(train|val|test)/.*$", path)
    return m.group(0) if m else os.path.basename(path)


def sample_per_category(df: pd.DataFrame, category_col: str, path_col: str, n_per_value: int, seed: int = 1337) -> list:
    """Sample up to n_per_value images for each unique value in category_col."""
    rng = np.random.default_rng(seed)
    sampled_paths = []
    
    for value in df[category_col].dropna().unique():
        subset = df[df[category_col] == value]
        n_to_sample = min(len(subset), n_per_value)  # Take all available if less than n_per_value
        
        if n_to_sample <= 0:
            continue
            
        if len(subset) <= n_per_value:
            paths = subset[path_col].tolist()
        else:
            sampled = subset.sample(n_per_value, random_state=seed)
            paths = sampled[path_col].tolist()
        sampled_paths.extend(paths)
    
    return sampled_paths


def main():
    # Fixed paths to the two data files
    METADATA_FILE = "static/susu_ERM_hypertag_stoic-energy-14_test_tsne_clip_metadata.csv"
    RESULTS_FILE = "static/results_persample_l3_valtest_clip_imagenet_w10.csv"
    
    ap = argparse.ArgumentParser(description="Prepare image list for blog grid display")
    ap.add_argument("--per-value", type=int, default=12, help="Images per category value")
    ap.add_argument("--output", default="image_list.txt", help="Output file for rsync")
    args = ap.parse_args()

    all_paths = []

    # Load metadata file for demographic/clinical categories
    print("Loading metadata for demographic categories...")
    meta_df = pd.read_csv(METADATA_FILE)
    
    # Categories from metadata file (using 'name' column for paths)
    meta_categories = {
        'frontal_lateral': 'frontal_lateral',
        'sex': 'sex', 
        'race': 'race',
        'Support Devices': 'Support Devices',
        'Lung Lesion': 'Lung Lesion',
        'Cardiomegaly': 'Cardiomegaly'
    }
    
    for cat_name, col_name in meta_categories.items():
        if col_name in meta_df.columns:
            print(f"Sampling {cat_name}...")
            # Clean the data - remove missing values
            clean_df = meta_df.dropna(subset=[col_name, 'name'])
            paths = sample_per_category(clean_df, col_name, 'name', args.per_value)
            all_paths.extend(paths)
            print(f"  -> {len(paths)} samples")

    # Load results file for discovered subgroups (CRITICAL: seed=0 only)
    print("Loading results for discovered subgroups...")
    results_df = pd.read_csv(RESULTS_FILE)
    # Filter for seed=0 AND split='test' only (to match t-SNE data)
    results_df = results_df[(results_df['seed'] == 0) & (results_df['split'] == 'test')]
    print(f"  Filtered to {len(results_df)} records with seed=0 AND split='test'")
    
    if 'discovered_subgroup_idx' in results_df.columns:
        print("Sampling discovered_subgroup_idx (seed=0, split=test)...")
        clean_df = results_df.dropna(subset=['discovered_subgroup_idx', 'name'])
        paths = sample_per_category(clean_df, 'discovered_subgroup_idx', 'name', args.per_value)
        all_paths.extend(paths)
        print(f"  -> {len(paths)} samples")

    # Convert to rsync-friendly relative paths and deduplicate
    rsync_paths = []
    for path in all_paths:
        tail = to_tail(path)
        if tail and tail not in rsync_paths:
            rsync_paths.append(tail)
    
    rsync_paths.sort()

    # Write output
    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    with open(args.output, "w") as f:
        for path in rsync_paths:
            f.write(f"{path}\n")

    print(f"\nWrote {len(rsync_paths)} unique image paths to {args.output}")
    print("Sample paths:")
    for i, path in enumerate(rsync_paths[:5]):
        print(f"  {path}")
    if len(rsync_paths) > 5:
        print("  ...")


if __name__ == "__main__":
    main()