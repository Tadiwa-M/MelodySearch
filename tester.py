# spotify_api_test.py - Test what Spotify APIs actually work
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import logging

# Your credentials
SPOTIFY_CLIENT_ID = '9818b6e351d84e1ab29bf345fa7ee898'
SPOTIFY_CLIENT_SECRET = '3dc0f649da4b4bd1bf30966ea4f3f49e'
SPOTIFY_REDIRECT_URI = 'http://127.0.0.1:5000/callback'
SCOPE = 'user-read-private user-read-email'

logging.basicConfig(level=logging.DEBUG)


def test_spotify_apis():
    """Test which Spotify APIs are actually working"""

    # Initialize Spotify client
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path='.cache'
    )

    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Test track: Hangman by Dave
    track_id = '7r7NTwtWAhPRtzylDu3hnE'  # From your logs

    print("=" * 60)
    print("TESTING SPOTIFY APIs")
    print("=" * 60)

    # Test 1: Basic track info
    print("\n1. BASIC TRACK INFO:")
    try:
        track = sp.track(track_id)
        print(f"✓ Track: {track['name']} by {track['artists'][0]['name']}")
        print(f"  Duration: {track['duration_ms']}ms")
        print(f"  Popularity: {track['popularity']}")
        print(f"  Preview URL: {track.get('preview_url', 'None')}")
    except Exception as e:
        print(f"✗ Basic track info failed: {e}")

    # Test 2: Audio Features (the old deprecated one)
    print("\n2. AUDIO FEATURES (deprecated):")
    try:
        features = sp.audio_features([track_id])[0]
        if features:
            print("✓ Audio Features still works!")
            print(f"  Tempo: {features['tempo']} BPM")
            print(f"  Key: {features['key']}")
            print(f"  Mode: {features['mode']} ({'Major' if features['mode'] == 1 else 'Minor'})")
            print(f"  Energy: {features['energy']}")
            print(f"  Valence: {features['valence']}")
            print(f"  Danceability: {features['danceability']}")
            print(f"  Acousticness: {features['acousticness']}")
        else:
            print("✗ Audio Features returned None")
    except Exception as e:
        print(f"✗ Audio Features failed: {e}")

    # Test 3: Audio Analysis (the detailed one)
    print("\n3. AUDIO ANALYSIS (detailed):")
    try:
        analysis = sp.audio_analysis(track_id)
        print("✓ Audio Analysis works!")

        track_info = analysis['track']
        print(f"  Tempo: {track_info['tempo']} BPM")
        print(f"  Key: {track_info['key']}")
        print(f"  Mode: {track_info['mode']} ({'Major' if track_info['mode'] == 1 else 'Minor'})")
        print(f"  Time Signature: {track_info['time_signature']}/4")
        print(f"  Loudness: {track_info['loudness']} dB")
        print(f"  Duration: {track_info['duration']} seconds")

        print(f"  Beats: {len(analysis['beats'])} beat markers")
        print(f"  Sections: {len(analysis['sections'])} sections")
        print(f"  Segments: {len(analysis['segments'])} segments")

        # Show first segment for timbral/pitch data
        if analysis['segments']:
            seg = analysis['segments'][0]
            print(f"  First segment timbral features: {len(seg['timbre'])} dimensions")
            print(f"  First segment pitch features: {len(seg['pitches'])} dimensions")

    except Exception as e:
        print(f"✗ Audio Analysis failed: {e}")

    # Test 4: Try a popular song that should have all data
    print("\n4. TESTING POPULAR SONG (Blinding Lights):")
    try:
        search_results = sp.search(q='Blinding Lights The Weeknd', type='track', limit=1)
        if search_results['tracks']['items']:
            popular_track = search_results['tracks']['items'][0]
            popular_id = popular_track['id']

            print(f"✓ Found: {popular_track['name']} by {popular_track['artists'][0]['name']}")
            print(f"  Preview URL: {popular_track.get('preview_url', 'None')}")

            # Test audio features on popular song
            try:
                pop_features = sp.audio_features([popular_id])[0]
                if pop_features:
                    print(f"  ✓ Has audio features - Tempo: {pop_features['tempo']} BPM")
                else:
                    print("  ✗ No audio features")
            except Exception as e:
                print(f"  ✗ Audio features failed: {e}")

            # Test audio analysis on popular song
            try:
                pop_analysis = sp.audio_analysis(popular_id)
                print(f"  ✓ Has audio analysis - {len(pop_analysis['segments'])} segments")
            except Exception as e:
                print(f"  ✗ Audio analysis failed: {e}")

    except Exception as e:
        print(f"✗ Popular song test failed: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_spotify_apis()