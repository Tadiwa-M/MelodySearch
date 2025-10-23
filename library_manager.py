"""
Library Manager - Handles user's saved songs and collections/playlists
"""
import json
import os
import uuid
from datetime import datetime

# Library storage paths
LIBRARY_DIR = os.getenv('LIBRARY_PATH', os.path.join('Data', 'library'))
LIBRARY_SONGS_PATH = os.path.join(LIBRARY_DIR, 'library_songs.json')
COLLECTIONS_PATH = os.path.join(LIBRARY_DIR, 'collections.json')


def _ensure_library_dir():
    """Create library directory if it doesn't exist"""
    os.makedirs(LIBRARY_DIR, exist_ok=True)


def _load_json(path, default=None):
    """Load JSON file with error handling"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default if default is not None else []
    except json.JSONDecodeError:
        print(f"Warning: Corrupted file at {path}, returning default")
        return default if default is not None else []


def _save_json(path, data):
    """Save data to JSON file"""
    _ensure_library_dir()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# LIBRARY SONGS MANAGEMENT
# ============================================================================

def add_song_to_library(song_data):
    """
    Add a song to the user's library
    
    Args:
        song_data: dict containing song information (title, artist, audio_features, etc.)
        
    Returns:
        dict with success status and song_id
    """
    library_songs = _load_json(LIBRARY_SONGS_PATH)
    
    # Generate unique ID for the song
    song_id = str(uuid.uuid4())
    
    # Create library entry
    library_entry = {
        'id': song_id,
        'title': song_data.get('title', 'Unknown'),
        'artist': song_data.get('artist', 'Unknown'),
        'audio_features': song_data.get('audio_features', {}),
        'spotify_metadata': song_data.get('spotify_metadata', {}),
        'spotify_id': song_data.get('spotify_id') or song_data.get('spotify_metadata', {}).get('spotify_id'),
        'added_at': datetime.utcnow().isoformat(),
        'source': song_data.get('source', 'manual')  # 'manual', 'search_result', 'upload'
    }
    
    # Check for duplicates (by title and artist or spotify_id)
    spotify_id = library_entry.get('spotify_id')
    for existing_song in library_songs:
        if spotify_id and existing_song.get('spotify_id') == spotify_id:
            return {
                'success': False,
                'message': 'Song already in library',
                'song_id': existing_song['id']
            }
        if (existing_song.get('title') == library_entry['title'] and 
            existing_song.get('artist') == library_entry['artist']):
            return {
                'success': False,
                'message': 'Song already in library',
                'song_id': existing_song['id']
            }
    
    # Add to library
    library_songs.append(library_entry)
    _save_json(LIBRARY_SONGS_PATH, library_songs)
    
    return {
        'success': True,
        'message': 'Song added to library',
        'song_id': song_id
    }


def get_library_songs(sort_by='added_at', order='desc'):
    """
    Get all songs in the library
    
    Args:
        sort_by: field to sort by ('added_at', 'title', 'artist')
        order: 'asc' or 'desc'
        
    Returns:
        list of library songs
    """
    library_songs = _load_json(LIBRARY_SONGS_PATH)
    
    # Sort songs
    reverse = (order == 'desc')
    if sort_by == 'added_at':
        library_songs.sort(key=lambda x: x.get('added_at', ''), reverse=reverse)
    elif sort_by == 'title':
        library_songs.sort(key=lambda x: x.get('title', '').lower(), reverse=reverse)
    elif sort_by == 'artist':
        library_songs.sort(key=lambda x: x.get('artist', '').lower(), reverse=reverse)
    
    return library_songs


def remove_song_from_library(song_id):
    """
    Remove a song from the library
    
    Args:
        song_id: ID of the song to remove
        
    Returns:
        dict with success status
    """
    library_songs = _load_json(LIBRARY_SONGS_PATH)
    
    # Find and remove song
    original_count = len(library_songs)
    library_songs = [s for s in library_songs if s.get('id') != song_id]
    
    if len(library_songs) < original_count:
        _save_json(LIBRARY_SONGS_PATH, library_songs)
        
        # Also remove from all collections
        _remove_song_from_all_collections(song_id)
        
        return {
            'success': True,
            'message': 'Song removed from library'
        }
    
    return {
        'success': False,
        'message': 'Song not found in library'
    }


def get_song_by_id(song_id):
    """Get a specific song from library by ID"""
    library_songs = _load_json(LIBRARY_SONGS_PATH)
    for song in library_songs:
        if song.get('id') == song_id:
            return song
    return None


# ============================================================================
# COLLECTIONS/PLAYLISTS MANAGEMENT
# ============================================================================

def create_collection(name, description=''):
    """
    Create a new collection/playlist
    
    Args:
        name: Collection name
        description: Optional description
        
    Returns:
        dict with success status and collection_id
    """
    collections = _load_json(COLLECTIONS_PATH)
    
    # Generate unique ID
    collection_id = str(uuid.uuid4())
    
    # Create collection
    collection = {
        'id': collection_id,
        'name': name,
        'description': description,
        'songs': [],  # List of song IDs
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    collections.append(collection)
    _save_json(COLLECTIONS_PATH, collections)
    
    return {
        'success': True,
        'message': 'Collection created',
        'collection_id': collection_id,
        'collection': collection
    }


def get_collections():
    """
    Get all collections
    
    Returns:
        list of collections with song counts
    """
    collections = _load_json(COLLECTIONS_PATH)
    
    # Add song counts
    for collection in collections:
        collection['song_count'] = len(collection.get('songs', []))
    
    return collections


def get_collection_by_id(collection_id):
    """Get a specific collection by ID"""
    collections = _load_json(COLLECTIONS_PATH)
    for collection in collections:
        if collection.get('id') == collection_id:
            return collection
    return None


def get_collection_with_songs(collection_id):
    """
    Get collection with full song details
    
    Args:
        collection_id: Collection ID
        
    Returns:
        dict with collection info and full song details
    """
    collection = get_collection_by_id(collection_id)
    if not collection:
        return None
    
    # Get full song details for each song ID
    library_songs = _load_json(LIBRARY_SONGS_PATH)
    song_ids = collection.get('songs', [])
    
    full_songs = []
    for song_id in song_ids:
        song = next((s for s in library_songs if s.get('id') == song_id), None)
        if song:
            full_songs.append(song)
    
    return {
        'id': collection['id'],
        'name': collection['name'],
        'description': collection.get('description', ''),
        'created_at': collection.get('created_at'),
        'updated_at': collection.get('updated_at'),
        'songs': full_songs
    }


def update_collection(collection_id, name=None, description=None):
    """
    Update collection metadata
    
    Args:
        collection_id: Collection ID
        name: New name (optional)
        description: New description (optional)
        
    Returns:
        dict with success status
    """
    collections = _load_json(COLLECTIONS_PATH)
    
    for collection in collections:
        if collection.get('id') == collection_id:
            if name is not None:
                collection['name'] = name
            if description is not None:
                collection['description'] = description
            collection['updated_at'] = datetime.utcnow().isoformat()
            
            _save_json(COLLECTIONS_PATH, collections)
            return {
                'success': True,
                'message': 'Collection updated',
                'collection': collection
            }
    
    return {
        'success': False,
        'message': 'Collection not found'
    }


def delete_collection(collection_id):
    """
    Delete a collection
    
    Args:
        collection_id: Collection ID
        
    Returns:
        dict with success status
    """
    collections = _load_json(COLLECTIONS_PATH)
    
    original_count = len(collections)
    collections = [c for c in collections if c.get('id') != collection_id]
    
    if len(collections) < original_count:
        _save_json(COLLECTIONS_PATH, collections)
        return {
            'success': True,
            'message': 'Collection deleted'
        }
    
    return {
        'success': False,
        'message': 'Collection not found'
    }


def add_song_to_collection(collection_id, song_id):
    """
    Add a song to a collection
    
    Args:
        collection_id: Collection ID
        song_id: Song ID from library
        
    Returns:
        dict with success status
    """
    # Verify song exists in library
    song = get_song_by_id(song_id)
    if not song:
        return {
            'success': False,
            'message': 'Song not found in library'
        }
    
    collections = _load_json(COLLECTIONS_PATH)
    
    for collection in collections:
        if collection.get('id') == collection_id:
            songs = collection.get('songs', [])
            
            # Check if already in collection
            if song_id in songs:
                return {
                    'success': False,
                    'message': 'Song already in collection'
                }
            
            songs.append(song_id)
            collection['songs'] = songs
            collection['updated_at'] = datetime.utcnow().isoformat()
            
            _save_json(COLLECTIONS_PATH, collections)
            return {
                'success': True,
                'message': 'Song added to collection'
            }
    
    return {
        'success': False,
        'message': 'Collection not found'
    }


def remove_song_from_collection(collection_id, song_id):
    """
    Remove a song from a collection
    
    Args:
        collection_id: Collection ID
        song_id: Song ID
        
    Returns:
        dict with success status
    """
    collections = _load_json(COLLECTIONS_PATH)
    
    for collection in collections:
        if collection.get('id') == collection_id:
            songs = collection.get('songs', [])
            
            if song_id in songs:
                songs.remove(song_id)
                collection['songs'] = songs
                collection['updated_at'] = datetime.utcnow().isoformat()
                
                _save_json(COLLECTIONS_PATH, collections)
                return {
                    'success': True,
                    'message': 'Song removed from collection'
                }
            
            return {
                'success': False,
                'message': 'Song not in collection'
            }
    
    return {
        'success': False,
        'message': 'Collection not found'
    }


def _remove_song_from_all_collections(song_id):
    """Remove a song from all collections (internal helper)"""
    collections = _load_json(COLLECTIONS_PATH)
    modified = False
    
    for collection in collections:
        songs = collection.get('songs', [])
        if song_id in songs:
            songs.remove(song_id)
            collection['songs'] = songs
            collection['updated_at'] = datetime.utcnow().isoformat()
            modified = True
    
    if modified:
        _save_json(COLLECTIONS_PATH, collections)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_library_stats():
    """Get statistics about the library"""
    library_songs = _load_json(LIBRARY_SONGS_PATH)
    collections = _load_json(COLLECTIONS_PATH)
    
    return {
        'total_songs': len(library_songs),
        'total_collections': len(collections),
        'songs_by_source': _count_by_field(library_songs, 'source'),
        'most_recent_additions': library_songs[-5:] if library_songs else []
    }


def _count_by_field(items, field):
    """Count items by a specific field value"""
    counts = {}
    for item in items:
        value = item.get(field, 'unknown')
        counts[value] = counts.get(value, 0) + 1
    return counts


def clear_library():
    """Clear all library data (for testing purposes)"""
    _save_json(LIBRARY_SONGS_PATH, [])
    _save_json(COLLECTIONS_PATH, [])
    return {
        'success': True,
        'message': 'Library cleared'
    }
