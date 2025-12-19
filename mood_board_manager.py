"""
Mood Board Manager
Handles saving, loading, and sharing mood board collections
"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional

MOOD_BOARDS_DIR = 'Data/mood_boards'

def ensure_mood_boards_dir():
    """Ensure the mood boards directory exists"""
    if not os.path.exists(MOOD_BOARDS_DIR):
        os.makedirs(MOOD_BOARDS_DIR)


def save_mood_board(user_id: str, images: List[Dict], tracks: List[Dict], board_name: str = None) -> str:
    """
    Save a mood board to the database

    Args:
        user_id: Spotify user ID
        images: List of image dictionaries
        tracks: List of track dictionaries
        board_name: Optional custom name for the board

    Returns:
        board_id: Unique ID for the saved board
    """
    ensure_mood_boards_dir()

    # Generate board ID from timestamp and user
    timestamp = datetime.now().isoformat()
    board_id = hashlib.md5(f"{user_id}{timestamp}".encode()).hexdigest()[:12]

    board_data = {
        'id': board_id,
        'user_id': user_id,
        'name': board_name or f"Mood Board {datetime.now().strftime('%B %d, %Y')}",
        'images': images,
        'tracks': tracks,
        'created_at': timestamp,
        'updated_at': timestamp
    }

    file_path = os.path.join(MOOD_BOARDS_DIR, f"{board_id}.json")
    with open(file_path, 'w') as f:
        json.dump(board_data, f, indent=2)

    return board_id


def load_mood_board(board_id: str) -> Optional[Dict]:
    """
    Load a mood board by ID

    Args:
        board_id: Unique board ID

    Returns:
        Board data dictionary or None if not found
    """
    file_path = os.path.join(MOOD_BOARDS_DIR, f"{board_id}.json")

    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as f:
        return json.load(f)


def get_user_mood_boards(user_id: str) -> List[Dict]:
    """
    Get all mood boards for a specific user

    Args:
        user_id: Spotify user ID

    Returns:
        List of mood board summaries (without full image data)
    """
    ensure_mood_boards_dir()
    boards = []

    for filename in os.listdir(MOOD_BOARDS_DIR):
        if filename.endswith('.json'):
            file_path = os.path.join(MOOD_BOARDS_DIR, filename)
            with open(file_path, 'r') as f:
                board = json.load(f)
                if board.get('user_id') == user_id:
                    # Return summary without full image data
                    boards.append({
                        'id': board['id'],
                        'name': board['name'],
                        'image_count': len(board.get('images', [])),
                        'created_at': board['created_at'],
                        'preview_image': board['images'][0] if board.get('images') else None
                    })

    # Sort by creation date (newest first)
    boards.sort(key=lambda x: x['created_at'], reverse=True)
    return boards


def delete_mood_board(board_id: str, user_id: str) -> bool:
    """
    Delete a mood board

    Args:
        board_id: Unique board ID
        user_id: Spotify user ID (for verification)

    Returns:
        True if deleted, False if not found or unauthorized
    """
    file_path = os.path.join(MOOD_BOARDS_DIR, f"{board_id}.json")

    if not os.path.exists(file_path):
        return False

    # Verify ownership
    with open(file_path, 'r') as f:
        board = json.load(f)
        if board.get('user_id') != user_id:
            return False

    os.remove(file_path)
    return True


def add_image_to_board(board_id: str, user_id: str, image: Dict) -> bool:
    """
    Add an image to an existing mood board

    Args:
        board_id: Unique board ID
        user_id: Spotify user ID (for verification)
        image: Image dictionary to add

    Returns:
        True if successful, False otherwise
    """
    board = load_mood_board(board_id)

    if not board or board.get('user_id') != user_id:
        return False

    # Add image if not already present
    image_url = image.get('url')
    if not any(img.get('url') == image_url for img in board.get('images', [])):
        board['images'].append(image)
        board['updated_at'] = datetime.now().isoformat()

        file_path = os.path.join(MOOD_BOARDS_DIR, f"{board_id}.json")
        with open(file_path, 'w') as f:
            json.dump(board, f, indent=2)

        return True

    return False


def remove_image_from_board(board_id: str, user_id: str, image_url: str) -> bool:
    """
    Remove an image from a mood board

    Args:
        board_id: Unique board ID
        user_id: Spotify user ID (for verification)
        image_url: URL of the image to remove

    Returns:
        True if successful, False otherwise
    """
    board = load_mood_board(board_id)

    if not board or board.get('user_id') != user_id:
        return False

    original_count = len(board.get('images', []))
    board['images'] = [img for img in board.get('images', []) if img.get('url') != image_url]

    if len(board['images']) < original_count:
        board['updated_at'] = datetime.now().isoformat()

        file_path = os.path.join(MOOD_BOARDS_DIR, f"{board_id}.json")
        with open(file_path, 'w') as f:
            json.dump(board, f, indent=2)

        return True

    return False


def generate_share_link(board_id: str, base_url: str) -> str:
    """
    Generate a shareable link for a mood board

    Args:
        board_id: Unique board ID
        base_url: Base URL of the application

    Returns:
        Shareable URL
    """
    return f"{base_url}/shared/mood-board/{board_id}"
