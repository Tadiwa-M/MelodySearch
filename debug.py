import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Your credentials - MUST be set via environment variables
import os

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5000/callback')
SCOPE = 'user-read-private user-read-email'

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables must be set")


def test_spotify_endpoints():
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path='.cache'
    )

    sp = spotipy.Spotify(auth_manager=auth_manager)

    try:
        # Test 1: Search (this works)
        print("Testing search...")
        results = sp.search(q='mr brightside', type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            track_id = track['id']
            print(f"✅ Search works: {track['name']} by {track['artists'][0]['name']}")

            # Test 2: Audio features (this fails)
            print(f"Testing audio features for track ID: {track_id}")
            try:
                audio_features = sp.audio_features([track_id])
                print(f"✅ Audio features work: {audio_features}")
            except spotipy.SpotifyException as e:
                print(f"❌ Audio features failed: {e}")
                print(f"HTTP Status: {e.http_status}")
                print(f"Response: {e.msg}")

            # Test 3: Try a different popular track
            print("\nTrying with a different track...")
            try:
                # Use a very popular track ID that definitely should work
                popular_track_id = '4iV5W9uYEdYUVa79Axb7Rh'  # Never Gonna Give You Up
                audio_features2 = sp.audio_features([popular_track_id])
                print(f"✅ Audio features work for popular track: {audio_features2}")
            except spotipy.SpotifyException as e:
                print(f"❌ Audio features failed for popular track too: {e}")

            # Test 4: Try without the array (single track)
            print("\nTrying single track (not array)...")
            try:
                audio_features3 = sp.audio_features(track_id)
                print(f"✅ Single audio features work: {audio_features3}")
            except spotipy.SpotifyException as e:
                print(f"❌ Single audio features failed: {e}")

    except Exception as e:
        print(f"General error: {e}")


if __name__ == "__main__":
    test_spotify_endpoints()