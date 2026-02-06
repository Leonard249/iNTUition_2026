import requests
import json
import os
import sys

# Base URL for the server
BASE_URL = "http://localhost:8000"

# Path to your specific file
IMAGE_PATH = os.path.join("images", "shopee.png")

def test_shopee_flow():
    print(f"1. 🔍 Checking for image file...")
    if not os.path.exists(IMAGE_PATH):
        print(f"   ❌ File not found at: {IMAGE_PATH}")
        print("      Please make sure you are running this from the 'backend' folder")
        print("      and that 'images/shopee.png' exists.")
        return
    print(f"   ✅ Found {IMAGE_PATH}")

    print(f"\n2. 🏥 Checking API Health...")
    try:
        requests.get(f"{BASE_URL}/health")
    except Exception:
        print(f"   ❌ Server not running at {BASE_URL}. Run 'uv run run.py' first.")
        return

    print(f"\n3. 🧠 Analyzing Shopee Page...")
    
    # Mock DOM elements (Simulating what a browser extension would see on Shopee)
    # This helps the AI match the visual screenshot to code elements
    shopee_dom_data = [
        {
            "tag": "input", 
            "text": "", 
            "selector": ".shopee-searchbar-input__input", 
            "placeholder": "Sign up and get 100% off first order",
            "bounds": {"x": 200, "y": 40}
        },
        {
            "tag": "button", 
            "text": "Search", 
            "selector": ".shopee-searchbar__search-button", 
            "bounds": {"x": 800, "y": 40}
        },
        {
            "tag": "a", 
            "text": "Cart", 
            "selector": ".shopee-cart-icon", 
            "bounds": {"x": 950, "y": 40}
        },
        {
            "tag": "div", 
            "text": "Login", 
            "selector": ".navbar__link--login", 
            "bounds": {"x": 1100, "y": 10}
        }
    ]

    files = {
        'screenshot': ('shopee.png', open(IMAGE_PATH, 'rb'), 'image/png')
    }
    
    data = {
        'dom_elements': json.dumps(shopee_dom_data),
        'session_id': 'test-session-shopee'
    }

    try:
        # Send POST request
        response = requests.post(f"{BASE_URL}/api/analyze-page", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n   ✅ SUCCESS! AI Analysis Result:")
            print("   ------------------------------------------------")
            # Pretty print the AI's response
            print(json.dumps(result["analysis"], indent=2))
            print("   ------------------------------------------------")
            print(f"   Session ID: {result.get('session_id')}")
            print(f"   Elements processed: {result.get('elements_count')}")
            
        else:
            print(f"\n   ❌ Failed with status: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request Error: {e}")
    finally:
        # Close the file handle
        files['screenshot'][1].close()

if __name__ == "__main__":
    test_shopee_flow()