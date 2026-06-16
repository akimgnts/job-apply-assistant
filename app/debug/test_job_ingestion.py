"""
Test script for job ingestion service.

Usage:
    python -m app.debug.test_job_ingestion "https://example.com/job"
    python -m app.debug.test_job_ingestion "paste job text here"
"""

import asyncio
import sys
from app.services.job_ingestion_service import ingest_job_input


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.debug.test_job_ingestion <URL or text>")
        sys.exit(1)

    raw_input = " ".join(sys.argv[1:])

    print(f"\n📋 Testing job ingestion...")
    print(f"Input: {raw_input[:100]}...")

    result = await ingest_job_input(raw_input)

    print(f"\n✅ Result:")
    print(f"  source_type: {result['source_type']}")
    print(f"  source_url: {result['source_url']}")
    print(f"  extraction_success: {result['extraction_success']}")

    if result["extraction_success"]:
        clean_text = result["clean_text"]
        print(f"  extracted_length: {len(clean_text)} chars")
        print(f"\n📄 First 1000 characters:\n")
        print(clean_text[:1000])
        if len(clean_text) > 1000:
            print(f"\n... ({len(clean_text) - 1000} more characters)")
    else:
        print(f"  error: {result['error']}")

    print(f"\n")


if __name__ == "__main__":
    asyncio.run(main())
