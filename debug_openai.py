#!/usr/bin/env python3

import os
import sys

def debug_openai():
    """Debug OpenAI client creation step by step"""
    
    print("🔍 Debugging OpenAI Client Creation")
    print("=" * 50)
    
    # 1. Load environment
    print("\n1. Loading environment variables:")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env file loaded")
    except Exception as e:
        print(f"❌ Error loading .env: {e}")
        return
    
    # 2. Check API key
    print("\n2. Checking API key:")
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"✅ API key found: {api_key[:20]}...")
    else:
        print("❌ No API key found")
        return
    
    # 3. Check OpenAI import
    print("\n3. Checking OpenAI import:")
    try:
        from openai import OpenAI
        print("✅ OpenAI imported successfully")
    except Exception as e:
        print(f"❌ OpenAI import failed: {e}")
        return
    
    # 4. Check environment variables that might interfere
    print("\n4. Checking environment variables:")
    proxy_vars = [k for k in os.environ.keys() if 'proxy' in k.lower() or 'http' in k.lower()]
    if proxy_vars:
        print(f"⚠️ Found potential interfering vars: {proxy_vars}")
        for var in proxy_vars:
            print(f"   {var}: {os.environ[var]}")
    else:
        print("✅ No proxy/HTTP environment variables found")
    
    # 5. Try to create client
    print("\n5. Creating OpenAI client:")
    try:
        client = OpenAI(api_key=api_key)
        print("✅ Client created successfully!")
        
        # 6. Test API call
        print("\n6. Testing API call:")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Hello'"}],
            max_tokens=10
        )
        result = response.choices[0].message.content
        print(f"✅ API call successful: {result}")
        
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Try to get more details about the error
        if hasattr(e, '__dict__'):
            print(f"Error attributes: {e.__dict__}")

if __name__ == "__main__":
    debug_openai()
