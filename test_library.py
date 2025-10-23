#!/usr/bin/env python3
"""
Tests for library management functionality
"""
import os
import sys
import json
import tempfile
import shutil

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

import library_manager


def setup_test_environment():
    """Create a temporary directory for test data"""
    test_dir = tempfile.mkdtemp(prefix='melody_library_test_')
    
    # Override library paths to use test directory
    library_manager.LIBRARY_DIR = test_dir
    library_manager.LIBRARY_SONGS_PATH = os.path.join(test_dir, 'library_songs.json')
    library_manager.COLLECTIONS_PATH = os.path.join(test_dir, 'collections.json')
    
    return test_dir


def cleanup_test_environment(test_dir):
    """Remove temporary test directory"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


def test_add_song_to_library():
    """Test adding a song to the library"""
    print("\nTest: Add song to library")
    
    song_data = {
        'title': 'Test Song',
        'artist': 'Test Artist',
        'audio_features': {'tempo': 120, 'energy': 0.8},
        'spotify_id': 'test_spotify_id_123'
    }
    
    result = library_manager.add_song_to_library(song_data)
    
    assert result['success'], "Failed to add song"
    assert 'song_id' in result, "No song_id returned"
    print(f"✓ Song added with ID: {result['song_id']}")
    
    # Try adding duplicate
    result2 = library_manager.add_song_to_library(song_data)
    assert not result2['success'], "Duplicate song should not be added"
    print("✓ Duplicate song rejected correctly")
    
    return True


def test_get_library_songs():
    """Test retrieving library songs"""
    print("\nTest: Get library songs")
    
    # Add multiple songs
    for i in range(3):
        song_data = {
            'title': f'Song {i}',
            'artist': f'Artist {i}',
            'audio_features': {'tempo': 100 + i * 10},
            'spotify_id': f'spotify_{i}'
        }
        library_manager.add_song_to_library(song_data)
    
    songs = library_manager.get_library_songs()
    assert len(songs) >= 3, f"Expected at least 3 songs, got {len(songs)}"
    print(f"✓ Retrieved {len(songs)} songs from library")
    
    # Test sorting
    songs_by_title = library_manager.get_library_songs(sort_by='title', order='asc')
    assert songs_by_title[0]['title'] <= songs_by_title[1]['title'], "Sorting by title failed"
    print("✓ Sorting works correctly")
    
    return True


def test_remove_song_from_library():
    """Test removing a song from library"""
    print("\nTest: Remove song from library")
    
    # Add a song
    song_data = {
        'title': 'To Be Removed',
        'artist': 'Test Artist',
        'audio_features': {'tempo': 120}
    }
    result = library_manager.add_song_to_library(song_data)
    song_id = result['song_id']
    
    # Remove it
    remove_result = library_manager.remove_song_from_library(song_id)
    assert remove_result['success'], "Failed to remove song"
    print(f"✓ Song {song_id} removed successfully")
    
    # Verify it's gone
    song = library_manager.get_song_by_id(song_id)
    assert song is None, "Song still exists after removal"
    print("✓ Song confirmed removed")
    
    return True


def test_create_collection():
    """Test creating a collection"""
    print("\nTest: Create collection")
    
    result = library_manager.create_collection('My Playlist', 'Test description')
    
    assert result['success'], "Failed to create collection"
    assert 'collection_id' in result, "No collection_id returned"
    print(f"✓ Collection created with ID: {result['collection_id']}")
    
    return True


def test_get_collections():
    """Test retrieving collections"""
    print("\nTest: Get collections")
    
    # Create multiple collections
    library_manager.create_collection('Collection 1')
    library_manager.create_collection('Collection 2')
    
    collections = library_manager.get_collections()
    assert len(collections) >= 2, f"Expected at least 2 collections, got {len(collections)}"
    print(f"✓ Retrieved {len(collections)} collections")
    
    return True


def test_add_song_to_collection():
    """Test adding songs to a collection"""
    print("\nTest: Add song to collection")
    
    # Create a song and collection
    song_data = {
        'title': 'Collection Song',
        'artist': 'Collection Artist',
        'audio_features': {'tempo': 125}
    }
    song_result = library_manager.add_song_to_library(song_data)
    song_id = song_result['song_id']
    
    collection_result = library_manager.create_collection('Test Collection')
    collection_id = collection_result['collection_id']
    
    # Add song to collection
    add_result = library_manager.add_song_to_collection(collection_id, song_id)
    assert add_result['success'], "Failed to add song to collection"
    print(f"✓ Song added to collection")
    
    # Verify song is in collection
    collection = library_manager.get_collection_with_songs(collection_id)
    assert len(collection['songs']) == 1, "Song not in collection"
    assert collection['songs'][0]['id'] == song_id, "Wrong song in collection"
    print("✓ Song verified in collection")
    
    # Try adding duplicate
    dup_result = library_manager.add_song_to_collection(collection_id, song_id)
    assert not dup_result['success'], "Duplicate song should not be added to collection"
    print("✓ Duplicate song rejected correctly")
    
    return True


def test_remove_song_from_collection():
    """Test removing a song from a collection"""
    print("\nTest: Remove song from collection")
    
    # Setup
    song_data = {'title': 'Remove Test', 'artist': 'Test'}
    song_result = library_manager.add_song_to_library(song_data)
    song_id = song_result['song_id']
    
    collection_result = library_manager.create_collection('Remove Test Collection')
    collection_id = collection_result['collection_id']
    
    library_manager.add_song_to_collection(collection_id, song_id)
    
    # Remove song from collection
    remove_result = library_manager.remove_song_from_collection(collection_id, song_id)
    assert remove_result['success'], "Failed to remove song from collection"
    print("✓ Song removed from collection")
    
    # Verify it's gone
    collection = library_manager.get_collection_with_songs(collection_id)
    assert len(collection['songs']) == 0, "Song still in collection"
    print("✓ Song confirmed removed from collection")
    
    return True


def test_delete_collection():
    """Test deleting a collection"""
    print("\nTest: Delete collection")
    
    result = library_manager.create_collection('To Delete')
    collection_id = result['collection_id']
    
    delete_result = library_manager.delete_collection(collection_id)
    assert delete_result['success'], "Failed to delete collection"
    print(f"✓ Collection {collection_id} deleted")
    
    # Verify it's gone
    collection = library_manager.get_collection_by_id(collection_id)
    assert collection is None, "Collection still exists after deletion"
    print("✓ Collection confirmed deleted")
    
    return True


def test_update_collection():
    """Test updating collection metadata"""
    print("\nTest: Update collection")
    
    result = library_manager.create_collection('Original Name', 'Original Desc')
    collection_id = result['collection_id']
    
    update_result = library_manager.update_collection(
        collection_id,
        name='Updated Name',
        description='Updated Description'
    )
    
    assert update_result['success'], "Failed to update collection"
    print("✓ Collection updated")
    
    # Verify update
    collection = library_manager.get_collection_by_id(collection_id)
    assert collection['name'] == 'Updated Name', "Name not updated"
    assert collection['description'] == 'Updated Description', "Description not updated"
    print("✓ Updates verified")
    
    return True


def test_library_stats():
    """Test library statistics"""
    print("\nTest: Library statistics")
    
    stats = library_manager.get_library_stats()
    
    assert 'total_songs' in stats, "Missing total_songs"
    assert 'total_collections' in stats, "Missing total_collections"
    assert isinstance(stats['total_songs'], int), "total_songs not an integer"
    
    print(f"✓ Stats: {stats['total_songs']} songs, {stats['total_collections']} collections")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Library Management Tests")
    print("=" * 60)
    
    test_dir = None
    
    try:
        # Setup test environment
        test_dir = setup_test_environment()
        print(f"Test directory: {test_dir}")
        
        # Run tests
        tests = [
            test_add_song_to_library,
            test_get_library_songs,
            test_remove_song_from_library,
            test_create_collection,
            test_get_collections,
            test_add_song_to_collection,
            test_remove_song_from_collection,
            test_delete_collection,
            test_update_collection,
            test_library_stats
        ]
        
        results = []
        for test_func in tests:
            try:
                result = test_func()
                results.append(result)
            except AssertionError as e:
                print(f"✗ Test failed: {e}")
                results.append(False)
            except Exception as e:
                print(f"✗ Test error: {e}")
                results.append(False)
        
        print("\n" + "=" * 60)
        print(f"Results: {sum(results)}/{len(results)} tests passed")
        print("=" * 60)
        
        if all(results):
            print("✓ All tests passed!")
            return 0
        else:
            print("✗ Some tests failed")
            return 1
    
    finally:
        # Cleanup
        if test_dir:
            cleanup_test_environment(test_dir)
            print(f"\nCleaned up test directory")


if __name__ == '__main__':
    sys.exit(main())
