#!/usr/bin/env python3
"""
prepare_assets_representative.py - Representative sampling for all categories
Samples images for both discovered subgroups AND demographic/metadata categories
"""

import os
import csv
import random
from collections import defaultdict


def to_tail(path: str) -> str:
    """Extract train/val/test relative path."""
    if not isinstance(path, str) or not path:
        return ""
    # Find train/val/test part
    parts = path.split('/')
    for i, part in enumerate(parts):
        if part in ['train', 'val', 'test']:
            return '/'.join(parts[i:])
    return os.path.basename(path)


def sample_from_category(data_rows, category_col: str, path_col: str, n_per_value: int, seed: int = 1337):
    """Sample images for ONE specific category, ensuring good representation."""
    random.seed(seed)
    sampled_paths = []
    
    print(f"  Sampling for category: {category_col}")
    
    # Group by category values
    category_groups = defaultdict(list)
    for row in data_rows:
        if row.get(category_col) and row.get(path_col):
            value = str(row[category_col]).strip()
            if value and value.lower() not in ['', 'nan', 'none']:
                category_groups[value].append(row[path_col])
    
    for value in sorted(category_groups.keys()):
        samples = category_groups[value]
        n_available = len(samples)
        n_to_sample = min(n_available, n_per_value)
        
        if n_to_sample == 0:
            continue
            
        if n_available <= n_per_value:
            # Take all available
            sampled = samples
        else:
            # Random sample
            sampled = random.sample(samples, n_per_value)
        
        sampled_paths.extend(sampled)
        print(f"    {value}: {len(sampled)} samples (from {n_available} available)")
    
    return sampled_paths


def main():
    # File paths
    METADATA_FILE = "static/susu_ERM_hypertag_stoic-energy-14_test_tsne_clip_metadata.csv"
    RESULTS_FILE = "static/results_persample_l3_valtest_clip_imagenet_w10.csv"
    
    print("=== REPRESENTATIVE IMAGE SAMPLING FOR ALL CATEGORIES ===")
    
    all_paths = set()  # Use set to avoid duplicates across categories
    per_value = 12
    
    # 1. Sample from metadata/demographic categories
    print(f"\n📊 Loading metadata file: {METADATA_FILE}")
    metadata_rows = []
    with open(METADATA_FILE, 'r') as f:
        reader = csv.DictReader(f)
        metadata_rows = list(reader)
    
    print(f"Loaded {len(metadata_rows)} metadata records")
    
    # Add frontal/lateral derived column
    for row in metadata_rows:
        if 'frontal_lateral' not in row or not row['frontal_lateral']:
            # Derive from path
            path = row.get('name', '')
            if 'lateral' in str(path).lower():
                row['frontal_lateral'] = 'Lateral'
            else:
                row['frontal_lateral'] = 'Frontal'
    
    # Sample from demographic/clinical categories
    metadata_categories = [
        'frontal_lateral',
        'sex', 
        'race',
        'Support Devices',
        'Lung Lesion',
        'Cardiomegaly'
    ]
    
    for category in metadata_categories:
        # Check if column exists
        if any(row.get(category) for row in metadata_rows):
            print(f"\n📊 {category}:")
            paths = sample_from_category(metadata_rows, category, 'name', per_value)
            all_paths.update(paths)
        else:
            print(f"\n⚠️  Category '{category}' not found in metadata")
    
    # 2. Sample from discovered subgroups (ONLY seed=0 rows)
    print(f"\n📊 Loading discovered subgroups: {RESULTS_FILE}")
    all_results_rows = []
    with open(RESULTS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        all_results_rows = list(reader)
    
    # Filter for seed=0 AND split='test' only (to match t-SNE data)
    results_rows = [row for row in all_results_rows 
                   if row.get('seed') == '0' and row.get('split') == 'test']
    
    print(f"Loaded {len(all_results_rows)} total results records")
    print(f"Filtered to {len(results_rows)} records with seed=0 AND split='test'")
    
    if any(row.get('discovered_subgroup_idx') for row in results_rows):
        print(f"\n📊 discovered_subgroup_idx (seed=0, split=test):")
        paths = sample_from_category(results_rows, 'discovered_subgroup_idx', 'name', per_value)
        all_paths.update(paths)
    else:
        print("\n⚠️  No discovered subgroups found with seed=0")
    
    # Convert to rsync-friendly relative paths
    rsync_paths = []
    for path in all_paths:
        tail = to_tail(path)
        if tail:
            rsync_paths.append(tail)
    
    # Remove duplicates and sort
    rsync_paths = sorted(list(set(rsync_paths)))
    
    # Write output
    output_file = "static/image_list_representative.txt"
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    
    with open(output_file, "w") as f:
        for path in rsync_paths:
            f.write(f"{path}\n")
    
    print(f"\n✅ SUMMARY:")
    print(f"Wrote {len(rsync_paths)} unique image paths to {output_file}")
    print(f"This ensures representative sampling across all categories.")
    
    # Verify discovered subgroups specifically (seed=0, split=test only)
    print(f"\nVerification - discovered subgroup counts (seed=0, split=test):")
    path_to_subgroup = {}
    with open(RESULTS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get('seed') == '0' and row.get('split') == 'test' and 
                row.get('discovered_subgroup_idx') and row.get('name')):
                tail = to_tail(row['name'])
                if tail:
                    path_to_subgroup[tail] = row['discovered_subgroup_idx']
    
    final_counts = defaultdict(int)
    for path in rsync_paths:
        if path in path_to_subgroup:
            sg = path_to_subgroup[path]
            final_counts[sg] += 1
    
    if final_counts:
        for sg in sorted(final_counts.keys(), key=int):
            print(f"  Subgroup {sg}: {final_counts[sg]} images")
    else:
        print("  No discovered subgroup images found in final list")


if __name__ == "__main__":
    main()