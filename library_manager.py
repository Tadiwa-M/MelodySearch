"""
Library Manager - Handles user's saved songs and collections/playlists
Enhanced with comprehensive error handling and data validation.
"""
import json
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Library storage paths
LIBRARY_DIR = os.getenv('LIBRARY_PATH', os.path.join('Data', 'library'))
LIBRARY_SONGS_PATH = os.path.join(LIBRARY_DIR, 'library_songs.json')
COLLECTIONS_PATH = os.path.join(LIBRARY_DIR, 'collections.json')


def _ensure_library_dir():
    """Create library directory if it doesn't exist with error handling."""
    try:
        os.makedirs(LIBRARY_DIR, exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied creating library directory: {LIBRARY_DIR}")
        raise
    except Exception as e:
        logger.error(f"Failed to create library directory: {e}")
        raise


def _load_json(path, default=None):
    """
    Load JSON file with comprehensive error handling.
    
    Args:
        path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Loaded data or default value
    """
    try:
        if not os.path.exists(path):
            logger.debug(f"File does not exist, using default: {path}")
            return default if default is not None else []
        
        # Check file size
        file_size = os.path.getsize(path)
        if file_size == 0:
            logger.warning(f"File is empty: {path}")
            return default if default is not None else []
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            logger.warning(f"File is very large ({file_size} bytes): {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Validate data structure
        if not isinstance(data, (list, dict)):
            logger.warning(f"Invalid data structure in {path}, using default")
            return default if default is not None else []
        
        return data
        
    except FileNotFoundError:
        logger.debug(f"File not found: {path}")
        return default if default is not None else []
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted JSON file at {path}: {e}")
        # Backup the corrupted file
        try:
            backup_path = f"{path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(path):
                import shutil
                shutil.copy2(path, backup_path)
                logger.info(f"Backed up corrupted file to: {backup_path}")
        except Exception as backup_error:
            logger.warning(f"Could not backup corrupted file: {backup_error}")
        
        return default if default is not None else []
    except PermissionError:
        logger.error(f"Permission denied reading file: {path}")
        return default if default is not None else []
    except Exception as e:
        logger.error(f"Unexpected error loading {path}: {e}")
        return default if default is not None else []


def _save_json(path, data):
    """
    Save data to JSON file with error handling and atomic writes.
    
    Args:
        path: Path to JSON file
        data: Data to save
    """
    try:
        _ensure_library_dir()
        
        # Validate data can be serialized
        try:
            json_str = json.dumps(data, indent=2)
        except (TypeError, ValueError) as e:
            logger.error(f"Data cannot be serialized to JSON: {e}")
            raise ValueError(f"Invalid data for JSON serialization: {e}")
        
        # Use atomic write (write to temp file, then rename)
        temp_path = f"{path}.tmp"
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk
            
            # Atomic rename
            if os.path.exists(path):
                # Backup existing file
                backup_path = f"{path}.backup"
                try:
                    import shutil
                    shutil.copy2(path, backup_path)
                except Exception as backup_error:
                    logger.warning(f"Could not create backup: {backup_error}")
            
            os.replace(temp_path, path)
            logger.debug(f"Successfully saved to {path}")
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise
            
    except PermissionError:
        logger.error(f"Permission denied writing to: {path}")
        raise
    except OSError as e:
        logger.error(f"OS error saving file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error saving to {path}: {e}")
        raise


# ============================================================================
# LIBRARY SONGS MANAGEMENT
# ============================================================================

def add_song_to_library(song_data):
    """
    Add a song to the user's library with comprehensive validation.
    
    Args:
        song_data: dict containing song information (title, artist, audio_features, etc.)
        
    Returns:
        dict with success status and song_id
    """
    # Validate input
    if not song_data or not isinstance(song_data, dict):
        logger.error("Invalid song_data: must be a non-empty dictionary")
        return {
            'success': False,
            'message': 'Invalid song data',
            'error': 'song_data must be a dictionary'
        }
    
    # Validate required fields
    title = song_data.get('title')
    if not title or not str(title).strip():
        logger.error("Song title is required")
        return {
            'success': False,
            'message': 'Song title is required',
            'error': 'missing_title'
        }
    
    try:
        library_songs = _load_json(LIBRARY_SONGS_PATH)
        
        # Ensure library_songs is a list
        if not isinstance(library_songs, list):
            logger.warning("Library songs data is not a list, initializing new list")
            library_songs = []
        
        # Generate unique ID for the song
        song_id = str(uuid.uuid4())
        
        # Sanitize and validate title and artist
        title = str(title).strip()[:500]  # Limit length
        artist = str(song_data.get('artist', 'Unknown')).strip()[:500]
        
        # Create library entry with safe defaults
        library_entry = {
            'id': song_id,
            'title': title,
            'artist': artist,
            'audio_features': song_data.get('audio_features', {}),
            'spotify_metadata': song_data.get('spotify_metadata', {}),
            'spotify_id': song_data.get('spotify_id') or song_data.get('spotify_metadata', {}).get('spotify_id'),
            'added_at': datetime.utcnow().isoformat(),
            'source': song_data.get('source', 'manual')  # 'manual', 'search_result', 'upload'
        }
        
        # Check for duplicates (by title and artist or spotify_id)
        spotify_id = library_entry.get('spotify_id')
        for existing_song in library_songs:
            if not isinstance(existing_song, dict):
                continue
                
            # Check by Spotify ID if available
            if spotify_id and existing_song.get('spotify_id') == spotify_id:
                logger.info(f"Song already in library (by Spotify ID): {title}")
                return {
                    'success': False,
                    'message': 'Song already in library',
                    'song_id': existing_song.get('id'),
                    'duplicate': True
                }
            
            # Check by title and artist
            if (existing_song.get('title') == title and 
                existing_song.get('artist') == artist):
                logger.info(f"Song already in library (by title/artist): {title} by {artist}")
                return {
                    'success': False,
                    'message': 'Song already in library',
                    'song_id': existing_song.get('id'),
                    'duplicate': True
                }
        
        # Add to library
        library_songs.append(library_entry)
        
        # Save with error handling
        try:
            _save_json(LIBRARY_SONGS_PATH, library_songs)
        except Exception as e:
            logger.error(f"Failed to save library: {e}")
            return {
                'success': False,
                'message': 'Failed to save to library',
                'error': str(e)
            }
        
        logger.info(f"Added song to library: {title} by {artist} (ID: {song_id})")
        
        return {
            'success': True,
            'message': 'Song added to library',
            'song_id': song_id
        }
        
    except Exception as e:
        logger.error(f"Unexpected error adding song to library: {e}", exc_info=True)
        return {
            'success': False,
            'message': 'Failed to add song to library',
            'error': str(e)
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
