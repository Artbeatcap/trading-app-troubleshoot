#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv

def fix_openai_client():
    """Fix OpenAI client initialization issue"""
    
    print("🔧 Fixing OpenAI Client Issue")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found")
        return False
    
    print(f"✅ API key found: {api_key[:20]}...")
    
    # Try different approaches to create the client
    print("\n🔍 Testing different client initialization methods...")
    
    # Method 1: Basic initialization
    print("\n1. Testing basic initialization:")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print("✅ Basic initialization successful!")
        
        # Test API call
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": "Say 'Hello'"}],
            max_tokens=10
        )
        print(f"✅ API call successful: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Basic initialization failed: {e}")
    
    # Method 2: Check for proxy environment variables
    print("\n2. Checking for proxy environment variables:")
    proxy_vars = [k for k in os.environ.keys() if 'proxy' in k.lower()]
    if proxy_vars:
        print(f"⚠️ Found proxy variables: {proxy_vars}")
        for var in proxy_vars:
            print(f"   {var}: {os.environ[var]}")
        
        # Try to temporarily unset proxy variables
        print("\n3. Testing without proxy variables:")
        try:
            # Save original values
            original_proxies = {}
            for var in proxy_vars:
                original_proxies[var] = os.environ.get(var)
                del os.environ[var]
            
            # Try client creation
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            print("✅ Client created without proxy variables!")
            
            # Test API call
            response = client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": "Say 'Hello'"}],
                max_tokens=10
            )
            print(f"✅ API call successful: {response.choices[0].message.content}")
            
            # Restore original values
            for var, value in original_proxies.items():
                if value:
                    os.environ[var] = value
            
            print("\n💡 SOLUTION: The issue is caused by proxy environment variables.")
            print("   The OpenAI client is trying to use proxy settings that aren't compatible.")
            return True
            
        except Exception as e:
            print(f"❌ Still failed: {e}")
            
            # Restore original values
            for var, value in original_proxies.items():
                if value:
                    os.environ[var] = value
    else:
        print("✅ No proxy variables found")
    
    # Method 3: Try with explicit parameters
    print("\n4. Testing with explicit parameters:")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.openai.com/v1"
        )
        print("✅ Client created with explicit base_url!")
        
        # Test API call
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": "Say 'Hello'"}],
            max_tokens=10
        )
        print(f"✅ API call successful: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Explicit parameters failed: {e}")
    
    print("\n❌ All methods failed. OpenAI client cannot be initialized.")
    return False

if __name__ == "__main__":
    fix_openai_client()
