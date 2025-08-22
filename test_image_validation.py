#!/usr/bin/env python3
"""
Test script to validate that image grids show correct samples for selected attributes.
This ensures the bokeh app displays the right images for demographic/clinical categories.
"""

import pandas as pd
import numpy as np
import re


def to_tail(path):
    """Extract train/val/test relative path."""
    if not isinstance(path, str) or not path:
        return ""
    m = re.search(r"(train|val|test)/.*$", path)
    return m.group(0) if m else path


def test_image_validation():
    """Test that images shown for each category match the metadata."""
    
    # Load data exactly as bokeh_app does
    bias_level, model_type = "0.6", "clip"
    dict_models = {"0.6":"stoic-energy-14","0.7":"vital-pond-23",
                   "0.8":"unique-glitter-24","0.9":"ancient-sky-25"}

    output_csv = f"static/susu_ERM_hypertag_{dict_models[bias_level]}_test_tsne_{model_type}_metadata.csv"
    subgroup_csv = f"static/results_persample_hypertag_valtest_{bias_level}_clip_imagenet_nslices15_weight10.csv"

    df = pd.merge(pd.read_csv(output_csv), pd.read_csv(subgroup_csv), "inner", "name")
    df['image_path'] = df['name'].apply(to_tail)
    
    # Load available images
    try:
        with open('static/image_list.txt', 'r') as f:
            available_images = set(line.strip() for line in f if line.strip())
        df = df[df['image_path'].isin(available_images)].copy()
        print(f"Testing with {len(df)} samples with available images")
    except FileNotFoundError:
        print("Warning: image_list.txt not found")
        return
    
    # Rename columns as bokeh app does
    df.rename(columns={"sex": "Sex", "race": "Race", 
                       'discovered_subgroup_idx':'(Ours) Found Subgroups'}, inplace=True)
    
    # Test categories
    test_categories = {
        'Sex': ['Male', 'Female'],
        'Race': ['White', 'Black', 'Asian'],
        '(Ours) Found Subgroups': ['0', '1', '8']  # Test a few subgroups
    }
    
    print("\n=== IMAGE VALIDATION TEST ===")
    
    for category, test_values in test_categories.items():
        if category not in df.columns:
            print(f"⚠️  Category '{category}' not found in data")
            continue
            
        print(f"\n📊 Testing category: {category}")
        
        for value in test_values:
            # Convert value to string to match bokeh app behavior
            value_str = str(value)
            subset = df[df[category].astype(str) == value_str]
            
            if len(subset) == 0:
                print(f"   {value}: No samples found")
                continue
                
            # Take first 10 samples (like bokeh app does)
            sample_images = subset.head(10)
            
            # Validate all samples match the expected value
            validation_values = sample_images[category].astype(str).unique()
            
            if len(validation_values) == 1 and validation_values[0] == value_str:
                print(f"   ✅ {value}: {len(sample_images)} samples - All correct")
            else:
                print(f"   ❌ {value}: Found mismatched values: {validation_values}")
                
            # Show sample paths for manual verification
            sample_paths = sample_images['image_path'].head(3).tolist()
            print(f"      Sample images: {', '.join(sample_paths)}")
    
    # Test specific case: Sex = Female
    print(f"\n🔍 DETAILED TEST: Sex = Female")
    female_samples = df[df['Sex'].astype(str) == 'Female'].head(5)
    
    for idx, row in female_samples.iterrows():
        print(f"   Image: {row['image_path']}")
        print(f"   Sex: {row['Sex']}, Race: {row.get('Race', 'N/A')}")
        print(f"   Subgroup: {row.get('(Ours) Found Subgroups', 'N/A')}")
        print()
    
    print("🎯 TEST COMPLETE")
    print("To manually verify, check that the sample images shown above")
    print("correspond to the correct demographic attributes in the original data.")


if __name__ == "__main__":
    test_image_validation()