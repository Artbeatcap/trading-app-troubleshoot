#!/usr/bin/env python3
"""
Test brief_routes import
"""

try:
    from brief_routes import register_brief_routes
    print("✅ Brief routes imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

