#!/usr/bin/env python3
"""
Security validation test script
Tests that the application properly enforces security requirements
"""

import os
import sys
import subprocess
import tempfile

def test_missing_secret_key():
    """Test that app fails when SECRET_KEY is not set"""
    print("Test 1: Checking SECRET_KEY requirement...")
    
    # Create a minimal test that tries to import server without SECRET_KEY
    test_code = """
import os
# Clear any existing SECRET_KEY
os.environ.pop('SECRET_KEY', None)
os.environ.pop('SPOTIFY_CLIENT_ID', None)
os.environ.pop('SPOTIFY_CLIENT_SECRET', None)

try:
    import server
    print("FAIL: App should not start without SECRET_KEY")
    sys.exit(1)
except RuntimeError as e:
    if "SECRET_KEY" in str(e):
        print("PASS: App correctly requires SECRET_KEY")
        sys.exit(0)
    else:
        print(f"FAIL: Wrong error: {e}")
        sys.exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_code],
        cwd="/home/runner/work/MelodySearch/MelodySearch",
        capture_output=True,
        text=True
    )
    
    if "PASS" in result.stdout:
        print("✓ SECRET_KEY validation works correctly")
        return True
    else:
        print("✗ SECRET_KEY validation failed")
        print(result.stdout)
        print(result.stderr)
        return False


def test_missing_spotify_credentials():
    """Test that app fails when Spotify credentials are not set"""
    print("\nTest 2: Checking Spotify credentials requirement...")
    
    test_code = """
import os
import sys
# Set SECRET_KEY but not Spotify credentials
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ.pop('SPOTIFY_CLIENT_ID', None)
os.environ.pop('SPOTIFY_CLIENT_SECRET', None)

try:
    import server
    print("FAIL: App should not start without Spotify credentials")
    sys.exit(1)
except RuntimeError as e:
    if "SPOTIFY_CLIENT_ID" in str(e) or "SPOTIFY_CLIENT_SECRET" in str(e):
        print("PASS: App correctly requires Spotify credentials")
        sys.exit(0)
    else:
        print(f"FAIL: Wrong error: {e}")
        sys.exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_code],
        cwd="/home/runner/work/MelodySearch/MelodySearch",
        capture_output=True,
        text=True
    )
    
    if "PASS" in result.stdout:
        print("✓ Spotify credentials validation works correctly")
        return True
    else:
        print("✗ Spotify credentials validation failed")
        print(result.stdout)
        print(result.stderr)
        return False


def test_no_hardcoded_credentials():
    """Test that no hardcoded credentials exist in the codebase"""
    print("\nTest 3: Checking for hardcoded credentials...")
    
    # Common patterns for credentials
    patterns = [
        "9818b6e351d84e1ab29bf345fa7ee898",  # Old client ID
        "3dc0f649da4b4bd1bf30966ea4f3f49e",  # Old client secret
        "dev-secret-key-12345"                # Old weak secret key
    ]
    
    found_credentials = []
    for pattern in patterns:
        result = subprocess.run(
            ["grep", "-r", pattern, ".", "--include=*.py", "--exclude=test_security.py"],
            cwd="/home/runner/work/MelodySearch/MelodySearch",
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:  # Found matches
            found_credentials.append((pattern, result.stdout))
    
    if not found_credentials:
        print("✓ No hardcoded credentials found")
        return True
    else:
        print("✗ Found hardcoded credentials:")
        for cred, location in found_credentials:
            print(f"  - {cred[:20]}... in:")
            print(f"    {location.strip()}")
        return False


def test_gunicorn_version():
    """Test that gunicorn is at secure version"""
    print("\nTest 4: Checking gunicorn version...")
    
    with open("/home/runner/work/MelodySearch/MelodySearch/requirements.txt", "r") as f:
        content = f.read()
        
    if "gunicorn==22.0.0" in content:
        print("✓ gunicorn is at secure version (22.0.0)")
        return True
    elif "gunicorn==21.2.0" in content:
        print("✗ gunicorn is still at vulnerable version (21.2.0)")
        return False
    else:
        print("⚠ gunicorn version unknown")
        return False


def test_security_files_exist():
    """Test that security documentation files exist"""
    print("\nTest 5: Checking security documentation...")
    
    required_files = [
        ".env.example",
        "SECURITY.md"
    ]
    
    all_exist = True
    for file in required_files:
        path = os.path.join("/home/runner/work/MelodySearch/MelodySearch", file)
        if os.path.exists(path):
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} is missing")
            all_exist = False
    
    return all_exist


def main():
    print("=" * 60)
    print("Security Validation Tests")
    print("=" * 60)
    
    tests = [
        test_missing_secret_key,
        test_missing_spotify_credentials,
        test_no_hardcoded_credentials,
        test_gunicorn_version,
        test_security_files_exist
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("✓ All security tests passed!")
        return 0
    else:
        print("✗ Some security tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
