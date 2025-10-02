# Python
import json

DB_PATH = r"C:\Users\Tmata\PycharmProjects\MelodySearch\Data\song_db.json"

def save_song_to_db(song_features):
    try:
        # Load existing database
        try:
            with open(DB_PATH, 'r') as db_file:
                song_db = json.load(db_file)
        except FileNotFoundError:
            song_db = []

        # Add new song
        song_db.append(song_features)

        # Save updated database
        with open(DB_PATH, 'w') as db_file:
            json.dump(song_db, db_file, indent=4)
    except Exception as e:
        print(f"Error saving song to database: {e}")

def load_song_db():
    try:
        with open(DB_PATH, 'r') as db_file:
            return json.load(db_file)
    except FileNotFoundError:
        return []