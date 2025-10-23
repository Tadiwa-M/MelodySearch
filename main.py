"""
MelodySearch Command-Line Interface
Analyze audio files and find similar songs.
Enhanced with comprehensive error handling and user guidance.
"""

import os
import sys
import logging
from typing import Optional

from feature_extraction import HybridFeatureExtractor
from matcher import CrossGenreSimilarityMatcher
from song_db import save_song_to_db, load_song_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_audio_file(file_path: str) -> tuple[bool, Optional[str]]:
    """
    Validate that the audio file exists and is accessible.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file_path or not file_path.strip():
        return False, "File path cannot be empty"
    
    file_path = file_path.strip()
    
    # Check if file exists
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    # Check if it's a file (not a directory)
    if not os.path.isfile(file_path):
        return False, f"Path is not a file: {file_path}"
    
    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        return False, f"File is not readable: {file_path}"
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty"
        if file_size < 1024:  # Less than 1KB
            return False, f"File is very small ({file_size} bytes), may be corrupted"
    except OSError as e:
        return False, f"Cannot access file: {e}"
    
    # Check file extension (basic validation)
    valid_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg', '.webm']
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in valid_extensions:
        logger.warning(f"File extension '{file_ext}' may not be supported. Supported: {', '.join(valid_extensions)}")
    
    return True, None


def print_header():
    """Print application header."""
    print("=" * 60)
    print("MelodySearch - Audio Analysis Tool")
    print("=" * 60)
    print()


def print_error(message: str, suggestions: list = None):
    """Print error message with optional suggestions."""
    print(f"\n❌ Error: {message}")
    if suggestions:
        print("\n💡 Suggestions:")
        for suggestion in suggestions:
            print(f"   - {suggestion}")
    print()


def print_success(message: str):
    """Print success message."""
    print(f"\n✓ {message}\n")


def main():
    """
    Main function for the command-line interface.
    Enhanced with comprehensive error handling.
    """
    print_header()
    
    # Get audio file path with validation
    max_attempts = 3
    audio_file_path = None
    
    for attempt in range(max_attempts):
        try:
            user_input = input("Enter the path to the audio file (or 'q' to quit): ").strip()
            
            if user_input.lower() == 'q':
                print("Exiting...")
                return 0
            
            is_valid, error_msg = validate_audio_file(user_input)
            
            if is_valid:
                audio_file_path = user_input
                break
            else:
                print_error(error_msg, [
                    "Check the file path is correct",
                    "Ensure the file exists and is accessible",
                    "Supported formats: WAV, MP3, FLAC, M4A, OGG, WEBM"
                ])
                
                if attempt < max_attempts - 1:
                    print(f"Please try again ({attempt + 1}/{max_attempts} attempts used)")
                    
        except KeyboardInterrupt:
            print("\n\nCancelled by user")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error getting file path: {e}")
            print_error("An unexpected error occurred", ["Try again"])
    
    if not audio_file_path:
        print_error("Too many invalid attempts", ["Run the program again"])
        return 1
    
    # Get song title
    try:
        song_title = input("Enter the title of the song (optional, press Enter to skip): ").strip()
        if not song_title:
            song_title = f"Unknown - {os.path.basename(audio_file_path)}"
            print(f"Using default title: {song_title}")
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        return 1
    
    print()
    print("-" * 60)
    print("Analyzing audio file...")
    print("-" * 60)
    
    # Initialize extractor with error handling
    try:
        extractor = HybridFeatureExtractor()
    except Exception as e:
        logger.error(f"Failed to initialize feature extractor: {e}")
        print_error("Failed to initialize audio analyzer", [
            "Check that all required libraries are installed",
            "Run: pip install -r requirements.txt"
        ])
        return 1
    
    # Extract features with error handling
    features = None
    try:
        print("Extracting audio features...")
        features = extractor.extract_features(audio_file_path)
    except FileNotFoundError:
        print_error(f"Audio file not found: {audio_file_path}")
        return 1
    except PermissionError:
        print_error(f"Permission denied reading file: {audio_file_path}", [
            "Check file permissions",
            "Ensure you have read access to the file"
        ])
        return 1
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}", exc_info=True)
        print_error("Failed to analyze audio file", [
            "Ensure the file is a valid audio file",
            "Try converting to WAV or MP3 format",
            "Check that the file is not corrupted",
            "Supported formats: WAV, MP3, FLAC, M4A, OGG"
        ])
        return 1
    
    if not features:
        print_error("No features could be extracted from the audio file", [
            "The file may be corrupted or in an unsupported format",
            "Try a different audio file",
            "Convert the file to WAV format and try again"
        ])
        return 1
    
    print_success("Audio features extracted successfully")
    
    # Add metadata
    features["title"] = song_title
    
    # Save to database with error handling
    try:
        print("Saving to database...")
        save_song_to_db(features)
        print_success("Song saved to database")
    except Exception as e:
        logger.warning(f"Failed to save to database: {e}")
        print(f"⚠️  Warning: Could not save to database: {e}")
        print("Continuing with analysis...")
    
    # Load song database with error handling
    try:
        print("Loading song database...")
        song_db = load_song_db()
        print(f"Loaded {len(song_db)} songs from database")
    except Exception as e:
        logger.error(f"Failed to load song database: {e}")
        print_error("Could not load song database", [
            "The database file may be corrupted",
            "Check Data/song_db.json exists and is valid",
            "You can delete the file to create a new database"
        ])
        return 1
    
    # Check if database has enough songs
    if len(song_db) < 2:
        print()
        print("⚠️  Warning: Database has very few songs")
        print("Add more songs to get better recommendations")
        print()
    
    # Initialize matcher with error handling
    try:
        matcher = CrossGenreSimilarityMatcher()
    except Exception as e:
        logger.error(f"Failed to initialize matcher: {e}")
        print_error("Failed to initialize similarity matcher", [
            "Check that all required libraries are installed"
        ])
        return 1
    
    # Find similar songs with error handling
    try:
        print()
        print("-" * 60)
        print("Finding similar songs...")
        print("-" * 60)
        
        recommendations = matcher.find_mathematical_similarities(
            features, song_db, top_n=10
        )
    except Exception as e:
        logger.error(f"Similarity matching failed: {e}", exc_info=True)
        print_error("Failed to find similar songs", [
            "The database may have invalid entries",
            "Try rebuilding the database"
        ])
        return 1
    
    # Display results
    print()
    if recommendations and len(recommendations) > 0:
        print("=" * 60)
        print("Top Recommendations:")
        print("=" * 60)
        print()
        
        for i, (title, score, _) in enumerate(recommendations, 1):
            # Format similarity score
            percentage = score * 100
            
            # Add visual indicators
            if score >= 0.9:
                indicator = "🔥"
            elif score >= 0.7:
                indicator = "✓"
            else:
                indicator = "•"
            
            print(f"{i:2d}. {indicator} {title}")
            print(f"     Similarity: {score:.2f} ({percentage:.0f}%)")
            print()
        
        print("=" * 60)
        print(f"Found {len(recommendations)} similar songs")
        print("=" * 60)
        
    else:
        print("=" * 60)
        print("No recommendations found")
        print("=" * 60)
        print()
        print("💡 To get recommendations:")
        print("   - Add more songs to the database")
        print("   - Analyze different audio files using this tool")
        print("   - Each analyzed song is added to the database")
        print()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        print_error("An unexpected error occurred", [
            "Check the error log for details",
            "Try running the program again",
            "Contact support if the issue persists"
        ])
        sys.exit(1)
