#!/usr/bin/env python3
"""
Script to fix PostgreSQL permissions for the trading analysis app.
This script connects to PostgreSQL and grants the necessary privileges.
"""

import psycopg2
import os
from urllib.parse import urlparse

def fix_postgres_permissions():
    """Fix PostgreSQL permissions for the trading_user"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL environment variable not found!")
        return False
    
    # Parse the database URL
    parsed = urlparse(database_url)
    
    # Extract connection details
    host = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path[1:]  # Remove leading slash
    username = parsed.username
    password = parsed.password
    
    print(f"Connecting to PostgreSQL at {host}:{port}")
    print(f"Database: {database}")
    print(f"User: {username}")
    
    try:
        # First, connect as the trading_user to test the connection
        print("\n1. Testing connection as trading_user...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password
        )
        conn.close()
        print("✓ Connection as trading_user successful!")
        
        # Now we need to connect as a superuser to grant privileges
        # Try common superuser names
        superusers = ['postgres', 'admin', 'root']
        
        for superuser in superusers:
            try:
                print(f"\n2. Trying to connect as superuser '{superuser}'...")
                
                # Try to connect as superuser (you'll need to provide password)
                print(f"Please enter password for superuser '{superuser}' (or press Enter to skip):")
                superuser_password = input().strip()
                
                if not superuser_password:
                    continue
                
                superuser_conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database='postgres',  # Connect to default database first
                    user=superuser,
                    password=superuser_password
                )
                
                print(f"✓ Connected as superuser '{superuser}'!")
                
                # Grant privileges
                print("\n3. Granting database privileges...")
                with superuser_conn.cursor() as cur:
                    # Grant all privileges on the database
                    cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {database} TO {username};")
                    print(f"✓ Granted all privileges on database '{database}' to '{username}'")
                
                # Connect to the specific database
                superuser_conn.close()
                superuser_conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=superuser,
                    password=superuser_password
                )
                
                print("\n4. Granting schema privileges...")
                with superuser_conn.cursor() as cur:
                    # Grant schema privileges
                    cur.execute(f"GRANT USAGE, CREATE ON SCHEMA public TO {username};")
                    print(f"✓ Granted USAGE, CREATE on schema public to '{username}'")
                    
                    # Make the user the owner of the public schema
                    cur.execute(f"ALTER SCHEMA public OWNER TO {username};")
                    print(f"✓ Made '{username}' the owner of public schema")
                    
                    # Grant all privileges on all tables (current and future)
                    cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {username};")
                    print(f"✓ Granted all privileges on all tables to '{username}'")
                    
                    cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {username};")
                    print(f"✓ Granted all privileges on all sequences to '{username}'")
                    
                    # Set default privileges for future tables
                    cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {username};")
                    print(f"✓ Set default privileges for future tables")
                    
                    cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {username};")
                    print(f"✓ Set default privileges for future sequences")
                
                superuser_conn.commit()
                superuser_conn.close()
                
                print("\n✅ PostgreSQL permissions fixed successfully!")
                return True
                
            except psycopg2.Error as e:
                print(f"✗ Failed to connect as '{superuser}': {e}")
                continue
            except Exception as e:
                print(f"✗ Error with '{superuser}': {e}")
                continue
        
        print("\n❌ Could not connect as any superuser.")
        print("You may need to:")
        print("1. Install PostgreSQL locally")
        print("2. Use pgAdmin or another GUI tool")
        print("3. Contact your database administrator")
        return False
        
    except psycopg2.Error as e:
        print(f"❌ Database connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("PostgreSQL Permission Fix Script")
    print("=" * 40)
    
    success = fix_postgres_permissions()
    
    if success:
        print("\n🎉 Permissions fixed! You can now run your Flask app.")
    else:
        print("\n💡 Alternative: Use SQLite for now by commenting out the DATABASE_URL line in app.py") 