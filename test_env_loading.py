#!/usr/bin/env python3

import os
import sys
from pathlib import Path

def test_env_loading():
    """Test loading environment variables from .env file"""
    
    print("🔍 Testing Environment Variable Loading")
    print("=" * 50)
    
    # Check before loading .env
    print("\n1. Before loading .env file:")
    api_key_before = os.getenv('OPENAI_API_KEY')
    print(f"OPENAI_API_KEY: {'SET' if api_key_before else 'NOT SET'}")
    
    # Try to load .env file
    print("\n2. Loading .env file:")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env file loaded successfully")
    except ImportError:
        print("❌ python-dotenv not installed")
        return False
    except Exception as e:
        print(f"❌ Error loading .env: {e}")
        return False
    
    # Check after loading .env
    print("\n3. After loading .env file:")
    api_key_after = os.getenv('OPENAI_API_KEY')
    if api_key_after:
        print(f"✅ OPENAI_API_KEY: {api_key_after[:20]}...")
    else:
        print("❌ OPENAI_API_KEY: STILL NOT SET")
    
    # Test OpenAI client creation
    print("\n4. Testing OpenAI client creation:")
    if api_key_after:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key_after)
            print("✅ OpenAI client created successfully")
            
            # Test API call
            print("\n5. Testing API call:")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Say 'API is working!' in one sentence."}
                ],
                max_tokens=20
            )
            result = response.choices[0].message.content
            print(f"✅ API call successful: {result}")
            return True
            
        except Exception as e:
            print(f"❌ OpenAI test failed: {e}")
            return False
    else:
        print("❌ Cannot test OpenAI - no API key")
        return False

if __name__ == "__main__":
    test_env_loading()
