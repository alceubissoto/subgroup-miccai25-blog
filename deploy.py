#!/usr/bin/env python3
"""
Deployment helper script for the Subgroup Performance Analysis app
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        'streamlit_native.py',
        'requirements_native.txt',
        'static/susu_ERM_hypertag_stoic-energy-14_test_tsne_clip_metadata.csv',
        'static/results_persample_l3_valtest_clip_imagenet_w10.csv'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required files present")
    return True

def check_data():
    """Check if data files are properly formatted"""
    try:
        import pandas as pd
        
        # Check metadata file
        metadata_file = 'static/susu_ERM_hypertag_stoic-energy-14_test_tsne_clip_metadata.csv'
        df_meta = pd.read_csv(metadata_file)
        print(f"✅ Metadata file: {len(df_meta)} rows, {len(df_meta.columns)} columns")
        
        # Check results file
        results_file = 'static/results_persample_l3_valtest_clip_imagenet_w10.csv'
        df_results = pd.read_csv(results_file)
        print(f"✅ Results file: {len(df_results)} rows, {len(df_results.columns)} columns")
        
        return True
    except Exception as e:
        print(f"❌ Error reading data files: {e}")
        return False

def test_local():
    """Test the app locally"""
    print("🧪 Testing app locally...")
    try:
        result = subprocess.run([
            sys.executable, '-c', 
            'import streamlit_native; print("✅ App imports successfully")'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ App loads successfully")
            return True
        else:
            print(f"❌ App failed to load: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing app: {e}")
        return False

def show_deployment_options():
    """Show deployment options"""
    print("\n🚀 Deployment Options:")
    print("1. Streamlit Cloud (Recommended)")
    print("   - Go to https://share.streamlit.io")
    print("   - Connect your GitHub repo")
    print("   - Set main file: streamlit_native.py")
    print("   - Deploy!")
    
    print("\n2. Railway")
    print("   - Connect GitHub repo to Railway")
    print("   - Set start command: streamlit run streamlit_native.py --server.port=$PORT --server.address=0.0.0.0")
    
    print("\n3. Render")
    print("   - Connect GitHub repo")
    print("   - Build command: pip install -r requirements_native.txt")
    print("   - Start command: streamlit run streamlit_native.py --server.port=$PORT --server.address=0.0.0.0")
    
    print("\n4. Heroku")
    print("   - Use Procfile (already created)")
    print("   - Runtime: python-3.11.0 (runtime.txt already created)")

def main():
    print("🔧 Deployment Preparation for Subgroup Performance Analysis")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check data
    if not check_data():
        sys.exit(1)
    
    # Test locally
    if not test_local():
        print("⚠️  App has issues but deployment files are ready")
    
    print("\n✅ Deployment preparation complete!")
    show_deployment_options()
    
    print(f"\n📁 Current directory: {os.getcwd()}")
    print("📋 Files ready for deployment:")
    print("   - streamlit_native.py (main app)")
    print("   - requirements_native.txt (dependencies)")
    print("   - Procfile (for Heroku)")
    print("   - runtime.txt (Python version)")
    print("   - .streamlit/config.toml (Streamlit config)")
    print("   - static/ (data directory)")

if __name__ == "__main__":
    main()