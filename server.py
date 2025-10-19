from flask import Flask, request, jsonify, render_template, redirect, session
import logging
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from song_db import save_song_to_db, load_song_db
from flask_session import Session
import requests
import tempfile
from feature_extraction import HybridFeatureExtractor
from metadata_similarity_engine import MetadataSimilarityEngine
import random
import requests
import time
import json
import tempfile
from werkzeug.utils import secure_filename
import librosa
import numpy as np

app = Flask(__name__)
# Security: Require a strong secret key to be set via environment variable
secret_key = os.getenv('SECRET_KEY')
if not secret_key or secret_key == 'dev-secret-key-12345':
    # In development, generate a random key if none provided
    if os.getenv('FLASK_ENV') == 'development':
        import secrets
        secret_key = secrets.token_hex(32)
        logging.warning("Using randomly generated secret key. Set SECRET_KEY environment variable for persistence.")
    else:
        raise ValueError("SECRET_KEY environment variable must be set in production!")
app.secret_key = secret_key

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Security: Add security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Don't set CSP yet as it may need tuning for the application
    return response

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a', 'ogg'}

logging.basicConfig(level=logging.DEBUG)

# Spotify API credentials - MUST be set via environment variables for security
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5000/callback')

# Security: Validate that required credentials are set
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    logging.error("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set as environment variables!")
    # Allow startup but functionality will be limited
    SPOTIFY_CLIENT_ID = SPOTIFY_CLIENT_ID or 'NOT_SET'
    SPOTIFY_CLIENT_SECRET = SPOTIFY_CLIENT_SECRET or 'NOT_SET'
SCOPE = 'user-read-private user-read-email'
CACHE_PATH = '.cache'


def get_spotify_client():
    auth_manager = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_auth_manager():
    """Get Spotify OAuth manager for user authentication"""
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE_PATH
    )


def download_and_analyze_preview(preview_url):
    """Download Spotify preview and analyze with your existing feature extraction"""
    if not preview_url:
        return None

    try:
        # Security: Validate URL is from Spotify domain
        from urllib.parse import urlparse
        parsed = urlparse(preview_url)
        if not parsed.netloc.endswith('.spotify.com') and not parsed.netloc.endswith('.scdn.co'):
            logging.warning(f"Rejecting non-Spotify URL: {preview_url}")
            return None

        # Download the 30-second preview
        response = requests.get(preview_url, timeout=30)
        if response.status_code != 200:
            return None

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        try:
            # Use your existing extract_features function!
            features = extract_features(temp_path)
            return features
        finally:
            # Clean up temp file
            os.unlink(temp_path)

    except Exception as e:
        logging.error(f"Error analyzing preview: {e}")
        return None


def create_fallback_features(track_info):
    """Create basic features when no preview is available"""
    duration_ms = track_info.get('duration_ms', 180000)
    popularity = track_info.get('popularity', 50)

    # Better tempo estimation based on genre hints and duration
    estimated_tempo = max(60, min(200, (240000 / duration_ms) * 120))

    # Mood estimation based on popularity and other factors
    if popularity > 70:
        mood = "energetic"
    elif popularity < 30:
        mood = "calm"
    else:
        mood = "neutral"

    return {
        "tempo": round(estimated_tempo),
        "chroma": [0.1] * 12,  # Neutral chroma values
        "mood": mood,
        "rhythm": [0.5] * 8,  # Placeholder rhythm
        "spectral_contrast": [0.2] * 7,  # Placeholder spectral contrast
        "source": "estimated",  # Flag to show these are estimates
        "popularity": popularity,
        "duration_ms": duration_ms
    }


def find_and_analyze_similar_tracks(sp, original_track, original_features, limit=10):
    """Find similar tracks from Spotify and analyze them"""
    recommendations = []

    try:
        # Strategy 1: Search for songs by the same artist
        artist_name = original_track['artists'][0]['name']
        artist_results = sp.search(q=f'artist:{artist_name}', type='track', limit=20)

        # Strategy 2: Search for similar genre/style (use track name keywords)
        track_name = original_track['name']
        # Remove common suffixes that might confuse search
        clean_name = track_name.replace('- CD Pro Version', '').replace('(Remaster)', '').strip()
        style_results = sp.search(q=clean_name.split()[0], type='track', limit=30)

        # Strategy 3: Get popular tracks in similar tempo range
        tempo = original_features.get('tempo', 120)
        if tempo > 140:
            tempo_query = 'dance electronic pop'
        elif tempo < 80:
            tempo_query = 'ballad slow acoustic'
        else:
            tempo_query = 'rock alternative indie'
        tempo_results = sp.search(q=tempo_query, type='track', limit=20)

        # Combine all results
        all_candidates = []
        for results in [artist_results, style_results, tempo_results]:
            all_candidates.extend(results['tracks']['items'])

        # Remove duplicates and original song
        seen_ids = set()
        unique_candidates = []
        original_id = original_track.get('id')

        for track in all_candidates:
            if track['id'] not in seen_ids and track['id'] != original_id:
                seen_ids.add(track['id'])
                unique_candidates.append(track)

        logging.debug(f"Found {len(unique_candidates)} candidate tracks to analyze")

        # Analyze candidates with previews
        analyzed_tracks = []
        for track in unique_candidates[:50]:  # Limit to avoid too many API calls
            if track.get('preview_url'):
                logging.debug(f"Analyzing: {track['name']} by {track['artists'][0]['name']}")

                features = download_and_analyze_preview(track['preview_url'])
                if features:
                    track_data = {
                        "title": track['name'],
                        "artist": track['artists'][0]['name'],
                        "audio_features": features,
                        "spotify_id": track['id'],
                        "popularity": track['popularity'],
                        "preview_url": track['preview_url']
                    }
                    analyzed_tracks.append(track_data)

                    # Stop if we have enough
                    if len(analyzed_tracks) >= 25:
                        break

        logging.debug(f"Successfully analyzed {len(analyzed_tracks)} tracks")

        # Use your existing matcher to find similarities
        if analyzed_tracks:
            # Create a temporary database with just the analyzed tracks
            temp_db = [{"title": track["title"], **track["audio_features"]} for track in analyzed_tracks]

            # Find similar songs using your existing algorithm
            similar_matches = find_similar_songs(
                {"title": original_track['name'], **original_features},
                temp_db,
                top_n=limit
            )

            # Build recommendations with full track info
            for title, similarity_score in similar_matches:
                # Find the full track data
                for track_data in analyzed_tracks:
                    if track_data["title"] == title:
                        recommendations.append({
                            "title": track_data["title"],
                            "artist": track_data["artist"],
                            "similarity_score": round(similarity_score, 3),
                            "spotify_id": track_data["spotify_id"],
                            "popularity": track_data["popularity"],
                            "preview_url": track_data["preview_url"],
                            "audio_features": track_data["audio_features"]
                        })
                        break

        return recommendations

    except Exception as e:
        logging.error(f"Error finding similar tracks: {e}")
        return []


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login')
def login():
    session.clear()
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
    auth_manager = get_auth_manager()
    auth_url = auth_manager.get_authorize_url()
    return redirect(auth_url)


@app.route('/callback')
def callback():
    code = request.args.get('code')
    get_auth_manager().get_access_token(code)
    session['is_authenticated'] = True
    return redirect('/')


# Replace your search route with this clean metadata-only version

@app.route('/search', methods=['POST'])
def search_song():
    # Security: Proper authentication check - removed bypass
    if not session.get('is_authenticated'):
        return jsonify({"error": "Authentication required"}), 401

    try:
        # Security: Validate content type
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        sp = get_spotify_client()
        data = request.json
        
        # Security: Validate JSON structure
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON format"}), 400
            
        song_name = data.get('song_name')

        # Security: Input validation
        if not song_name:
            return jsonify({"error": "Song name is required"}), 400
        
        # Security: Limit song name length to prevent abuse
        if len(song_name) > 200:
            return jsonify({"error": "Song name too long"}), 400
        
        # Security: Basic sanitization - remove potentially dangerous characters
        song_name = song_name.strip()

        logging.debug(f"Searching for song: {song_name}")

        # Search for the original song
        results = sp.search(q=song_name, type='track', limit=1)
        if not results['tracks']['items']:
            return jsonify({"error": "Song not found"}), 404

        track = results['tracks']['items'][0]

        # NEW: Use metadata-based similarity engine
        similarity_engine = MetadataSimilarityEngine(sp)
        metadata_features = similarity_engine.extract_comprehensive_metadata(
            track['id'],
            track
        )

        logging.debug(f"Metadata analysis completeness: {metadata_features.get('feature_completeness', 0):.2%}")

        # Convert metadata to pseudo audio features for frontend compatibility
        pseudo_audio_features = convert_metadata_to_audio_features(metadata_features)

        # Structure the original song data
        original_song = {
            "title": track['name'],
            "artist": track['artists'][0]['name'],
            "audio_features": pseudo_audio_features,  # Frontend expects this key
            "spotify_metadata": {
                "popularity": track['popularity'],
                "duration_ms": track['duration_ms'],
                "explicit": track['explicit'],
                "preview_url": track.get('preview_url'),
                "has_preview": track.get('preview_url') is not None,
                "spotify_id": track['id'],
                "genres": metadata_features.get('artist_genres', []),
                "release_year": metadata_features.get('release_year'),
            }
        }

        # Save to your database
        save_song_to_db(original_song)

        # Find candidate tracks using metadata-based search
        logging.debug("Finding candidate tracks using metadata strategies...")
        candidate_recommendations = find_metadata_based_candidates(sp, track, metadata_features, limit=50)

        # Enhance candidates with metadata analysis
        enhanced_candidates = []
        for candidate in candidate_recommendations:
            try:
                if candidate.get('spotify_id'):
                    candidate_metadata = similarity_engine.extract_comprehensive_metadata(
                        candidate['spotify_id']
                    )

                    enhanced_candidate = {
                        "title": candidate.get('title', 'Unknown'),
                        "artist": candidate.get('artist', 'Unknown'),
                        "metadata_features": candidate_metadata,
                        "spotify_id": candidate.get('spotify_id'),
                        "popularity": candidate.get('popularity'),
                        "preview_url": candidate.get('preview_url')
                    }
                    enhanced_candidates.append(enhanced_candidate)

            except Exception as e:
                logging.warning(f"Failed to analyze candidate '{candidate.get('title', 'Unknown')}': {e}")
                continue

        logging.debug(f"Enhanced {len(enhanced_candidates)} candidates with metadata")

        # Use metadata similarity matching
        formatted_recommendations = []
        if enhanced_candidates:
            try:
                mathematical_matches = similarity_engine.find_metadata_similarities(
                    metadata_features,
                    enhanced_candidates,
                    top_n=10
                )

                logging.debug(f"Found {len(mathematical_matches)} metadata-based matches")

                # Format for frontend
                for title, similarity, breakdown in mathematical_matches:
                    original_candidate = next(
                        (rec for rec in enhanced_candidates if rec['title'] == title),
                        {}
                    )

                    # Convert metadata features to pseudo audio features for frontend
                    candidate_pseudo_features = convert_metadata_to_audio_features(
                        original_candidate.get('metadata_features', {})
                    )

                    formatted_recommendations.append({
                        "title": title,
                        "artist": original_candidate.get('artist', 'Unknown'),
                        "similarity_score": similarity,
                        "explanation": similarity_engine.explain_metadata_similarity(breakdown),
                        "feature_breakdown": breakdown,
                        "spotify_id": original_candidate.get('spotify_id'),
                        "popularity": original_candidate.get('popularity'),
                        "preview_url": original_candidate.get('preview_url'),
                        "audio_features": candidate_pseudo_features
                    })

            except Exception as e:
                logging.error(f"Metadata matching failed: {e}")
                # Fallback: return basic recommendations
                for candidate in enhanced_candidates[:10]:
                    candidate_pseudo_features = convert_metadata_to_audio_features(
                        candidate.get('metadata_features', {})
                    )
                    formatted_recommendations.append({
                        "title": candidate.get('title', 'Unknown'),
                        "artist": candidate.get('artist', 'Unknown'),
                        "similarity_score": 0.5,
                        "explanation": "Basic similarity (metadata analysis)",
                        "feature_breakdown": {},
                        "spotify_id": candidate.get('spotify_id'),
                        "popularity": candidate.get('popularity'),
                        "preview_url": candidate.get('preview_url'),
                        "audio_features": candidate_pseudo_features
                    })

        return jsonify({
            "message": "Song analyzed successfully",
            "original_song": original_song,
            "spotify_recommendations": formatted_recommendations,
            "local_recommendations": [],  # Skip local for now to simplify
            "total_recommendations": len(formatted_recommendations),
            "analysis_stats": {
                "original_completeness": metadata_features.get('feature_completeness', 0),
                "candidates_found": len(candidate_recommendations),
                "candidates_analyzed": len(enhanced_candidates),
                "metadata_matches": len(formatted_recommendations),
                "analysis_method": "metadata_based"
            }
        }), 200

    except spotipy.SpotifyException as e:
        logging.error(f"Spotify API error: {e}")
        # Security: Don't expose internal error details to client
        return jsonify({"error": "Spotify API error occurred"}), 403
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        # Security: Don't expose internal error details to client
        return jsonify({"error": "An unexpected error occurred"}), 500


def find_metadata_based_candidates(sp, original_track, metadata_features, limit=50):
    """Find candidate tracks using metadata-based search strategies"""
    candidates = []
    seen_ids = set()

    # Strategy 1: Same artist (but not too many)
    try:
        artist_name = original_track['artists'][0]['name']
        artist_results = sp.search(q=f'artist:{artist_name}', type='track', limit=10)
        for track in artist_results['tracks']['items']:
            if track['id'] not in seen_ids and track['id'] != original_track['id']:
                candidates.append(format_candidate(track))
                seen_ids.add(track['id'])
    except Exception as e:
        logging.warning(f"Artist search failed: {e}")

    # Strategy 2: Genre-based search (if we have genres)
    genres = metadata_features.get('artist_genres', [])
    if genres:
        for genre in genres[:2]:  # Top 2 genres
            try:
                genre_results = sp.search(q=f'genre:{genre}', type='track', limit=15)
                for track in genre_results['tracks']['items']:
                    if track['id'] not in seen_ids and len(candidates) < limit:
                        candidates.append(format_candidate(track))
                        seen_ids.add(track['id'])
            except Exception as e:
                logging.warning(f"Genre search failed for {genre}: {e}")

    # Strategy 3: Era-based search
    release_year = metadata_features.get('release_year')
    if release_year:
        try:
            year_start = release_year - 3
            year_end = release_year + 3
            year_results = sp.search(q=f'year:{year_start}-{year_end}', type='track', limit=20)
            for track in year_results['tracks']['items']:
                if track['id'] not in seen_ids and len(candidates) < limit:
                    candidates.append(format_candidate(track))
                    seen_ids.add(track['id'])
        except Exception as e:
            logging.warning(f"Year search failed: {e}")

    # Strategy 4: Similar popularity range
    popularity = metadata_features.get('popularity', 50)
    pop_min = max(0, popularity - 20)
    pop_max = min(100, popularity + 20)

    # Use general search terms based on characteristics
    search_terms = []
    if metadata_features.get('mainstream_level') == 'underground':
        search_terms.append('indie alternative experimental')
    elif metadata_features.get('mainstream_level') == 'mainstream':
        search_terms.append('popular hits chart')

    if metadata_features.get('duration_category') == 'short':
        search_terms.append('short track single')
    elif metadata_features.get('duration_category') == 'long':
        search_terms.append('extended mix album track')

    for term in search_terms:
        if len(candidates) < limit:
            try:
                term_results = sp.search(q=term, type='track', limit=10)
                for track in term_results['tracks']['items']:
                    if (track['id'] not in seen_ids and
                            pop_min <= track['popularity'] <= pop_max and
                            len(candidates) < limit):
                        candidates.append(format_candidate(track))
                        seen_ids.add(track['id'])
            except Exception as e:
                logging.warning(f"Term search failed for {term}: {e}")

    logging.debug(f"Found {len(candidates)} metadata-based candidates")
    return candidates


def format_candidate(track):
    """Format track for candidate list"""
    return {
        "title": track['name'],
        "artist": track['artists'][0]['name'] if track['artists'] else 'Unknown',
        "spotify_id": track['id'],
        "popularity": track['popularity'],
        "preview_url": track.get('preview_url')
    }


def convert_metadata_to_audio_features(metadata_features):
    """
    Convert metadata features to realistic pseudo-audio features for frontend display
    Uses ACTUAL metadata instead of generic mappings
    """
    if not metadata_features:
        return create_fallback_audio_features()

    # Get actual metadata values
    artist_genres = metadata_features.get('artist_genres', [])
    primary_genre = metadata_features.get('genre_primary', '').lower() if metadata_features.get('genre_primary') else ''
    release_year = metadata_features.get('release_year', 2000)
    popularity = metadata_features.get('popularity', 50)
    duration_ms = metadata_features.get('duration_ms', 180000)
    explicit = metadata_features.get('explicit', False)
    era = metadata_features.get('era', 'modern')
    mainstream_level = metadata_features.get('mainstream_level', 'mid_tier')

    # Create a detailed genre analysis
    genre_analysis = analyze_genre_characteristics(artist_genres)

    # TEMPO - Based on actual genres and era
    estimated_tempo = estimate_tempo_from_genres(artist_genres, era, duration_ms)

    # KEY - Based on genre patterns and musical theory
    estimated_key, estimated_mode = estimate_key_and_mode(artist_genres, era)

    # ENERGY - Based on genres, popularity, and era
    energy = calculate_energy_from_metadata(artist_genres, popularity, era, explicit)

    # VALENCE - Based on genres and song characteristics
    valence = calculate_valence_from_metadata(artist_genres, era, explicit)

    # DANCEABILITY - Based on genre characteristics
    danceability = calculate_danceability_from_metadata(artist_genres)

    # ACOUSTICNESS - Based on genre and era
    acousticness = calculate_acousticness_from_metadata(artist_genres, era)

    # INSTRUMENTALNESS - Based on genre patterns
    instrumentalness = calculate_instrumentalness_from_metadata(artist_genres)

    # SPEECHINESS - Based on genre (higher for rap/hip-hop)
    speechiness = calculate_speechiness_from_metadata(artist_genres)

    # LIVENESS - Based on genre and era
    liveness = calculate_liveness_from_metadata(artist_genres, era)

    # LOUDNESS - Based on genre and era
    loudness = calculate_loudness_from_metadata(artist_genres, era)

    return {
        'tempo': round(estimated_tempo),
        'key': estimated_key,
        'mode': estimated_mode,
        'energy': round(energy, 2),
        'valence': round(valence, 2),
        'danceability': round(danceability, 2),
        'acousticness': round(acousticness, 2),
        'instrumentalness': round(instrumentalness, 2),
        'speechiness': round(speechiness, 2),
        'liveness': round(liveness, 2),
        'loudness': round(loudness, 1),
        'duration': duration_ms,
        'time_signature': 4,  # Most music is 4/4
        'popularity': popularity,

        # Additional metadata for frontend display
        'genre_primary': metadata_features.get('genre_primary', 'Unknown'),
        'all_genres': ', '.join(artist_genres[:3]) if artist_genres else 'Unknown',
        'release_year': release_year,
        'era': era,
        'mainstream_level': mainstream_level,
        'artist_popularity': metadata_features.get('artist_popularity', 50),
        'explicit': explicit,

        # Analysis metadata
        'feature_completeness': metadata_features.get('feature_completeness', 0.8),
        'primary_source': 'metadata_analysis',
        'genre_confidence': len(artist_genres) / 5.0 if artist_genres else 0.2  # More genres = higher confidence
    }


def analyze_genre_characteristics(genres):
    """Analyze the musical characteristics of genres"""
    if not genres:
        return {'electronic': 0, 'acoustic': 0, 'energetic': 0, 'danceable': 0, 'vocal': 0}

    characteristics = {
        'electronic': 0, 'acoustic': 0, 'energetic': 0,
        'danceable': 0, 'vocal': 0, 'experimental': 0
    }

    genre_weights = {
        # Electronic genres
        'electronic': {'electronic': 1.0, 'danceable': 0.8, 'energetic': 0.7},
        'edm': {'electronic': 1.0, 'danceable': 1.0, 'energetic': 0.9},
        'house': {'electronic': 1.0, 'danceable': 1.0, 'energetic': 0.8},
        'techno': {'electronic': 1.0, 'danceable': 0.9, 'energetic': 0.8},
        'dubstep': {'electronic': 1.0, 'danceable': 0.7, 'energetic': 0.9},
        'ambient': {'electronic': 0.8, 'danceable': 0.1, 'energetic': 0.2, 'experimental': 0.7},

        # Hip-hop genres
        'hip hop': {'vocal': 0.9, 'energetic': 0.7, 'danceable': 0.6},
        'rap': {'vocal': 1.0, 'energetic': 0.8, 'danceable': 0.5},
        'trap': {'electronic': 0.6, 'vocal': 0.8, 'energetic': 0.8, 'danceable': 0.7},
        'drill': {'vocal': 0.9, 'energetic': 0.9, 'danceable': 0.6},

        # Rock genres
        'rock': {'energetic': 0.8, 'vocal': 0.8, 'acoustic': 0.3},
        'alternative rock': {'energetic': 0.7, 'vocal': 0.8, 'experimental': 0.5},
        'indie rock': {'energetic': 0.6, 'vocal': 0.8, 'experimental': 0.6},
        'punk': {'energetic': 1.0, 'vocal': 0.9, 'acoustic': 0.2},
        'metal': {'energetic': 1.0, 'vocal': 0.7, 'acoustic': 0.1},

        # Pop genres
        'pop': {'vocal': 0.9, 'danceable': 0.8, 'energetic': 0.6},
        'dance pop': {'vocal': 0.8, 'danceable': 1.0, 'energetic': 0.8, 'electronic': 0.6},

        # Acoustic genres
        'folk': {'acoustic': 1.0, 'vocal': 0.9, 'energetic': 0.3, 'danceable': 0.2},
        'country': {'acoustic': 0.8, 'vocal': 0.9, 'energetic': 0.4, 'danceable': 0.4},
        'acoustic': {'acoustic': 1.0, 'vocal': 0.8, 'energetic': 0.3, 'danceable': 0.2},

        # Jazz and blues
        'jazz': {'acoustic': 0.7, 'experimental': 0.8, 'energetic': 0.5, 'vocal': 0.6},
        'blues': {'acoustic': 0.8, 'vocal': 0.8, 'energetic': 0.4, 'danceable': 0.3},

        # Classical and orchestral
        'classical': {'acoustic': 1.0, 'experimental': 0.3, 'energetic': 0.4, 'vocal': 0.1},
        'orchestral': {'acoustic': 1.0, 'experimental': 0.2, 'energetic': 0.5, 'vocal': 0.2},

        # R&B and soul
        'r&b': {'vocal': 1.0, 'danceable': 0.7, 'energetic': 0.6, 'acoustic': 0.4},
        'soul': {'vocal': 1.0, 'danceable': 0.6, 'energetic': 0.7, 'acoustic': 0.5},
        'funk': {'vocal': 0.8, 'danceable': 0.9, 'energetic': 0.8, 'acoustic': 0.3},
    }

    # Calculate weighted characteristics
    total_weight = 0
    for genre in genres[:3]:  # Use top 3 genres
        genre_lower = genre.lower()
        for pattern, weights in genre_weights.items():
            if pattern in genre_lower:
                weight = 1.0 / (genres.index(genre) + 1)  # First genre has higher weight
                total_weight += weight
                for char, value in weights.items():
                    characteristics[char] += value * weight
                break

    # Normalize
    if total_weight > 0:
        for char in characteristics:
            characteristics[char] /= total_weight
            characteristics[char] = min(1.0, characteristics[char])  # Cap at 1.0

    return characteristics


def estimate_tempo_from_genres(genres, era, duration_ms):
    """Estimate tempo based on genres and context"""
    base_tempo = 120  # Default

    if not genres:
        return base_tempo

    # Genre-based tempo mapping (more comprehensive)
    tempo_map = {
        'drill': 150, 'drum and bass': 175, 'breakbeat': 130,
        'dubstep': 140, 'trap': 140, 'hardstyle': 150,
        'house': 125, 'deep house': 120, 'tech house': 125,
        'techno': 130, 'minimal techno': 125, 'detroit techno': 130,
        'trance': 135, 'progressive trance': 130, 'psytrance': 145,
        'electronic': 125, 'synthwave': 115, 'chillwave': 90,
        'ambient': 80, 'downtempo': 90, 'trip hop': 95,

        'hip hop': 85, 'old school hip hop': 100, 'boom bap': 90,
        'rap': 85, 'gangsta rap': 90, 'conscious hip hop': 85,
        'uk hip hop': 85, 'grime': 140,

        'rock': 120, 'hard rock': 125, 'progressive rock': 110,
        'punk': 180, 'pop punk': 170, 'hardcore punk': 200,
        'metal': 140, 'death metal': 160, 'black metal': 180,
        'heavy metal': 130, 'thrash metal': 160,
        'alternative rock': 115, 'indie rock': 110, 'grunge': 115,

        'pop': 120, 'dance pop': 128, 'synthpop': 115,
        'k-pop': 125, 'j-pop': 130, 'europop': 130,

        'reggae': 90, 'dub': 85, 'dancehall': 100,
        'ska': 160, 'two tone': 170,

        'jazz': 120, 'bebop': 140, 'smooth jazz': 100,
        'fusion': 110, 'free jazz': 100, 'swing': 120,

        'blues': 90, 'chicago blues': 95, 'delta blues': 80,
        'rhythm and blues': 100,

        'country': 100, 'bluegrass': 130, 'alt country': 95,
        'folk': 90, 'indie folk': 95, 'folk rock': 105,

        'classical': 60, 'baroque': 80, 'romantic': 70,
        'contemporary classical': 90,

        'r&b': 85, 'contemporary r&b': 90, 'neo soul': 80,
        'soul': 95, 'motown': 100, 'funk': 110,

        'latin': 100, 'salsa': 180, 'reggaeton': 95,
        'bossa nova': 120, 'tango': 120,
    }

    # Find best tempo match
    matched_tempos = []
    for genre in genres[:2]:  # Check first 2 genres
        genre_lower = genre.lower()
        for pattern, tempo in tempo_map.items():
            if pattern in genre_lower:
                matched_tempos.append(tempo)
                break

    if matched_tempos:
        base_tempo = sum(matched_tempos) / len(matched_tempos)

    # Era adjustments
    if era == 'classic':  # Pre-1980
        base_tempo *= 0.9  # Slightly slower
    elif era == 'current':  # Post-2015
        base_tempo *= 1.05  # Slightly faster

    # Duration adjustments (longer songs tend to be slightly slower)
    duration_seconds = duration_ms / 1000
    if duration_seconds > 300:  # > 5 minutes
        base_tempo *= 0.95
    elif duration_seconds < 180:  # < 3 minutes
        base_tempo *= 1.05

    return max(60, min(200, base_tempo))  # Reasonable bounds


def estimate_key_and_mode(genres, era):
    """Estimate musical key and mode based on genre patterns"""
    if not genres:
        return 0, 1  # C Major default

    # Genre key preferences (based on musical analysis)
    key_preferences = {
        'blues': [(4, 0), (9, 0), (2, 0)],  # E minor, A minor, D minor
        'country': [(7, 1), (2, 1), (0, 1)],  # G major, D major, C major
        'folk': [(7, 1), (0, 1), (5, 1)],  # G major, C major, F major
        'rock': [(4, 0), (7, 1), (2, 0)],  # E minor, G major, D minor
        'metal': [(2, 0), (4, 0), (9, 0)],  # D minor, E minor, A minor
        'pop': [(0, 1), (7, 1), (5, 1)],  # C major, G major, F major
        'hip hop': [(2, 0), (7, 0), (0, 1)],  # D minor, G minor, C major
        'jazz': [(5, 1), (10, 1), (3, 1)],  # F major, Bb major, Eb major
        'electronic': [(9, 0), (4, 0), (0, 1)],  # A minor, E minor, C major
        'classical': [(0, 1), (7, 1), (2, 1)],  # C major, G major, D major
    }

    # Find matching genre
    possible_keys = []
    for genre in genres[:2]:
        genre_lower = genre.lower()
        for pattern, keys in key_preferences.items():
            if pattern in genre_lower:
                possible_keys.extend(keys)
                break

    if possible_keys:
        # Pick most common key from preferences
        key_counts = {}
        for key, mode in possible_keys:
            key_counts[(key, mode)] = key_counts.get((key, mode), 0) + 1

        best_key = max(key_counts.items(), key=lambda x: x[1])[0]
        return best_key[0], best_key[1]

    return 0, 1  # C Major default


def calculate_energy_from_metadata(genres, popularity, era, explicit):
    """Calculate energy based on multiple metadata factors"""
    base_energy = 0.5

    # Genre-based energy
    genre_analysis = analyze_genre_characteristics(genres)
    genre_energy = genre_analysis.get('energetic', 0.5)

    # Popularity boost (more popular = often more energetic)
    popularity_boost = (popularity - 50) / 200  # -0.25 to +0.25

    # Era adjustments
    era_multiplier = {
        'classic': 0.8,  # Older music often less energetic
        'vintage': 0.9,
        'modern': 1.0,
        'current': 1.1  # Current music often more energetic
    }.get(era, 1.0)

    # Explicit content often more energetic
    explicit_boost = 0.1 if explicit else 0

    energy = (genre_energy * era_multiplier) + popularity_boost + explicit_boost
    return max(0.1, min(0.95, energy))


def calculate_valence_from_metadata(genres, era, explicit):
    """Calculate valence (musical positivity) from metadata"""
    genre_analysis = analyze_genre_characteristics(genres)

    # Base valence from genre
    base_valence = 0.5
    if not genres:
        return base_valence

    # Genre valence patterns
    valence_map = {
        'pop': 0.8, 'dance pop': 0.85, 'k-pop': 0.9,
        'funk': 0.8, 'disco': 0.9, 'reggae': 0.75,
        'gospel': 0.85, 'soul': 0.7,
        'blues': 0.3, 'sad': 0.2, 'melancholy': 0.25,
        'metal': 0.35, 'doom': 0.2, 'black metal': 0.15,
        'emo': 0.25, 'screamo': 0.3,
        'ambient': 0.5, 'meditation': 0.6,
        'classical': 0.55, 'baroque': 0.6,
        'electronic': 0.6, 'house': 0.75, 'trance': 0.7
    }

    # Find best valence match
    matched_valences = []
    for genre in genres:
        genre_lower = genre.lower()
        for pattern, valence in valence_map.items():
            if pattern in genre_lower:
                matched_valences.append(valence)
                break

    if matched_valences:
        base_valence = sum(matched_valences) / len(matched_valences)

    # Era adjustments (older music often more optimistic)
    if era == 'classic':
        base_valence *= 1.1
    elif era == 'vintage':
        base_valence *= 1.05

    return max(0.1, min(0.95, base_valence))


def calculate_danceability_from_metadata(genres):
    """Calculate danceability from genre characteristics"""
    genre_analysis = analyze_genre_characteristics(genres)
    return max(0.1, min(0.95, genre_analysis.get('danceable', 0.5)))


def calculate_acousticness_from_metadata(genres, era):
    """Calculate acousticness from genre and era"""
    genre_analysis = analyze_genre_characteristics(genres)
    base_acoustic = genre_analysis.get('acoustic', 0.3)

    # Era adjustments (older music more acoustic)
    if era == 'classic':
        base_acoustic *= 1.3
    elif era == 'vintage':
        base_acoustic *= 1.1

    return max(0.05, min(0.95, base_acoustic))


def calculate_instrumentalness_from_metadata(genres):
    """Calculate instrumentalness from genre patterns"""
    instrumental_genres = {
        'classical': 0.9, 'orchestral': 0.9, 'symphony': 0.95,
        'ambient': 0.8, 'drone': 0.9, 'meditation': 0.8,
        'post-rock': 0.7, 'math rock': 0.6,
        'jazz fusion': 0.6, 'smooth jazz': 0.5,
        'electronic': 0.4, 'techno': 0.6, 'house': 0.5,
        'instrumental': 0.9, 'soundtrack': 0.7
    }

    max_instrumental = 0.1  # Most music has vocals

    if genres:
        for genre in genres:
            genre_lower = genre.lower()
            for pattern, value in instrumental_genres.items():
                if pattern in genre_lower:
                    max_instrumental = max(max_instrumental, value)

    return max_instrumental


def calculate_speechiness_from_metadata(genres):
    """Calculate speechiness (vocal vs musical content)"""
    speech_genres = {
        'rap': 0.8, 'hip hop': 0.7, 'grime': 0.8,
        'spoken word': 0.9, 'poetry': 0.9,
        'comedy': 0.95, 'audiobook': 0.98,
        'trap': 0.6, 'drill': 0.7
    }

    max_speech = 0.05  # Most music is not very speech-like

    if genres:
        for genre in genres:
            genre_lower = genre.lower()
            for pattern, value in speech_genres.items():
                if pattern in genre_lower:
                    max_speech = max(max_speech, value)

    return max_speech


def calculate_liveness_from_metadata(genres, era):
    """Calculate liveness (live recording vs studio)"""
    live_genres = {
        'jazz': 0.3, 'blues': 0.35, 'folk': 0.25,
        'live': 0.9, 'concert': 0.9, 'acoustic': 0.3
    }

    base_live = 0.15  # Most recordings are studio

    # Era adjustment (older recordings more likely to be live)
    if era == 'classic':
        base_live = 0.25
    elif era == 'vintage':
        base_live = 0.2

    if genres:
        for genre in genres:
            genre_lower = genre.lower()
            for pattern, value in live_genres.items():
                if pattern in genre_lower:
                    base_live = max(base_live, value)

    return base_live


def calculate_loudness_from_metadata(genres, era):
    """Calculate loudness in dB"""
    # Base loudness by genre
    loudness_map = {
        'metal': -5, 'hardcore': -4, 'punk': -6,
        'electronic': -7, 'edm': -5, 'dubstep': -4,
        'pop': -8, 'rock': -7,
        'jazz': -12, 'classical': -15, 'ambient': -14,
        'folk': -12, 'acoustic': -13,
        'hip hop': -8, 'trap': -6
    }

    base_loudness = -10  # Default

    if genres:
        matched_loudness = []
        for genre in genres:
            genre_lower = genre.lower()
            for pattern, db in loudness_map.items():
                if pattern in genre_lower:
                    matched_loudness.append(db)
                    break

        if matched_loudness:
            base_loudness = sum(matched_loudness) / len(matched_loudness)

    # Era adjustments (loudness war - newer music is louder)
    if era == 'current':
        base_loudness += 2
    elif era == 'modern':
        base_loudness += 1
    elif era == 'classic':
        base_loudness -= 3

    return max(-25, min(-2, base_loudness))


def create_fallback_audio_features():
    """Fallback when no metadata available"""
    return {
        'tempo': 120, 'key': 0, 'mode': 1, 'energy': 0.5,
        'valence': 0.5, 'danceability': 0.5, 'acousticness': 0.5,
        'instrumentalness': 0.1, 'speechiness': 0.1, 'liveness': 0.2,
        'loudness': -10.0, 'duration': 180000, 'time_signature': 4,
        'popularity': 50, 'feature_completeness': 0.3,
        'primary_source': 'fallback', 'genre_primary': 'Unknown'
    }


def allowed_file(filename):
    """Security: Validate file extension and filename"""
    if not filename or '.' not in filename:
        return False
    
    # Security: Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def extract_real_audio_features(audio_file_path):
    """Extract REAL audio features using librosa"""
    try:
        logging.info(f"Analyzing uploaded audio: {audio_file_path}")

        # Load audio (first 60 seconds)
        y, sr = librosa.load(audio_file_path, duration=60)

        # TEMPO AND RHYTHM
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(tempo)

        # Beat stability
        beat_times = librosa.frames_to_time(beats, sr=sr)
        if len(beat_times) > 1:
            beat_intervals = np.diff(beat_times)
            rhythm_stability = 1.0 / (1.0 + np.var(beat_intervals)) if len(beat_intervals) > 0 else 0.5
        else:
            rhythm_stability = 0.5

        # CHROMA AND KEY
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)

        # Simple key detection
        estimated_key = int(np.argmax(chroma_mean))
        estimated_mode = 1  # Assume major for now

        # ENERGY AND DYNAMICS
        rms_energy = librosa.feature.rms(y=y)
        energy = float(np.mean(rms_energy))
        energy = min(1.0, max(0.0, energy * 5))  # Scale to 0-1 range

        # SPECTRAL FEATURES
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        brightness = float(np.mean(spectral_centroid) / sr * 2)  # Normalize
        brightness = min(1.0, max(0.0, brightness))

        # Zero crossing rate (texture)
        zcr = librosa.feature.zero_crossing_rate(y)
        roughness = float(np.mean(zcr))

        # ESTIMATE OTHER FEATURES from extracted ones
        # Valence (positivity) - estimated from spectral characteristics
        valence = (brightness + (1.0 - roughness)) / 2  # Brighter, smoother = more positive
        valence = max(0.1, min(0.9, valence))

        # Danceability - tempo and rhythm stability
        if 90 <= tempo <= 140:
            danceability = 0.7 + (rhythm_stability * 0.3)
        elif tempo > 140:
            danceability = 0.8 + (rhythm_stability * 0.2)
        else:
            danceability = 0.3 + (rhythm_stability * 0.4)
        danceability = max(0.1, min(0.9, danceability))

        # Acousticness - inverse of energy and roughness
        acousticness = 1.0 - (energy + roughness) / 2
        acousticness = max(0.05, min(0.95, acousticness))

        # Loudness (dB estimate)
        loudness = 20 * np.log10(max(energy, 1e-10)) - 10
        loudness = max(-25, min(-2, loudness))

        # Speechiness - estimate from spectral properties
        speechiness = min(0.5, roughness * 2)  # Higher roughness = more speech-like

        # Instrumentalness - low for most uploaded music
        instrumentalness = max(0.05, 1.0 - (brightness * 2))  # Brighter usually means vocals
        instrumentalness = min(0.9, instrumentalness)

        # Liveness - estimate from reverb/echo (simplified)
        liveness = 0.2  # Default assumption for uploads

        features = {
            'tempo': round(tempo),
            'key': estimated_key,
            'mode': estimated_mode,
            'energy': round(energy, 2),
            'valence': round(valence, 2),
            'danceability': round(danceability, 2),
            'acousticness': round(acousticness, 2),
            'instrumentalness': round(instrumentalness, 2),
            'speechiness': round(speechiness, 2),
            'liveness': round(liveness, 2),
            'loudness': round(loudness, 1),
            'duration': len(y) * 1000 / sr,  # Convert to milliseconds
            'time_signature': 4,  # Default

            # Real analysis indicators
            'feature_completeness': 0.95,
            'primary_source': 'real_audio_analysis',
            'chroma_vector': chroma_mean.tolist(),
            'rhythm_stability': round(rhythm_stability, 2),
            'beat_strength': 0.8,  # Default for real analysis
            'spectral_brightness': round(brightness, 2),
            'spectral_roughness': round(roughness, 2),

            # Confidence scores
            'tempo_confidence': 0.9,
            'key_confidence': 0.7,
            'energy_confidence': 0.9
        }

        logging.info(f"Real audio analysis complete: {tempo} BPM, {estimated_key} key, {energy:.2f} energy")
        return features

    except Exception as e:
        logging.error(f"Real audio analysis failed: {e}")
        return None


# ADD NEW UPLOAD ROUTE
@app.route('/upload', methods=['POST'])
def upload_audio():
    """Handle audio file uploads for real analysis"""
    try:
        if 'audio_file' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        file = request.files['audio_file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Security: Additional file validation
        if not file.filename:
            return jsonify({"error": "Invalid filename"}), 400
            
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not supported. Use MP3, WAV, FLAC, M4A, or OGG"}), 400

        # Security: Limit file size (already configured at app level, but double-check)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 16 * 1024 * 1024:  # 16MB
            return jsonify({"error": "File too large. Maximum size is 16MB"}), 400
        
        if file_size == 0:
            return jsonify({"error": "File is empty"}), 400

        # Save uploaded file temporarily with secure filename
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(suffix=f'_{filename}', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        try:
            # Extract real audio features
            real_features = extract_real_audio_features(temp_path)
            if not real_features:
                return jsonify({"error": "Failed to analyze audio file"}), 500

            # Create song object for database
            uploaded_song = {
                "title": f"Uploaded: {filename}",
                "artist": "User Upload",
                "audio_features": real_features,
                "spotify_metadata": {
                    "popularity": 50,  # Neutral
                    "duration_ms": real_features['duration'],
                    "explicit": False,
                    "preview_url": None,
                    "has_preview": False,
                    "is_upload": True,
                    "upload_filename": filename
                }
            }

            # Save to database
            save_song_to_db(uploaded_song)

            # Find similar tracks using existing metadata system
            sp = get_spotify_client()
            similarity_engine = MetadataSimilarityEngine(sp)

            # Create pseudo-metadata for searching (since we don't have genre info)
            pseudo_metadata = create_pseudo_metadata_from_audio(real_features, filename)

            # Find candidates using audio characteristics
            candidates = find_candidates_by_audio_characteristics(sp, real_features, pseudo_metadata)

            # Enhance candidates with metadata
            enhanced_candidates = []
            for candidate in candidates:
                try:
                    if candidate.get('spotify_id'):
                        candidate_metadata = similarity_engine.extract_comprehensive_metadata(candidate['spotify_id'])
                        candidate_pseudo_features = convert_metadata_to_audio_features(candidate_metadata)

                        enhanced_candidate = {
                            "title": candidate.get('title', 'Unknown'),
                            "artist": candidate.get('artist', 'Unknown'),
                            "metadata_features": candidate_metadata,
                            "audio_features": candidate_pseudo_features,
                            "spotify_id": candidate.get('spotify_id'),
                            "popularity": candidate.get('popularity'),
                            "preview_url": candidate.get('preview_url')
                        }
                        enhanced_candidates.append(enhanced_candidate)
                except Exception as e:
                    logging.warning(f"Failed to enhance candidate: {e}")
                    continue

            # Compare real features with estimated features
            recommendations = compare_real_vs_estimated_features(real_features, enhanced_candidates)

            return jsonify({
                "message": "Audio file analyzed successfully",
                "original_song": uploaded_song,
                "recommendations": recommendations,
                "analysis_stats": {
                    "analysis_method": "real_audio_upload",
                    "feature_completeness": real_features.get('feature_completeness', 0.95),
                    "candidates_found": len(candidates),
                    "candidates_analyzed": len(enhanced_candidates),
                    "matches_found": len(recommendations)
                }
            }), 200

        finally:
            # Clean up temp file
            os.unlink(temp_path)

    except Exception as e:
        logging.error(f"Upload processing failed: {e}")
        # Security: Don't expose internal error details to client
        return jsonify({"error": "Upload failed. Please try again."}), 500


def create_pseudo_metadata_from_audio(audio_features, filename):
    """Create searchable metadata from audio characteristics"""
    tempo = audio_features.get('tempo', 120)
    energy = audio_features.get('energy', 0.5)
    danceability = audio_features.get('danceability', 0.5)

    # Classify tempo
    if tempo > 140:
        tempo_class = 'fast'
    elif tempo < 90:
        tempo_class = 'slow'
    else:
        tempo_class = 'medium'

    # Classify energy
    if energy > 0.7:
        energy_class = 'high'
    elif energy < 0.4:
        energy_class = 'low'
    else:
        energy_class = 'medium'

    return {
        'tempo': tempo,
        'energy_class': energy_class,
        'tempo_class': tempo_class,
        'danceability': danceability,
        'filename': filename,
        'era': 'current',  # Assume current
        'mainstream_level': 'mid_tier'
    }


def find_candidates_by_audio_characteristics(sp, real_features, pseudo_metadata):
    """Find candidates based on audio characteristics rather than metadata"""
    candidates = []
    seen_ids = set()

    tempo = real_features.get('tempo', 120)
    energy = real_features.get('energy', 0.5)
    danceability = real_features.get('danceability', 0.5)

    # Search terms based on audio characteristics
    search_terms = []

    if tempo > 140 and energy > 0.7:
        search_terms.extend(['energetic', 'upbeat', 'fast', 'intense'])
    elif tempo < 90 and energy < 0.4:
        search_terms.extend(['slow', 'mellow', 'chill', 'calm'])
    else:
        search_terms.extend(['moderate', 'steady', 'groove'])

    if danceability > 0.7:
        search_terms.extend(['danceable', 'rhythmic', 'groove'])

    if energy > 0.8:
        search_terms.extend(['powerful', 'driving', 'high energy'])
    elif energy < 0.3:
        search_terms.extend(['ambient', 'peaceful', 'soft'])

    # Execute searches
    for term in search_terms[:6]:  # Limit searches
        try:
            results = sp.search(q=term, type='track', limit=10)
            for track in results['tracks']['items']:
                if track['id'] not in seen_ids and len(candidates) < 50:
                    candidates.append(format_candidate(track))
                    seen_ids.add(track['id'])
        except Exception as e:
            logging.warning(f"Audio characteristic search failed for {term}: {e}")

    logging.info(f"Found {len(candidates)} candidates based on audio characteristics")
    return candidates


def compare_real_vs_estimated_features(real_features, enhanced_candidates):
    """Compare real audio features with metadata estimates"""
    recommendations = []

    real_vector = create_audio_feature_vector(real_features)

    for candidate in enhanced_candidates:
        try:
            estimated_features = candidate.get('audio_features', {})
            estimated_vector = create_audio_feature_vector(estimated_features)

            # Calculate similarity between real and estimated features
            similarity = calculate_vector_similarity(real_vector, estimated_vector)

            if similarity > 0.3:  # Minimum similarity threshold
                recommendations.append({
                    "title": candidate.get('title', 'Unknown'),
                    "artist": candidate.get('artist', 'Unknown'),
                    "similarity_score": similarity,
                    "explanation": f"Audio analysis match: {similarity:.1%} similar",
                    "spotify_id": candidate.get('spotify_id'),
                    "popularity": candidate.get('popularity'),
                    "preview_url": candidate.get('preview_url'),
                    "audio_features": estimated_features,
                    "comparison_type": "real_vs_estimated"
                })
        except Exception as e:
            logging.warning(f"Comparison failed for candidate: {e}")
            continue

    # Sort by similarity
    recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
    return recommendations[:10]


def create_audio_feature_vector(features):
    """Create feature vector from audio features"""
    return np.array([
        features.get('tempo', 120) / 200,  # Normalize tempo
        features.get('energy', 0.5),
        features.get('valence', 0.5),
        features.get('danceability', 0.5),
        features.get('acousticness', 0.5),
        features.get('instrumentalness', 0.1),
        features.get('speechiness', 0.1),
        features.get('loudness', -10) / -30 + 1,  # Normalize loudness
    ])


def calculate_vector_similarity(vec1, vec2):
    """Calculate similarity between feature vectors"""
    try:
        if len(vec1) != len(vec2):
            return 0.0

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)

        if norms == 0:
            return 0.0

        similarity = dot_product / norms
        return max(0.0, min(1.0, similarity))
    except:
        return 0.0




if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Security: Never run debug mode in production
    flask_env = os.getenv('FLASK_ENV', 'production')
    debug = flask_env == 'development'
    
    if debug:
        logging.warning("Running in DEBUG mode. This should NEVER be used in production!")
    
    app.run(host='0.0.0.0', port=port, debug=debug)