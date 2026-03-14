#!/usr/bin/env python3
"""
Quick Supabase connection test - verifies credentials and database schema.

Usage:
    python scripts/verify_supabase.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def main():
    """Verify Supabase configuration and schema."""
    print("\n" + "="*70)
    print("Supabase Configuration Verification")
    print("="*70 + "\n")
    
    # 1. Check environment variables
    print("1. Checking environment variables...")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url:
        print("   ❌ SUPABASE_URL not set in .env")
        print("   → Add: SUPABASE_URL=https://your-project-ref.supabase.co")
        sys.exit(1)
    
    if not key:
        print("   ❌ SUPABASE_KEY not set in .env")
        print("   → Add: SUPABASE_KEY=your-supabase-anon-key")
        sys.exit(1)
    
    print(f"   ✅ SUPABASE_URL: {url}")
    print(f"   ✅ SUPABASE_KEY: {key[:20]}...")
    
    # 2. Check supabase package
    print("\n2. Checking supabase package...")
    try:
        import supabase
        print(f"   ✅ supabase package installed (version: {supabase.__version__})")
    except ImportError:
        print("   ❌ supabase package not installed")
        print("   → Run: pip install supabase")
        sys.exit(1)
    
    # 3. Test connection
    print("\n3. Testing connection to Supabase...")
    try:
        from src.orchestrator.supabase_adapter import create_supabase_adapter
        adapter = create_supabase_adapter()
        print("   ✅ Connection successful")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        sys.exit(1)
    
    # 4. Check schema
    print("\n4. Verifying database schema...")
    try:
        # Check projects table
        adapter.client.table("projects").select("session_id").limit(0).execute()
        print("   ✅ 'projects' table exists")
    except Exception as e:
        print("   ❌ 'projects' table missing")
        print("   → Run migration: migrations/001_initial_schema.sql in Supabase SQL Editor")
        print(f"   → Error: {e}")
        sys.exit(1)
    
    try:
        # Check conversation_messages table
        adapter.client.table("conversation_messages").select("id").limit(0).execute()
        print("   ✅ 'conversation_messages' table exists")
    except Exception as e:
        print("   ❌ 'conversation_messages' table missing")
        print("   → Run migration: migrations/001_initial_schema.sql")
        sys.exit(1)
    
    try:
        # Check mockups table
        adapter.client.table("mockups").select("id").limit(0).execute()
        print("   ✅ 'mockups' table exists")
    except Exception as e:
        print("   ❌ 'mockups' table missing")
        print("   → Run migration: migrations/001_initial_schema.sql")
        sys.exit(1)
    
    # 5. Summary
    print("\n" + "="*70)
    print("✅ ALL CHECKS PASSED - Supabase is ready!")
    print("="*70)
    print("\nNext steps:")
    print("1. Run full test suite: python test_supabase_adapter.py")
    print("2. Start using the app - state will persist automatically!")
    print("3. View data in Supabase Dashboard → Table Editor")


if __name__ == "__main__":
    main()
