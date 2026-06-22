#!/usr/bin/env python
"""Coolify-specific database connection testing."""

import sys
import os
from typing import Optional
import psycopg2

COOLIFY_IP = "37.59.112.53"
COOLIFY_PORT = 5432
COOLIFY_USER = "postgres"
COOLIFY_PASSWORD = "K5InfD88xGYxS3dUFr210Jmu1SgKzxTTxpqsgQ0Ua0dj3W0wQqf7QM5cfL3gAFca"
COOLIFY_DATABASE = "postgres"

def test_raw_connection():
    """Test TCP connection to Coolify proxy."""
    print("🔌 Testing network connectivity...")
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((COOLIFY_IP, COOLIFY_PORT))
        sock.close()
        if result == 0:
            print(f"   ✓ TCP connection to {COOLIFY_IP}:{COOLIFY_PORT} successful")
            return True
        else:
            print(f"   ✗ Cannot reach {COOLIFY_IP}:{COOLIFY_PORT}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_postgres_connection():
    """Test PostgreSQL auth."""
    print("\n🔐 Testing PostgreSQL authentication...")
    try:
        conn = psycopg2.connect(
            host=COOLIFY_IP,
            port=COOLIFY_PORT,
            user=COOLIFY_USER,
            password=COOLIFY_PASSWORD,
            database=COOLIFY_DATABASE,
            sslmode='disable',
            connect_timeout=3
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        print(f"   ✓ PostgreSQL auth successful")
        print(f"   Server: {version.split(',')[0]}")
        return True
    except psycopg2.OperationalError as e:
        error = str(e)
        print(f"   ✗ PostgreSQL error: {error}")

        if "password authentication failed" in error:
            print("\n   💡 Suggestions:")
            print("      1. Check if password is correct in .env")
            print("      2. Coolify might use different credentials for public access")
            print("      3. Try creating a new user in Coolify for public access")
            print("      4. Verify public proxy is enabled in Coolify dashboard")
        elif "does not exist" in error:
            print("\n   💡 Database might not exist")
            print("      Create it in Coolify dashboard first")

        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {type(e).__name__}: {e}")
        return False

def test_database_contents():
    """Check what's in the database."""
    print("\n📊 Checking database contents...")
    try:
        conn = psycopg2.connect(
            host=COOLIFY_IP,
            port=COOLIFY_PORT,
            user=COOLIFY_USER,
            password=COOLIFY_PASSWORD,
            database=COOLIFY_DATABASE,
            sslmode='disable',
            connect_timeout=3
        )
        cursor = conn.cursor()

        # List tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"   ✓ Found {len(tables)} tables:")
            for (table,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"      - {table}: {count} rows")
        else:
            print("   ⚠️  Database is empty (no tables)")

        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"   ✗ Cannot query database: {type(e).__name__}")
        return False

def main():
    """Run Coolify-specific tests."""
    print("🌐 Coolify PostgreSQL Connection Test")
    print("=" * 50)
    print(f"\nTarget: {COOLIFY_IP}:{COOLIFY_PORT}")
    print(f"User: {COOLIFY_USER}")
    print(f"Database: {COOLIFY_DATABASE}")
    print()

    # Test network first
    if not test_raw_connection():
        print("\n❌ Cannot reach Coolify server")
        print("   Check if IP address is correct")
        return False

    # Test auth
    if not test_postgres_connection():
        print("\n❌ PostgreSQL authentication failed")
        print("\n📋 Next steps:")
        print("   1. Review COOLIFY_SETUP.md for troubleshooting")
        print("   2. Verify password in Coolify dashboard")
        print("   3. Check if public proxy is enabled")
        return False

    # Check contents
    test_database_contents()

    print("\n✅ Connection successful!")
    print("\n🚀 You can now run the bot:")
    print("   python -m app.bot.telegram_bot")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
