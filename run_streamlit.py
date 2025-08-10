#!/usr/bin/env python3
"""
Launcher script for the Tax Loss Harvesting Streamlit application.
Run this script to start the Streamlit server.
"""

import subprocess
import sys
import os

def main():
    """Launch the Streamlit application"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("Streamlit is not installed. Installing required packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Launch the Streamlit app
    print("🚀 Launching Tax Loss Harvesting Dashboard...")
    print("📊 The app will open in your default web browser")
    print("🔗 If it doesn't open automatically, go to: http://localhost:8501")
    print("\nPress Ctrl+C to stop the server")
    
    # Run streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "streamlit_app.py",
        "--server.port", "8501",
        "--server.headless", "false"
    ])

if __name__ == "__main__":
    main()
