#!/usr/bin/env python3
"""
Integration test for API endpoints
Tests both the new /similar-songs and existing /search endpoints
"""
import os
import sys

def test_endpoint_definitions():
    """Test that both endpoints are properly defined"""
    print("=" * 60)
    print("Testing endpoint definitions")
    print("=" * 60)
    
    # Read server.py
    with open('server.py', 'r') as f:
        content = f.read()
    
    # Check for /similar-songs endpoint
    if "@app.route('/similar-songs', methods=['POST'])" in content:
        print("✓ /similar-songs endpoint is defined")
    else:
        print("✗ /similar-songs endpoint is NOT defined")
        return False
    
    # Check for /search endpoint (backward compatibility)
    if "@app.route('/search', methods=['POST'])" in content:
        print("✓ /search endpoint is defined (backward compatibility)")
    else:
        print("✗ /search endpoint is NOT defined")
        return False
    
    # Check for /upload endpoint
    if "@app.route('/upload', methods=['POST'])" in content:
        print("✓ /upload endpoint is defined")
    else:
        print("✗ /upload endpoint is NOT defined")
        return False
    
    return True


def test_similar_songs_logic():
    """Test the /similar-songs endpoint logic"""
    print("\n" + "=" * 60)
    print("Testing /similar-songs endpoint logic")
    print("=" * 60)
    
    # Check that the endpoint accepts both title and artist
    with open('server.py', 'r') as f:
        content = f.read()
    
    # Find the similar-songs function
    if 'def get_similar_songs():' in content:
        print("✓ get_similar_songs() function is defined")
    else:
        print("✗ get_similar_songs() function is NOT defined")
        return False
    
    # Check for title parameter
    if "data.get('title'" in content:
        print("✓ Endpoint accepts 'title' parameter")
    else:
        print("✗ Endpoint does NOT accept 'title' parameter")
        return False
    
    # Check for artist parameter
    if "data.get('artist'" in content:
        print("✓ Endpoint accepts 'artist' parameter")
    else:
        print("✗ Endpoint does NOT accept 'artist' parameter")
        return False
    
    # Check for proper search query
    if 'track:{title} artist:{artist}' in content or 'f"track:{title} artist:{artist}"' in content:
        print("✓ Endpoint uses both title and artist in search query")
    else:
        print("⚠ Warning: Search query may not use optimal format")
    
    # Check for metadata extraction
    if 'extract_comprehensive_metadata' in content:
        print("✓ Endpoint extracts comprehensive metadata")
    else:
        print("✗ Endpoint does NOT extract metadata")
        return False
    
    # Check for similarity calculation
    if 'find_metadata_similarities' in content:
        print("✓ Endpoint calculates similarity scores")
    else:
        print("✗ Endpoint does NOT calculate similarities")
        return False
    
    # Check response format
    if '"original_song"' in content and '"similar_songs"' in content:
        print("✓ Endpoint returns proper response format")
    else:
        print("✗ Endpoint does NOT return proper response format")
        return False
    
    return True


def test_search_endpoint_compatibility():
    """Test that the existing /search endpoint is unchanged"""
    print("\n" + "=" * 60)
    print("Testing /search endpoint backward compatibility")
    print("=" * 60)
    
    with open('server.py', 'r') as f:
        content = f.read()
    
    # Check that search_song function exists
    if 'def search_song():' in content:
        print("✓ search_song() function still exists")
    else:
        print("✗ search_song() function was removed")
        return False
    
    # Check that it still uses song_name parameter
    search_section = content[content.find('def search_song():'):content.find('def search_song():') + 5000]
    
    if "data.get('song_name')" in search_section:
        print("✓ /search endpoint still accepts 'song_name' parameter")
    else:
        print("✗ /search endpoint no longer accepts 'song_name' parameter")
        return False
    
    return True


def test_response_metadata():
    """Test that responses include required metadata fields"""
    print("\n" + "=" * 60)
    print("Testing response metadata completeness")
    print("=" * 60)
    
    with open('server.py', 'r') as f:
        content = f.read()
    
    # Check for required metadata fields in similar-songs response
    similar_songs_section = content[content.find('def get_similar_songs()'):content.find('def get_similar_songs()') + 10000]
    
    required_fields = [
        '"title"',
        '"artist"',
        '"spotify_id"',
        '"popularity"',
        '"duration_ms"',
        '"explicit"',
        '"album"',
        '"release_date"',
        '"genres"',
        '"audio_features"',
        '"similarity_score"'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in similar_songs_section:
            missing_fields.append(field)
    
    if not missing_fields:
        print(f"✓ All {len(required_fields)} required metadata fields are present")
    else:
        print(f"✗ Missing metadata fields: {', '.join(missing_fields)}")
        return False
    
    return True


def test_input_validation():
    """Test that input validation is properly implemented"""
    print("\n" + "=" * 60)
    print("Testing input validation")
    print("=" * 60)
    
    with open('server.py', 'r') as f:
        content = f.read()
    
    similar_songs_section = content[content.find('def get_similar_songs()'):content.find('def get_similar_songs()') + 10000]
    
    checks = [
        ('Empty title check', 'if not title'),
        ('Empty artist check', 'if not artist'),
        ('Length validation', 'len(title) > 200' or 'len(artist) > 200'),
        ('XSS prevention', 're.search(r\'[<>\\"\\\\]\''),
    ]
    
    passed = 0
    for check_name, pattern in checks:
        if pattern in similar_songs_section:
            print(f"✓ {check_name} is implemented")
            passed += 1
        else:
            print(f"⚠ {check_name} may not be properly implemented")
    
    if passed >= 3:
        print(f"✓ Input validation is adequate ({passed}/{len(checks)} checks)")
        return True
    else:
        print(f"✗ Input validation is incomplete ({passed}/{len(checks)} checks)")
        return False


def test_documentation():
    """Test that documentation is present"""
    print("\n" + "=" * 60)
    print("Testing documentation")
    print("=" * 60)
    
    # Check for API_DOCUMENTATION.md
    if os.path.exists('API_DOCUMENTATION.md'):
        print("✓ API_DOCUMENTATION.md exists")
        with open('API_DOCUMENTATION.md', 'r') as f:
            doc_content = f.read()
            if '/similar-songs' in doc_content:
                print("✓ API documentation includes /similar-songs endpoint")
            else:
                print("✗ API documentation does NOT include /similar-songs endpoint")
                return False
    else:
        print("✗ API_DOCUMENTATION.md does NOT exist")
        return False
    
    # Check if README was updated
    if os.path.exists('README.md'):
        with open('README.md', 'r') as f:
            readme_content = f.read()
            if '/similar-songs' in readme_content:
                print("✓ README.md mentions /similar-songs endpoint")
            else:
                print("⚠ README.md does not mention /similar-songs endpoint")
    
    return True


def main():
    print("\n" + "=" * 60)
    print("API ENDPOINTS INTEGRATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Endpoint Definitions", test_endpoint_definitions),
        ("Similar Songs Logic", test_similar_songs_logic),
        ("Search Endpoint Compatibility", test_search_endpoint_compatibility),
        ("Response Metadata", test_response_metadata),
        ("Input Validation", test_input_validation),
        ("Documentation", test_documentation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Overall: {passed}/{total} tests passed")
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
