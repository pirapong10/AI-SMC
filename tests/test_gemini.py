"""
Test Gemini API Connection
Step 2: Test Gemini API Key
"""

import os
import sys
import io
from pathlib import Path

# Force UTF-8 output encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

def test_gemini_api():
    """Test Gemini API connection"""
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    print("=" * 50)
    print("[KEY] Gemini API Test")
    print("=" * 50)
    
    # Step 1: Check API key
    if not api_key:
        print("[FAIL] GEMINI_API_KEY not found in .env")
        return False
    
    print(f"[OK] API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Step 2: Configure Gemini
    try:
        genai.configure(api_key=api_key)
        print("[OK] Gemini configured successfully")
    except Exception as e:
        print(f"[FAIL] Configuration failed: {e}")
        return False
    
    # Step 3: Test API call
    try:
        print("\n[...] Testing API connection with gemini-2.5-flash...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            "Say 'Hello from AI SMC Trading Bot!' and nothing else."
        )
        print(f"[OK] API Response: {response.text.strip()}")
    except Exception as e:
        print(f"[FAIL] API call failed: {e}")
        return False
    
    # Step 4: Test with trading context
    try:
        print("\n[...] Testing with SMC trading prompt...")
        response = model.generate_content(
            "In one sentence, what is a 'Liquidity Sweep' in Smart Money Concepts (SMC) trading?"
        )
        print(f"[OK] SMC Response: {response.text.strip()}")
    except Exception as e:
        print(f"[FAIL] SMC test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("[PASS] All tests passed! Gemini API is ready.")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1)
