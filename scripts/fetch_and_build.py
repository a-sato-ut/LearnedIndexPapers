#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main script that orchestrates the data fetching and processing pipeline.
This script calls fetch_data.py and process_data.py in sequence.

- First fetches raw data from OpenAlex using fetch_data.py
- Then processes the data with tags and statistics using process_data.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

def main():
    print("Starting data pipeline...")
    
    # Step 1: Fetch raw data
    print("\n=== Step 1: Fetching data from OpenAlex ===")
    fetch_script = SCRIPTS_DIR / "fetch_data.py"
    result = subprocess.run([sys.executable, str(fetch_script)], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error in fetch_data.py:")
        print(result.stderr)
        sys.exit(1)
    
    print(result.stdout)
    
    # Step 2: Process data with tags and statistics
    print("\n=== Step 2: Processing data with tags and statistics ===")
    process_script = SCRIPTS_DIR / "process_data.py"
    result = subprocess.run([sys.executable, str(process_script)], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error in process_data.py:")
        print(result.stderr)
        sys.exit(1)
    
    print(result.stdout)
    
    print("\n=== Pipeline completed successfully ===")

if __name__ == "__main__":
    main() 