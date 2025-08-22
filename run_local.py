#!/usr/bin/env python3
"""
Local development runner for different versions
Usage:
    python run_local.py native      # Run native Streamlit version (RECOMMENDED)
    python run_local.py streamlit   # Run Bokeh-based Streamlit version  
    python run_local.py flask       # Run Flask version
"""

import sys
import subprocess
import os

def run_flask():
    """Run the Flask version locally"""
    print("🚀 Starting Flask development server...")
    os.environ['FLASK_ENV'] = 'development'
    
    try:
        import app
        app.app.run(host="localhost", port=9000, debug=True)
    except ImportError:
        print("❌ Flask dependencies not installed. Run: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error running Flask app: {e}")

def run_streamlit():
    """Run the Bokeh-based Streamlit version locally"""
    print("🚀 Starting Bokeh-based Streamlit server...")
    print("⚠️  Note: This version has Bokeh compatibility issues. Use 'native' instead.")
    
    try:
        result = subprocess.run([
            "streamlit", "run", "streamlit_app.py", 
            "--server.port=8501",
            "--server.address=localhost"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        print("💡 Try: pip install -r requirements_streamlit.txt")
    except FileNotFoundError:
        print("❌ Streamlit not found. Install with: pip install streamlit")

def run_native():
    """Run the native Streamlit version (recommended)"""
    print("🚀 Starting native Streamlit server (RECOMMENDED)...")
    
    try:
        result = subprocess.run([
            "streamlit", "run", "streamlit_native.py", 
            "--server.port=8501",
            "--server.address=localhost"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running native Streamlit: {e}")
        print("💡 Try: pip install -r requirements_native.txt")
    except FileNotFoundError:
        print("❌ Streamlit not found. Install with: pip install streamlit")

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_local.py [native|streamlit|flask]")
        print("Recommended: python run_local.py native")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "native":
        run_native()
    elif mode == "streamlit":
        run_streamlit()
    elif mode == "flask":
        run_flask()
    else:
        print("❌ Invalid mode. Use 'native', 'streamlit', or 'flask'")
        print("Recommended: python run_local.py native")
        sys.exit(1)

if __name__ == "__main__":
    main()