#!/usr/bin/env python
"""Diagnose database connection issues."""

import os
import sys
from typing import Optional
import psycopg2

def test_connection(host: str, port: int, user: str, password: str, database: str, sslmode: str = "disable") -> bool:
    """Test database connection."""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            sslmode=sslmode,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"✓ Connected to {host}:{port} (SSL: {sslmode})")
        print(f"  PostgreSQL: {version.split(',')[0]}")
        return True
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "could not translate host name" in error_msg:
            print(f"✗ DNS resolution failed for {host}")
        elif "Connection refused" in error_msg:
            print(f"✗ Connection refused to {host}:{port} (port not open or service not listening)")
        elif "password authentication failed" in error_msg:
            print(f"✗ Authentication failed for user '{user}' at {host}:{port}")
        elif "does not support SSL" in error_msg:
            print(f"✗ SSL required but server doesn't support it (at {host}:{port})")
        else:
            print(f"✗ Connection error: {error_msg}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")
        return False

def main():
    """Run connection tests."""
    print("Database Connection Diagnostic Tool")
    print("=" * 50)

    # Read config from .env
    from dotenv import load_dotenv
    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        return False

    print(f"Current DATABASE_URL: {db_url[:60]}...")
    print()

    # Parse connection string
    import re
    match = re.match(
        r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)",
        db_url
    )

    if not match:
        print("ERROR: Invalid DATABASE_URL format")
        return False

    user, password, host, port, database = match.groups()
    port = int(port)

    print("Testing connection configurations:")
    print()

    # Test 1: Current config
    print(f"1. Current config: {host}:{port}/{database}")
    test_connection(host, port, user, password, database)
    print()

    # Test 2: Try different ports if using public IP
    if "37.59.112.53" in host:
        print(f"2. Try port 3000 (Coolify port mapping):")
        test_connection(host, 3000, user, password, database)
        print()

    # Test 3: Localhost for development
    print(f"3. Try localhost (development):")
    test_connection("localhost", 5432, user, password, database)
    print()

    # Test 4: Alternative database names
    if database == "postgres":
        alt_db = "job_apply_db"
        print(f"4. Try alternative database name: {alt_db}")
        test_connection(host, port, user, password, alt_db)
        print()

    print("Recommendations:")
    print("- If public IP fails with authentication: check Coolify for public proxy settings")
    print("- If localhost works: set DATABASE_URL to postgresql://user:pass@localhost:5432/db")
    print("- If port 3000 works: set DATABASE_URL to postgresql://user:pass@37.59.112.53:3000/db")

if __name__ == "__main__":
    main()
