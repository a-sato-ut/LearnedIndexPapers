#!/usr/bin/env python3
"""
Test OpenAlex API connectivity and basic functionality.
"""

import requests
import json

def test_basic_api():
    """Test basic OpenAlex API connectivity."""
    print("Testing OpenAlex API connectivity...")
    
    # Test 1: Basic works endpoint
    print("\n1. Testing basic works endpoint...")
    try:
        r = requests.get("https://api.openalex.org/works", params={"per-page": 1})
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Results count: {len(data.get('results', []))}")
        else:
            print(f"Error: {r.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 2: Search by title
    print("\n2. Testing search by title...")
    try:
        r = requests.get("https://api.openalex.org/works", params={
            "search": "The Case for Learned Index Structures",
            "per-page": 1
        })
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Results count: {len(data.get('results', []))}")
            if data.get('results'):
                work = data['results'][0]
                print(f"Found work: {work.get('display_name', 'N/A')}")
                print(f"DOI: {work.get('doi', 'N/A')}")
                print(f"Cited by count: {work.get('cited_by_count', 'N/A')}")
        else:
            print(f"Error: {r.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 3: Search by DOI
    print("\n3. Testing search by DOI...")
    try:
        r = requests.get("https://api.openalex.org/works", params={
            "filter": "doi:10.1145/3183713.3196909",
            "per-page": 1
        })
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Results count: {len(data.get('results', []))}")
            if data.get('results'):
                work = data['results'][0]
                print(f"Found work: {work.get('display_name', 'N/A')}")
                print(f"Cited by API URL: {work.get('cited_by_api_url', 'N/A')}")
        else:
            print(f"Error: {r.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 4: With mailto parameter
    print("\n4. Testing with mailto parameter...")
    try:
        r = requests.get("https://api.openalex.org/works", params={
            "search": "The Case for Learned Index Structures",
            "per-page": 1,
            "mailto": "test@example.com"
        })
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Results count: {len(data.get('results', []))}")
        else:
            print(f"Error: {r.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_basic_api() 