#!/usr/bin/env python3
"""Test script for the contact form API endpoint.

This script demonstrates how to use the contact form API and validates
that it works correctly.
"""

import asyncio
import json
from pathlib import Path

import httpx


async def test_contact_form_api() -> None:
    """Test the contact form API endpoint."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("=" * 70)
        print("Testing MAO Contact Form API")
        print("=" * 70)
        print()

        # Test 1: Health check
        print("1. Testing health check endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            response.raise_for_status()
            print(f"   ✓ Health check passed: {response.json()}")
        except Exception as e:
            print(f"   ✗ Health check failed: {e}")
            print("   Make sure the API server is running: mao-api")
            return

        print()

        # Test 2: Root endpoint
        print("2. Testing root endpoint...")
        try:
            response = await client.get(f"{base_url}/")
            response.raise_for_status()
            data = response.json()
            print(f"   ✓ Root endpoint: {data['name']} v{data['version']}")
        except Exception as e:
            print(f"   ✗ Root endpoint failed: {e}")

        print()

        # Test 3: Submit valid contact form
        print("3. Testing valid contact form submission...")
        valid_form = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "message": "This is a test message to verify the contact form API works correctly.",
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/contact",
                json=valid_form,
            )
            response.raise_for_status()
            data = response.json()
            print(f"   ✓ Form submitted successfully")
            print(f"     - Status: {data['status']}")
            print(f"     - Message: {data['message']}")
            print(f"     - Submission ID: {data['submission_id']}")
            submission_id = data["submission_id"]
        except Exception as e:
            print(f"   ✗ Form submission failed: {e}")
            if hasattr(e, "response"):
                print(f"     Response: {e.response.text}")
            submission_id = None

        print()

        # Test 4: Retrieve submitted form
        if submission_id:
            print("4. Testing form retrieval...")
            try:
                response = await client.get(f"{base_url}/api/v1/contact/{submission_id}")
                response.raise_for_status()
                data = response.json()
                print(f"   ✓ Form retrieved successfully")
                print(f"     - Name: {data['name']}")
                print(f"     - Email: {data['email']}")
                print(f"     - Submitted at: {data['submitted_at']}")
            except Exception as e:
                print(f"   ✗ Form retrieval failed: {e}")

            print()

        # Test 5: List all forms
        print("5. Testing list all forms...")
        try:
            response = await client.get(f"{base_url}/api/v1/contact")
            response.raise_for_status()
            data = response.json()
            print(f"   ✓ Retrieved {len(data)} form(s)")
            for i, form in enumerate(data[:3], 1):
                print(f"     {i}. {form['name']} ({form['email']}) - {form['submission_id']}")
        except Exception as e:
            print(f"   ✗ List forms failed: {e}")

        print()

        # Test 6: Invalid form (missing required field)
        print("6. Testing invalid form (missing message)...")
        invalid_form = {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/contact",
                json=invalid_form,
            )
            if response.status_code == 422:
                print(f"   ✓ Validation error caught correctly")
                print(f"     Status code: {response.status_code}")
            else:
                print(f"   ✗ Expected validation error, got: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Test failed unexpectedly: {e}")

        print()

        # Test 7: Invalid form (invalid email)
        print("7. Testing invalid form (invalid email)...")
        invalid_email_form = {
            "name": "Test User",
            "email": "not-an-email",
            "message": "This should fail due to invalid email format.",
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/contact",
                json=invalid_email_form,
            )
            if response.status_code == 422:
                print(f"   ✓ Email validation error caught correctly")
                print(f"     Status code: {response.status_code}")
            else:
                print(f"   ✗ Expected validation error, got: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Test failed unexpectedly: {e}")

        print()

        # Test 8: Invalid form (message too short)
        print("8. Testing invalid form (message too short)...")
        short_message_form = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "Short",
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/contact",
                json=short_message_form,
            )
            if response.status_code == 422:
                print(f"   ✓ Message length validation error caught correctly")
                print(f"     Status code: {response.status_code}")
            else:
                print(f"   ✗ Expected validation error, got: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Test failed unexpectedly: {e}")

        print()
        print("=" * 70)
        print("Testing Complete")
        print("=" * 70)
        print()

        # Check storage directory
        storage_dir = Path(".mao/contact_forms")
        if storage_dir.exists():
            json_files = list(storage_dir.glob("*.json"))
            print(f"Stored submissions: {len(json_files)} file(s) in {storage_dir}")
            if json_files:
                print("\nExample stored submission:")
                with open(json_files[0]) as f:
                    data = json.load(f)
                    print(json.dumps(data, indent=2))
        else:
            print(f"Storage directory not found: {storage_dir}")


def main() -> None:
    """Main entry point."""
    print("\nStarting API tests...")
    print("Make sure the API server is running: mao-api\n")

    try:
        asyncio.run(test_contact_form_api())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")


if __name__ == "__main__":
    main()
