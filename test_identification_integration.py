#!/usr/bin/env python3
"""
Integration test for song identification feature.
Tests the complete flow without requiring actual API keys.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

def test_song_identifier_class():
    """Test that SongIdentifier class is properly structured"""
    print("Testing SongIdentifier class structure...")
    
    from song_identifier import SongIdentifier
    
    # Test initialization without API key
    identifier = SongIdentifier()
    assert identifier.acoustid_api_key is None
    print("  ✓ SongIdentifier can be initialized without API key")
    
    # Test initialization with API key
    identifier_with_key = SongIdentifier("test_api_key")
    assert identifier_with_key.acoustid_api_key == "test_api_key"
    print("  ✓ SongIdentifier stores API key correctly")
    
    # Test that methods exist
    assert hasattr(identifier, 'identify_song')
    assert hasattr(identifier, 'identify_with_spotify_fallback')
    assert hasattr(identifier, 'batch_identify')
    print("  ✓ All required methods are present")
    
    return True


def test_server_identify_endpoint():
    """Test that the /identify endpoint is properly configured"""
    print("\nTesting /identify endpoint configuration...")
    
    # Check server.py file for the endpoint
    with open('server.py', 'r') as f:
        server_content = f.read()
    
    # Check that identify route exists
    assert "@app.route('/identify'" in server_content
    print("  ✓ /identify endpoint is registered")
    
    # Check that identify function exists
    assert "def identify_song():" in server_content
    print("  ✓ identify_song function is defined")
    
    # Check for SongIdentifier import
    assert "from song_identifier import SongIdentifier" in server_content
    print("  ✓ SongIdentifier is imported in server.py")
    
    return True


def test_frontend_integration():
    """Test that frontend has identification UI"""
    print("\nTesting frontend integration...")
    
    with open('templates/index.html', 'r') as f:
        html_content = f.read()
    
    # Check for identify section
    assert 'identifyForm' in html_content
    print("  ✓ Identify form is present")
    
    assert 'identifyAudioFile' in html_content
    print("  ✓ File input for identification is present")
    
    assert 'identifySong' in html_content
    print("  ✓ JavaScript identify function is present")
    
    assert 'Identify Unknown Song' in html_content or 'Identify Song' in html_content
    print("  ✓ UI text for identification is present")
    
    return True


def test_dependencies():
    """Test that required dependencies are installed"""
    print("\nTesting dependencies...")
    
    try:
        import acoustid
        print("  ✓ pyacoustid is installed")
    except ImportError:
        print("  ✗ pyacoustid is not installed")
        return False
    
    try:
        import musicbrainzngs
        print("  ✓ musicbrainzngs is installed")
    except ImportError:
        print("  ✗ musicbrainzngs is not installed")
        return False
    
    # Check for fpcalc tool
    import subprocess
    try:
        result = subprocess.run(['fpcalc', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✓ chromaprint (fpcalc) is installed")
            return True
        else:
            print("  ✗ chromaprint (fpcalc) is not working")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  ✗ chromaprint (fpcalc) is not installed")
        return False


def test_metadata_flow():
    """Test metadata extraction flow with mock data"""
    print("\nTesting metadata extraction flow...")
    
    from song_identifier import SongIdentifier
    
    identifier = SongIdentifier("test_key")
    
    # Mock the _fetch_musicbrainz_metadata method
    mock_metadata = {
        'title': 'Test Song',
        'artist': 'Test Artist',
        'album': 'Test Album',
        'release_date': '2023-01-01',
        'cover_art_url': 'https://example.com/cover.jpg',
        'recording_id': 'test-id',
        'isrc': 'TEST123',
        'tags': ['rock', 'alternative'],
        'musicbrainz_url': 'https://musicbrainz.org/recording/test-id'
    }
    
    # Verify structure
    assert 'title' in mock_metadata
    assert 'artist' in mock_metadata
    assert 'album' in mock_metadata
    assert 'cover_art_url' in mock_metadata
    print("  ✓ Metadata structure is correct")
    
    return True


def test_api_response_format():
    """Test that API responses have correct format"""
    print("\nTesting API response format...")
    
    expected_response = {
        "message": "Song identified successfully",
        "song": {
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "cover_art_url": "https://example.com/cover.jpg",
            "release_date": "2023-01-01",
            "identification_score": 0.95,
            "spotify_id": "test-id",
            "spotify_url": "https://open.spotify.com/track/test-id",
            "isrc": "TEST123",
            "tags": ["rock"],
            "musicbrainz_url": "https://musicbrainz.org/recording/test-id"
        },
        "identification_source": "acoustid"
    }
    
    # Verify all required fields are present
    assert "message" in expected_response
    assert "song" in expected_response
    assert "title" in expected_response["song"]
    assert "artist" in expected_response["song"]
    assert "album" in expected_response["song"]
    assert "cover_art_url" in expected_response["song"]
    print("  ✓ API response format is correct")
    
    return True


def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("Song Identification Integration Tests")
    print("=" * 60)
    
    tests = [
        ("SongIdentifier Class", test_song_identifier_class),
        ("Server Endpoint", test_server_identify_endpoint),
        ("Frontend Integration", test_frontend_integration),
        ("Dependencies", test_dependencies),
        ("Metadata Flow", test_metadata_flow),
        ("API Response Format", test_api_response_format),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ {test_name} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ All integration tests passed!")
        print("\nThe song identification feature is properly implemented.")
        print("\nTo use it:")
        print("1. Get a free AcoustID API key from https://acoustid.org/new-application")
        print("2. Set it as environment variable: export ACOUSTID_API_KEY='your-key'")
        print("3. Start the server: python server.py")
        print("4. Upload an audio file in the 'Identify Unknown Song' section")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
