#!/usr/bin/env python3
"""
Script to check all database sequences and their permissions
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def check_all_sequences():
    """Check all database sequences and their permissions"""
    
    with app.app_context():
        print("Checking all database sequences...")
        print("=" * 50)
        
        try:
            with db.engine.connect() as conn:
                # Get all sequences
                result = conn.execute(text("""
                    SELECT sequence_name 
                    FROM information_schema.sequences 
                    WHERE sequence_schema = 'public'
                    ORDER BY sequence_name;
                """))
                
                print("All sequences in database:")
                sequences = []
                for row in result:
                    sequences.append(row[0])
                    print(f"  {row[0]}")
                
                print(f"\nTotal sequences: {len(sequences)}")
                
                # Check permissions for each sequence
                for sequence_name in sequences:
                    print(f"\nChecking permissions for {sequence_name}:")
                    
                    result = conn.execute(text("""
                        SELECT grantee, privilege_type 
                        FROM information_schema.usage_privileges 
                        WHERE object_name = :sequence_name;
                    """), {"sequence_name": sequence_name})
                    
                    permissions = []
                    for row in result:
                        permissions.append(f"{row[0]}: {row[1]}")
                        print(f"  {row[0]}: {row[1]}")
                    
                    if not permissions:
                        print("  No explicit permissions found")
                    
                    # Check if tradingapp has permissions
                    tradingapp_has_permissions = any('tradingapp' in perm for perm in permissions)
                    
                    if not tradingapp_has_permissions:
                        print(f"  ❌ tradingapp user does not have permissions on {sequence_name}")
                    else:
                        print(f"  ✅ tradingapp user has permissions on {sequence_name}")
                        
        except Exception as e:
            print(f"❌ Error checking sequences: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_all_sequences()




