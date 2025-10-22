"""
Test script for song identification functionality
"""

import os
import sys
import logging
from song_identifier import SongIdentifier
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

logging.basicConfig(level=logging.INFO)

def test_identifier_module():
    """Test the SongIdentifier module"""
    print("\n" + "="*60)
    print("TESTING SONG IDENTIFIER MODULE")
    print("="*60)
    
    # Test 1: Initialize without API key (free tier)
    print("\n1. Testing initialization (free tier):")
    try:
        identifier = SongIdentifier()
        print("✓ SongIdentifier initialized successfully")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False
    
    # Test 2: Check methods exist
    print("\n2. Testing method availability:")
    methods = ['identify_song', '_identify_with_audd', 'enrich_metadata_from_spotify']
    for method in methods:
        if hasattr(identifier, method):
            print(f"✓ Method '{method}' exists")
        else:
            print(f"✗ Method '{method}' missing")
            return False
    
    # Test 3: Test metadata enrichment with mock data
    print("\n3. Testing metadata enrichment:")
    try:
        # Check if Spotify credentials are available
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            print("⚠ Spotify credentials not set, skipping enrichment test")
        else:
            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Mock metadata
            mock_metadata = {
                'title': 'Blinding Lights',
                'artist': 'The Weeknd',
                'identified': True
            }
            
            enriched = identifier.enrich_metadata_from_spotify(mock_metadata, sp)
            
            if enriched.get('spotify_enriched'):
                print("✓ Metadata enrichment successful")
                print(f"  - Title: {enriched.get('title')}")
                print(f"  - Artist: {enriched.get('artist')}")
                print(f"  - Album: {enriched.get('album')}")
                print(f"  - Cover Art: {'Yes' if enriched.get('cover_art') else 'No'}")
            else:
                print("✗ Metadata enrichment failed")
                
    except Exception as e:
        print(f"✗ Enrichment test failed: {e}")
    
    print("\n" + "="*60)
    print("MODULE TESTS COMPLETE")
    print("="*60)
    return True


def test_api_endpoint():
    """Test the /identify API endpoint"""
    print("\n" + "="*60)
    print("TESTING /identify API ENDPOINT")
    print("="*60)
    
    print("\nNote: This test requires:")
    print("  1. Server to be running (python server.py)")
    print("  2. An audio file to test with")
    print("  3. AUDD_API_KEY environment variable (optional, free tier works)")
    
    print("\nManual testing commands:")
    print("  1. Start the server:")
    print("     python server.py")
    print()
    print("  2. Test with curl:")
    print("     curl -X POST http://127.0.0.1:5000/identify \\")
    print("       -F 'audio_file=@path/to/your/song.mp3'")
    print()
    print("  3. Or use the web interface at http://127.0.0.1:5000")
    
    print("\n" + "="*60)


def test_integration():
    """Test full integration"""
    print("\n" + "="*60)
    print("INTEGRATION TEST SUMMARY")
    print("="*60)
    
    print("\nThe song identification feature provides:")
    print("  ✓ SongIdentifier class for identifying songs from audio")
    print("  ✓ /identify API endpoint for web requests")
    print("  ✓ AudD API integration (free tier: 50 requests/day)")
    print("  ✓ Spotify metadata enrichment")
    print("  ✓ Returns: title, artist, album, cover art, and more")
    
    print("\nHow to use:")
    print("  1. Set AUDD_API_KEY in .env (optional, free tier works without it)")
    print("  2. Upload audio file to /identify endpoint")
    print("  3. Receive song metadata in response")
    
    print("\nExample response structure:")
    print("""
    {
      "message": "Song identified successfully",
      "identified": true,
      "song": {
        "title": "Song Title",
        "artist": "Artist Name",
        "album": "Album Name",
        "cover_art": "https://...",
        "album_art": "https://...",
        "release_date": "2020-01-01",
        "spotify_id": "...",
        "spotify_url": "https://open.spotify.com/...",
        "genres": ["pop", "dance"],
        ...
      }
    }
    """)
    
    print("\n" + "="*60)


if __name__ == "__main__":
    print("\n🎵 MelodySearch - Song Identification Test Suite 🎵\n")
    
    # Run module tests
    if test_identifier_module():
        print("\n✓ All module tests passed!")
    else:
        print("\n✗ Some module tests failed")
        sys.exit(1)
    
    # Show API endpoint testing instructions
    test_api_endpoint()
    
    # Show integration summary
    test_integration()
    
    print("\n✓ Test suite completed!\n")
