import json
import os

# Use relative path for local, environment variable for production
DB_PATH = os.getenv('SONG_DB_PATH', os.path.join('Data', 'song_db.json'))


def save_song_to_db(song_features):
    try:
        # Create Data directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        # Load existing database
        try:
            with open(DB_PATH, 'r') as db_file:
                song_db = json.load(db_file)
        except FileNotFoundError:
            song_db = []

        # Add new song (avoid duplicates)
        song_title = song_features.get('title', '')
        if not any(s.get('title') == song_title for s in song_db):
            song_db.append(song_features)

        # Save updated database
        with open(DB_PATH, 'w') as db_file:
            json.dump(song_db, db_file, indent=4)

        print(f"✓ Saved song: {song_title}")
    except Exception as e:
        print(f"Error saving song to database: {e}")


def load_song_db():
    try:
        with open(DB_PATH, 'r') as db_file:
            return json.load(db_file)
    except FileNotFoundError:
        print("Database file not found, returning empty list")
        return []
    except json.JSONDecodeError:
        print("Database file corrupted, returning empty list")
        return []