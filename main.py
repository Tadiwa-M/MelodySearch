from feature_extraction import HybridFeatureExtractor
from matcher import CrossGenreSimilarityMatcher
from song_db import save_song_to_db, load_song_db

if __name__ == "__main__":
    audio_file_path = input("Enter the path to the WAV file: ")
    song_title = input("Enter the title of the song: ")

    # Initialize extractor
    extractor = HybridFeatureExtractor()

    # Extract features as a dictionary
    features = extractor.extract_features(audio_file_path)

    if features:
        # Add metadata
        features["title"] = song_title

        # Save the song to the database
        save_song_to_db(features)

        # Load the song database
        song_db = load_song_db()

        # Initialize matcher
        matcher = CrossGenreSimilarityMatcher()

        # Find similar songs (top 10)
        recommendations = matcher.find_mathematical_similarities(
            features, song_db, top_n=10
        )

        if recommendations:
            print("Top Recommendations:")
            for title, score, _ in recommendations:
                print(f"{title} (Similarity: {score:.2f})")
        else:
            print("No recommendations found. Add more songs to the database.")
    else:
        print("Failed to extract features from the audio file.")
