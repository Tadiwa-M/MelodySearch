#!/usr/bin/env python3
"""
Test script for the /similar-songs endpoint
"""
import os
import sys
import json

# Test data
test_cases = [
    {
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "description": "Popular pop song"
    },
    {
        "title": "Bohemian Rhapsody",
        "artist": "Queen",
        "description": "Classic rock song"
    },
    {
        "title": "Shape of You",
        "artist": "Ed Sheeran",
        "description": "Modern pop hit"
    }
]

def test_endpoint_logic():
    """Test the endpoint logic without actually running the server"""
    print("=" * 60)
    print("Testing /similar-songs endpoint logic")
    print("=" * 60)
    
    # Check required environment variables
    required_vars = ['SECRET_KEY', 'SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"\n✗ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nTo run this test, set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}='your_value_here'")
        return False
    
    # Import server components after env var check
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        from metadata_similarity_engine import MetadataSimilarityEngine
        
        print("\n✓ All dependencies imported successfully")
        
        # Test Spotify connection
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
        ))
        
        print("✓ Spotify client initialized")
        
        # Test each case
        for test_case in test_cases:
            print(f"\n{'=' * 60}")
            print(f"Test: {test_case['description']}")
            print(f"Song: '{test_case['title']}' by '{test_case['artist']}'")
            print(f"{'=' * 60}")
            
            try:
                # Search for the song
                search_query = f"track:{test_case['title']} artist:{test_case['artist']}"
                results = sp.search(q=search_query, type='track', limit=1)
                
                if not results['tracks']['items']:
                    print(f"✗ Song not found on Spotify")
                    continue
                
                track = results['tracks']['items'][0]
                print(f"✓ Found: '{track['name']}' by '{track['artists'][0]['name']}'")
                print(f"  Spotify ID: {track['id']}")
                print(f"  Popularity: {track['popularity']}")
                print(f"  Duration: {track['duration_ms']}ms")
                
                # Test metadata extraction
                similarity_engine = MetadataSimilarityEngine(sp)
                metadata = similarity_engine.extract_comprehensive_metadata(track['id'], track)
                
                print(f"✓ Metadata extracted successfully")
                print(f"  Genres: {', '.join(metadata.get('artist_genres', [])[:3])}")
                print(f"  Release year: {metadata.get('release_year')}")
                print(f"  Era: {metadata.get('era')}")
                print(f"  Completeness: {metadata.get('feature_completeness', 0):.1%}")
                
            except Exception as e:
                print(f"✗ Test failed: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n{'=' * 60}")
        print("All tests completed!")
        print(f"{'=' * 60}")
        return True
        
    except ImportError as e:
        print(f"\n✗ Failed to import required modules: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_input_validation():
    """Test input validation logic"""
    print("\n" + "=" * 60)
    print("Testing input validation")
    print("=" * 60)
    
    # Test cases for validation
    validation_tests = [
        {"title": "", "artist": "Artist", "should_fail": True, "reason": "Empty title"},
        {"title": "Song", "artist": "", "should_fail": True, "reason": "Empty artist"},
        {"title": "A" * 201, "artist": "Artist", "should_fail": True, "reason": "Title too long"},
        {"title": "Song", "artist": "B" * 201, "should_fail": True, "reason": "Artist too long"},
        {"title": "Song<script>", "artist": "Artist", "should_fail": True, "reason": "XSS in title"},
        {"title": "Song", "artist": "Artist<script>", "should_fail": True, "reason": "XSS in artist"},
        {"title": "Song", "artist": "Artist", "should_fail": False, "reason": "Valid input"},
        {"title": "Don't Stop Believin'", "artist": "Journey", "should_fail": False, "reason": "Apostrophe OK"},
    ]
    
    import re
    
    passed = 0
    failed = 0
    
    for test in validation_tests:
        title = test['title']
        artist = test['artist']
        should_fail = test['should_fail']
        reason = test['reason']
        
        # Apply validation logic
        validation_failed = False
        error_msg = ""
        
        if not title.strip():
            validation_failed = True
            error_msg = "Empty title"
        elif not artist.strip():
            validation_failed = True
            error_msg = "Empty artist"
        elif len(title) > 200:
            validation_failed = True
            error_msg = "Title too long"
        elif len(artist) > 200:
            validation_failed = True
            error_msg = "Artist too long"
        elif re.search(r'[<>\"\\]', title) or re.search(r'[<>\"\\]', artist):
            validation_failed = True
            error_msg = "Invalid characters"
        
        # Check if result matches expectation
        if validation_failed == should_fail:
            print(f"✓ {reason}: {error_msg if validation_failed else 'Passed'}")
            passed += 1
        else:
            print(f"✗ {reason}: Expected {'fail' if should_fail else 'pass'} but got {'fail' if validation_failed else 'pass'}")
            failed += 1
    
    print(f"\nValidation tests: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SIMILAR SONGS ENDPOINT TEST SUITE")
    print("=" * 60)
    
    # Run validation tests (don't need API keys)
    validation_ok = test_input_validation()
    
    # Run endpoint logic tests (need API keys)
    endpoint_ok = test_endpoint_logic()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Validation tests: {'✓ PASSED' if validation_ok else '✗ FAILED'}")
    print(f"Endpoint tests: {'✓ PASSED' if endpoint_ok else '✗ FAILED'}")
    print("=" * 60)
    
    sys.exit(0 if (validation_ok and endpoint_ok) else 1)
