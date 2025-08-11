#!/usr/bin/env python3
"""
Test script to verify the setup and API connectivity.
"""

import os
from dotenv import load_dotenv
import requests

def test_setup():
    """Test if the environment is properly configured."""
    print("Testing Twelve Data Dividends Extractor Setup...")
    print("=" * 50)
    
    # Test 1: Check if .env file exists and loads
    if not os.path.exists('.env'):
        print("❌ .env file not found. Please copy .env.example to .env and add your API key.")
        return False
    
    load_dotenv()
    api_key = os.getenv('TWELVE_DATA_API_KEY')
    
    if not api_key or api_key == 'your_twelve_data_api_key_here':
        print("❌ TWELVE_DATA_API_KEY not set or still has placeholder value.")
        print("   Please edit .env file and add your actual API key.")
        return False
    
    print("✅ Environment variables loaded successfully")
    
    # Test 2: Check if symbols.txt exists
    if not os.path.exists('symbols.txt'):
        print("❌ symbols.txt file not found")
        return False
    
    print("✅ symbols.txt file found")
    
    # Test 3: Test API connectivity
    try:
        url = "https://api.twelvedata.com/stocks"
        params = {
            'symbol': 'AAPL',
            'apikey': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and data['data']:
            print("✅ API connectivity test successful")
            print(f"   Test query returned data for AAPL: {data['data'][0].get('name', 'Unknown')}")
        else:
            print("❌ API returned empty data - check your API key")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API connectivity test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during API test: {e}")
        return False
    
    print("\n🎉 All tests passed! You're ready to run the extractor.")
    print("\nExample usage:")
    print("python extract_dividends.py 2024-01-01 2024-12-31 --limit 5")
    
    return True

if __name__ == '__main__':
    test_setup()
