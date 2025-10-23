#!/usr/bin/env python3
"""
Example usage of the /similar-songs endpoint

This script demonstrates how to use the MelodySearch API to find similar songs.
Run the Flask server before executing this script:
    python server.py

Then run this script:
    python example_usage.py
"""

import requests
import json

# Base URL of the MelodySearch API
BASE_URL = "http://127.0.0.1:5000"


def find_similar_songs(title, artist):
    """
    Find songs similar to the given title and artist.
    
    Args:
        title (str): Song title
        artist (str): Artist name
        
    Returns:
        dict: Response containing original song and similar songs
    """
    url = f"{BASE_URL}/similar-songs"
    data = {
        "title": title,
        "artist": artist
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None


def print_song_info(song, is_original=False):
    """Print formatted song information"""
    prefix = "🎵 ORIGINAL" if is_original else "  ✓ Similar"
    
    print(f"\n{prefix}: {song['title']}")
    print(f"    Artist: {song['artist']}")
    print(f"    Album: {song.get('album', 'Unknown')}")
    print(f"    Release: {song.get('release_date', 'Unknown')}")
    print(f"    Popularity: {song.get('popularity', 0)}/100")
    
    if song.get('genres'):
        print(f"    Genres: {', '.join(song['genres'][:3])}")
    
    if not is_original and song.get('similarity_score'):
        print(f"    Similarity: {song['similarity_score']:.1%}")
        if song.get('similarity_explanation'):
            print(f"    Why: {song['similarity_explanation']}")
    
    # Audio features
    if song.get('audio_features'):
        features = song['audio_features']
        print(f"    Tempo: {features.get('tempo', 0)} BPM")
        print(f"    Energy: {features.get('energy', 0):.2f}")
        print(f"    Danceability: {features.get('danceability', 0):.2f}")


def example_1():
    """Example 1: Find songs similar to a popular modern pop song"""
    print("=" * 70)
    print("EXAMPLE 1: Popular Modern Pop Song")
    print("=" * 70)
    
    result = find_similar_songs("Blinding Lights", "The Weeknd")
    
    if result:
        print_song_info(result['original_song'], is_original=True)
        
        print(f"\n📊 Found {result['total_matches']} similar songs:\n")
        for song in result['similar_songs'][:5]:  # Show top 5
            print_song_info(song)
    else:
        print("Failed to get results. Make sure the server is running!")


def example_2():
    """Example 2: Find songs similar to a classic rock song"""
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: Classic Rock Song")
    print("=" * 70)
    
    result = find_similar_songs("Bohemian Rhapsody", "Queen")
    
    if result:
        print_song_info(result['original_song'], is_original=True)
        
        print(f"\n📊 Found {result['total_matches']} similar songs:\n")
        for song in result['similar_songs'][:5]:  # Show top 5
            print_song_info(song)
    else:
        print("Failed to get results. Make sure the server is running!")


def example_3():
    """Example 3: Find songs similar to a hip-hop track"""
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: Hip-Hop Track")
    print("=" * 70)
    
    result = find_similar_songs("HUMBLE.", "Kendrick Lamar")
    
    if result:
        print_song_info(result['original_song'], is_original=True)
        
        print(f"\n📊 Found {result['total_matches']} similar songs:\n")
        for song in result['similar_songs'][:5]:  # Show top 5
            print_song_info(song)
    else:
        print("Failed to get results. Make sure the server is running!")


def example_custom():
    """Example: Custom song search"""
    print("\n\n" + "=" * 70)
    print("CUSTOM SEARCH")
    print("=" * 70)
    
    title = input("\nEnter song title: ").strip()
    artist = input("Enter artist name: ").strip()
    
    if not title or not artist:
        print("Both title and artist are required!")
        return
    
    result = find_similar_songs(title, artist)
    
    if result:
        print_song_info(result['original_song'], is_original=True)
        
        print(f"\n📊 Found {result['total_matches']} similar songs:\n")
        for song in result['similar_songs']:
            print_song_info(song)
    else:
        print("Failed to get results. Make sure the server is running!")


def main():
    """Main function"""
    print("\n" + "🎵" * 35)
    print("   MelodySearch - Similar Songs API Examples")
    print("🎵" * 35)
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL, timeout=5)
        print("\n✓ Server is running!")
    except requests.exceptions.RequestException:
        print("\n✗ Server is not running!")
        print("\nPlease start the server first:")
        print("    python server.py")
        print("\nThen run this script again:")
        print("    python example_usage.py")
        return
    
    # Run examples
    example_1()
    example_2()
    example_3()
    
    # Interactive example
    print("\n\n" + "=" * 70)
    print("Want to try your own song? (yes/no): ", end="")
    response = input().strip().lower()
    if response in ['yes', 'y']:
        example_custom()
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
