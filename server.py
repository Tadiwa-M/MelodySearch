from flask import Flask, request, jsonify, render_template, redirect, session
import logging
import os
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from song_db import save_song_to_db, load_song_db
from library_manager import (
    add_song_to_library, get_library_songs, remove_song_from_library,
    create_collection, get_collections, get_collection_with_songs,
    update_collection, delete_collection, add_song_to_collection,
    remove_song_from_collection, get_library_stats
)
from image_service import get_image_service
from mood_board_manager import (
    save_mood_board, load_mood_board, get_user_mood_boards,
    delete_mood_board, add_image_to_board, remove_image_from_board,
    generate_share_link
)
from flask_session import Session
import requests
import tempfile
from feature_extraction import HybridFeatureExtractor
from metadata_similarity_engine import MetadataSimilarityEngine
from song_identifier import SongIdentifier
import random
import time
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import librosa
import numpy as np
from urllib.parse import urlparse

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
    # Only set HSTS when using HTTPS
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Don't set CSP yet as it may need tuning for the application
    return response

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a', 'ogg', 'webm'}

# Security: Configure logging level based on environment
log_level = logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Helper function for standardized error responses
def create_error_response(error_type, message, details=None, suggestions=None, status_code=400):
    """
    Create a standardized error response with helpful information.
    
    Args:
        error_type: Type of error (e.g., 'validation_error', 'api_error')
        message: User-friendly error message
        details: Optional technical details
        suggestions: Optional list of suggestions to fix the error
        status_code: HTTP status code
    
    Returns:
        tuple: (jsonify response, status_code)
    """
    response = {
        'error': error_type,
        'message': message,
        'success': False
    }
    
    if details:
        response['details'] = details
    
    if suggestions:
        response['suggestions'] = suggestions if isinstance(suggestions, list) else [suggestions]
    
    # Add timestamp for debugging
    response['timestamp'] = datetime.now().isoformat()
    
    return jsonify(response), status_code


def validate_string_input(value, field_name, max_length=200, required=True):
    """
    Validate string input with comprehensive checks.
    
    Args:
        value: Input value to validate
        field_name: Name of the field for error messages
        max_length: Maximum allowed length
        required: Whether the field is required
    
    Returns:
        tuple: (is_valid, error_message, sanitized_value)
    """
    # Check if required
    if required and (not value or not str(value).strip()):
        return False, f"{field_name} is required", None
    
    if not value:
        return True, None, None
    
    # Convert to string and strip
    sanitized = str(value).strip()
    
    # Check length
    if len(sanitized) > max_length:
        return False, f"{field_name} is too long (max {max_length} characters)", None
    
    # Check for dangerous characters (XSS prevention)
    dangerous_chars = re.search(r'[<>\"\\]', sanitized)
    if dangerous_chars:
        return False, f"{field_name} contains invalid characters", None
    
    return True, None, sanitized

# Spotify API credentials and redirect URI
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5000/callback')

# Validate required credentials
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables must be set")
SCOPE = 'user-read-private user-read-email user-read-currently-playing user-read-playback-state user-read-recently-played user-top-read user-library-read'
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
    auth_manager = get_auth_manager()
    token_info = auth_manager.get_access_token(code)
    session['token_info'] = token_info
    session['is_authenticated'] = True
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
    return redirect('/')


@app.route('/auth-status', methods=['GET'])
def auth_status():
    """Check if user is authenticated with Spotify"""
    is_authenticated = session.get('is_authenticated', False)
    token_info = session.get('token_info')

    if is_authenticated and token_info:
        # Try to get user info
        try:
            auth_manager = get_auth_manager()
            sp = spotipy.Spotify(auth_manager=auth_manager)
            user_info = sp.current_user()
            return jsonify({
                'authenticated': True,
                'user': {
                    'display_name': user_info.get('display_name'),
                    'email': user_info.get('email')
                }
            })
        except Exception as e:
            logging.error(f"Error checking auth status: {e}")
            session.clear()
            return jsonify({'authenticated': False})

    return jsonify({'authenticated': False})


# Replace your search route with this clean metadata-only version

@app.route('/search', methods=['POST'])
def search_song():
    """
    Search for a song and find similar tracks using metadata-based analysis.
    Enhanced with comprehensive error handling and user-friendly messages.
    """
    # Note: Authentication not required for search - uses Spotify Client Credentials
    # User authentication (OAuth) is only needed for user-specific features (playlists, etc.)
    # This allows public song search without login, fixing HTTP 401 errors
    
    try:
        # Security: Validate content type
        if not request.is_json:
            return create_error_response(
                'invalid_request',
                'Invalid request format',
                details='Content-Type must be application/json',
                suggestions=['Ensure your request has Content-Type: application/json header'],
                status_code=400
            )
            
        data = request.json
        
        # Security: Validate JSON structure
        if not isinstance(data, dict):
            return create_error_response(
                'invalid_json',
                'Invalid JSON format',
                details='Request body must be a JSON object',
                status_code=400
            )
            
        song_name = data.get('song_name', '').strip()

        # Enhanced input validation using helper function
        is_valid, error_msg, song_name = validate_string_input(
            song_name, 
            'Song name', 
            max_length=200, 
            required=True
        )
        
        if not is_valid:
            return create_error_response(
                'validation_error',
                error_msg,
                suggestions=[
                    'Enter a valid song name',
                    'Song name should be less than 200 characters',
                    'Avoid special characters like <, >, ", \\'
                ],
                status_code=400
            )

        logging.info(f"Searching for song: {song_name}")
        
        # Get Spotify client with error handling
        try:
            sp = get_spotify_client()
        except Exception as e:
            logging.error(f"Failed to initialize Spotify client: {e}")
            return create_error_response(
                'spotify_auth_error',
                'Failed to connect to Spotify',
                details='Could not initialize Spotify client',
                suggestions=[
                    'Check that SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set',
                    'Verify your Spotify API credentials are valid'
                ],
                status_code=503
            )

        # Search for the original song with retry logic
        max_retries = 3
        retry_delay = 1
        results = None
        
        for attempt in range(max_retries):
            try:
                results = sp.search(q=song_name, type='track', limit=1)
                break
            except spotipy.SpotifyException as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Spotify search attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logging.error(f"Spotify search failed after {max_retries} attempts: {e}")
                    return create_error_response(
                        'spotify_api_error',
                        'Spotify search failed',
                        details=str(e),
                        suggestions=[
                            'Try again in a few moments',
                            'Check your internet connection',
                            'Try searching with a different song name'
                        ],
                        status_code=503
                    )
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logging.warning(f"Spotify search timeout, retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    return create_error_response(
                        'timeout_error',
                        'Request timed out',
                        details='The search request took too long',
                        suggestions=['Try again with a shorter or more specific song name'],
                        status_code=504
                    )
            except requests.exceptions.ConnectionError:
                return create_error_response(
                    'connection_error',
                    'Network connection error',
                    details='Could not connect to Spotify servers',
                    suggestions=[
                        'Check your internet connection',
                        'Try again in a few moments'
                    ],
                    status_code=503
                )
        
        if not results or not results['tracks']['items']:
            return create_error_response(
                'not_found',
                f'Song "{song_name}" not found',
                details='No matching songs found in Spotify catalog',
                suggestions=[
                    'Check the spelling of the song name',
                    'Try including the artist name in the search',
                    'Try a more popular song or different search terms'
                ],
                status_code=404
            )

        track = results['tracks']['items'][0]

        # NEW: Use metadata-based similarity engine with error handling
        try:
            similarity_engine = MetadataSimilarityEngine(sp)
            metadata_features = similarity_engine.extract_comprehensive_metadata(
                track['id'],
                track
            )
        except Exception as e:
            logging.error(f"Metadata extraction failed: {e}")
            # Graceful degradation - continue with limited features
            metadata_features = {
                'popularity': track.get('popularity', 50),
                'duration_ms': track.get('duration_ms', 180000),
                'explicit': track.get('explicit', False),
                'feature_completeness': 0.3
            }

        logging.debug(f"Metadata analysis completeness: {metadata_features.get('feature_completeness', 0):.2%}")

        # Convert metadata to pseudo audio features for frontend compatibility
        try:
            pseudo_audio_features = convert_metadata_to_audio_features(metadata_features)
        except Exception as e:
            logging.error(f"Feature conversion failed: {e}")
            pseudo_audio_features = create_fallback_audio_features()

        # Structure the original song data
        original_song = {
            "title": track['name'],
            "artist": track['artists'][0]['name'] if track.get('artists') else 'Unknown',
            "audio_features": pseudo_audio_features,  # Frontend expects this key
            "spotify_metadata": {
                "popularity": track.get('popularity', 0),
                "duration_ms": track.get('duration_ms', 0),
                "explicit": track.get('explicit', False),
                "preview_url": track.get('preview_url'),
                "has_preview": track.get('preview_url') is not None,
                "spotify_id": track['id'],
                "genres": metadata_features.get('artist_genres', []),
                "release_year": metadata_features.get('release_year'),
            }
        }

        # Save to database with error handling
        try:
            save_song_to_db(original_song)
        except Exception as e:
            logging.error(f"Failed to save song to database: {e}")
            # Non-critical error, continue anyway

        # Find candidate tracks using metadata-based search
        logging.debug("Finding candidate tracks using metadata strategies...")
        try:
            candidate_recommendations = find_metadata_based_candidates(sp, track, metadata_features, limit=50)
        except Exception as e:
            logging.error(f"Candidate search failed: {e}")
            candidate_recommendations = []

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
                    try:
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
                    except Exception as e2:
                        logging.error(f"Failed to format candidate: {e2}")
                        continue

        # Return results (even if partial)
        return jsonify({
            "message": "Song analyzed successfully",
            "success": True,
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
        return create_error_response(
            'spotify_api_error',
            'Spotify service error',
            details='An error occurred while communicating with Spotify',
            suggestions=[
                'Try again in a few moments',
                'Check if Spotify services are operational'
            ],
            status_code=503
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error: {e}")
        return create_error_response(
            'network_error',
            'Network error occurred',
            details='Could not complete the request due to network issues',
            suggestions=[
                'Check your internet connection',
                'Try again in a few moments'
            ],
            status_code=503
        )
    except Exception as e:
        logging.error(f"Unexpected error in /search: {e}", exc_info=True)
        return create_error_response(
            'internal_error',
            'An unexpected error occurred',
            details='The server encountered an error while processing your request',
            suggestions=[
                'Try again',
                'If the problem persists, contact support'
            ],
            status_code=500
        )


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
@app.route('/similar-songs', methods=['POST'])
def get_similar_songs():
    """
    Generate a list of songs similar to a given song (title and artist).
    Returns metadata for each similar song.
    Enhanced with comprehensive error handling and validation.
    """
    # Note: Authentication not required - uses Spotify Client Credentials
    # User authentication (OAuth) is only needed for user-specific features
    
    try:
        # Validate content type
        if not request.is_json:
            return create_error_response(
                'invalid_request',
                'Invalid request format',
                details='Content-Type must be application/json',
                status_code=400
            )
        
        data = request.json
        
        # Validate JSON structure
        if not isinstance(data, dict):
            return create_error_response(
                'invalid_json',
                'Invalid JSON format',
                status_code=400
            )
        
        # Validate title
        is_valid, error_msg, title = validate_string_input(
            data.get('title'), 
            'Song title', 
            max_length=200, 
            required=True
        )
        if not is_valid:
            return create_error_response(
                'validation_error',
                error_msg,
                suggestions=['Provide a valid song title'],
                status_code=400
            )
        
        # Validate artist
        is_valid, error_msg, artist = validate_string_input(
            data.get('artist'), 
            'Artist name', 
            max_length=200, 
            required=True
        )
        if not is_valid:
            return create_error_response(
                'validation_error',
                error_msg,
                suggestions=['Provide a valid artist name'],
                status_code=400
            )
        
        logging.info(f"Searching for: '{title}' by '{artist}'")
        
        # Get Spotify client with error handling
        try:
            sp = get_spotify_client()
        except Exception as e:
            logging.error(f"Failed to initialize Spotify client: {e}")
            return create_error_response(
                'spotify_auth_error',
                'Failed to connect to Spotify',
                suggestions=['Check Spotify API credentials configuration'],
                status_code=503
            )
        
        # Search for the song using both title and artist for better accuracy
        search_query = f"track:{title} artist:{artist}"
        
        # Implement retry logic for search
        max_retries = 3
        results = None
        
        for attempt in range(max_retries):
            try:
                results = sp.search(q=search_query, type='track', limit=5)
                break
            except (spotipy.SpotifyException, requests.exceptions.RequestException) as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Search attempt {attempt + 1} failed, retrying...")
                    time.sleep(1 * (attempt + 1))
                else:
                    logging.error(f"Search failed after {max_retries} attempts: {e}")
                    return create_error_response(
                        'search_failed',
                        'Could not search Spotify',
                        details=str(e),
                        suggestions=['Try again in a few moments', 'Check your connection'],
                        status_code=503
                    )
        
        if not results or not results['tracks']['items']:
            # Fallback: try without strict formatting
            try:
                search_query = f"{title} {artist}"
                results = sp.search(q=search_query, type='track', limit=5)
            except Exception as e:
                logging.error(f"Fallback search failed: {e}")
            
            if not results or not results['tracks']['items']:
                return create_error_response(
                    'not_found',
                    f'Song "{title}" by "{artist}" not found',
                    suggestions=[
                        'Check the spelling of the song title and artist',
                        'Try a more well-known song',
                        'Ensure the song is available on Spotify'
                    ],
                    status_code=404
                )
        
        # Find the best match from results
        track = results['tracks']['items'][0]
        
        # Use metadata-based similarity engine with error handling
        try:
            similarity_engine = MetadataSimilarityEngine(sp)
            metadata_features = similarity_engine.extract_comprehensive_metadata(
                track['id'],
                track
            )
        except Exception as e:
            logging.error(f"Metadata extraction failed: {e}")
            # Use minimal features if extraction fails
            metadata_features = {
                'popularity': track.get('popularity', 50),
                'duration_ms': track.get('duration_ms', 180000),
                'feature_completeness': 0.3
            }
        
        logging.debug(f"Found: '{track['name']}' by '{track['artists'][0]['name']}'")
        logging.debug(f"Metadata completeness: {metadata_features.get('feature_completeness', 0):.2%}")
        
        # Convert metadata to audio features for response
        try:
            pseudo_audio_features = convert_metadata_to_audio_features(metadata_features)
        except Exception as e:
            logging.error(f"Feature conversion failed: {e}")
            pseudo_audio_features = create_fallback_audio_features()
        
        # Structure the original song data
        original_song = {
            "title": track['name'],
            "artist": track['artists'][0]['name'],
            "spotify_id": track['id'],
            "popularity": track.get('popularity', 0),
            "duration_ms": track.get('duration_ms', 0),
            "explicit": track.get('explicit', False),
            "preview_url": track.get('preview_url'),
            "album": track['album']['name'] if track.get('album') else 'Unknown',
            "release_date": track['album'].get('release_date', 'Unknown') if track.get('album') else 'Unknown',
            "genres": metadata_features.get('artist_genres', []),
            "audio_features": pseudo_audio_features
        }
        
        # Find similar songs with comprehensive error handling
        logging.debug("Finding similar songs...")
        try:
            candidate_recommendations = find_metadata_based_candidates(
                sp, track, metadata_features, limit=50
            )
        except Exception as e:
            logging.error(f"Candidate search failed: {e}")
            candidate_recommendations = []
        
        # Enhance candidates with metadata
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
                logging.debug(f"Skipping candidate due to error: {e}")
                continue
        
        logging.debug(f"Enhanced {len(enhanced_candidates)} candidates")
        
        # Calculate similarities
        similar_songs = []
        if enhanced_candidates:
            try:
                mathematical_matches = similarity_engine.find_metadata_similarities(
                    metadata_features,
                    enhanced_candidates,
                    top_n=10
                )
                
                logging.debug(f"Found {len(mathematical_matches)} similar songs")
                
                # Format results for response
                for title_match, similarity, breakdown in mathematical_matches:
                    original_candidate = next(
                        (rec for rec in enhanced_candidates if rec['title'] == title_match),
                        {}
                    )
                    
                    candidate_features = original_candidate.get('metadata_features', {})
                    candidate_pseudo_features = convert_metadata_to_audio_features(candidate_features)
                    
                    # Get full track info for additional metadata
                    track_id = original_candidate.get('spotify_id')
                    track_info = {}
                    if track_id:
                        try:
                            track_info = sp.track(track_id)
                        except Exception as e:
                            logging.debug(f"Could not fetch track info: {e}")
                    
                    similar_songs.append({
                        "title": title_match,
                        "artist": original_candidate.get('artist', 'Unknown'),
                        "spotify_id": original_candidate.get('spotify_id'),
                        "popularity": original_candidate.get('popularity', 0),
                        "duration_ms": candidate_features.get('duration_ms', 0),
                        "explicit": candidate_features.get('explicit', False),
                        "preview_url": original_candidate.get('preview_url'),
                        "album": track_info.get('album', {}).get('name', 'Unknown'),
                        "release_date": track_info.get('album', {}).get('release_date', 'Unknown'),
                        "genres": candidate_features.get('artist_genres', []),
                        "similarity_score": similarity,
                        "similarity_explanation": similarity_engine.explain_metadata_similarity(breakdown),
                        "audio_features": candidate_pseudo_features
                    })
                    
            except Exception as e:
                logging.error(f"Similarity calculation failed: {e}")
                # Return partial results if available
                if not similar_songs and enhanced_candidates:
                    similar_songs = [{
                        "title": c.get('title', 'Unknown'),
                        "artist": c.get('artist', 'Unknown'),
                        "spotify_id": c.get('spotify_id'),
                        "similarity_score": 0.5,
                        "similarity_explanation": "Could not calculate detailed similarity"
                    } for c in enhanced_candidates[:10]]
        
        return jsonify({
            "success": True,
            "original_song": original_song,
            "similar_songs": similar_songs,
            "total_matches": len(similar_songs),
            "analysis_method": "metadata_based",
            "message": "Similar songs found successfully" if similar_songs else "No similar songs found"
        }), 200
        
    except spotipy.SpotifyException as e:
        logging.error(f"Spotify API error: {e}")
        return create_error_response(
            'spotify_api_error',
            'Spotify service error',
            details=str(e),
            suggestions=['Try again in a few moments'],
            status_code=503
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error: {e}")
        return create_error_response(
            'network_error',
            'Network connection error',
            suggestions=['Check your internet connection', 'Try again'],
            status_code=503
        )
    except Exception as e:
        logging.error(f"Unexpected error in /similar-songs: {e}", exc_info=True)
        return create_error_response(
            'internal_error',
            'An unexpected error occurred',
            suggestions=['Try again', 'Contact support if issue persists'],
            status_code=500
        )


@app.route('/upload', methods=['POST'])
def upload_audio():
    """
    Handle audio file uploads for real analysis.
    Enhanced with comprehensive error handling and validation.
    """
    try:
        # Validate file presence
        if 'audio_file' not in request.files:
            return create_error_response(
                'missing_file',
                'No audio file provided',
                details='The request must include an audio file',
                suggestions=[
                    'Ensure you are sending a file with the key "audio_file"',
                    'Check that the request has Content-Type: multipart/form-data'
                ],
                status_code=400
            )

        file = request.files['audio_file']
        
        if file.filename == '':
            return create_error_response(
                'empty_filename',
                'No file selected',
                suggestions=['Select a valid audio file'],
                status_code=400
            )

        # Validate filename
        if not file.filename:
            return create_error_response(
                'invalid_filename',
                'Invalid filename',
                status_code=400
            )
            
        if not allowed_file(file.filename):
            return create_error_response(
                'unsupported_format',
                'File type not supported',
                details=f'File: {file.filename}',
                suggestions=[
                    'Use one of these formats: MP3, WAV, FLAC, M4A, OGG, WEBM',
                    'Ensure the file has the correct extension'
                ],
                status_code=400
            )

        # Validate file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 16 * 1024 * 1024:  # 16MB
            return create_error_response(
                'file_too_large',
                'File too large',
                details=f'File size: {file_size / 1024 / 1024:.1f}MB',
                suggestions=['File must be under 16MB', 'Try compressing the audio file'],
                status_code=413
            )
        
        if file_size == 0:
            return create_error_response(
                'empty_file',
                'File is empty',
                suggestions=['Ensure the file contains audio data'],
                status_code=400
            )

        # Save uploaded file temporarily with secure filename
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(suffix=f'_{filename}', delete=False) as temp_file:
            try:
                file.save(temp_file.name)
                temp_path = temp_file.name
            except Exception as e:
                logging.error(f"Failed to save uploaded file: {e}")
                return create_error_response(
                    'save_error',
                    'Failed to save uploaded file',
                    suggestions=['Try uploading again', 'Check file permissions'],
                    status_code=500
                )

        try:
            # Extract real audio features with timeout protection
            logging.info(f"Analyzing uploaded file: {filename}")
            try:
                real_features = extract_real_audio_features(temp_path)
            except librosa.util.exceptions.ParameterError as e:
                logging.error(f"Invalid audio file format: {e}")
                return create_error_response(
                    'invalid_audio',
                    'Invalid or corrupted audio file',
                    details=str(e),
                    suggestions=[
                        'Ensure the file is a valid audio file',
                        'Try converting to a different format (MP3 or WAV recommended)',
                        'Check that the file is not corrupted'
                    ],
                    status_code=400
                )
            except Exception as e:
                logging.error(f"Audio analysis failed: {e}")
                return create_error_response(
                    'analysis_failed',
                    'Failed to analyze audio file',
                    details=str(e),
                    suggestions=[
                        'Ensure the file is a valid audio file',
                        'Try a different file',
                        'File may be corrupted or in an unsupported format'
                    ],
                    status_code=500
                )
            
            if not real_features:
                return create_error_response(
                    'analysis_failed',
                    'Failed to extract audio features',
                    suggestions=[
                        'The audio file may be corrupted',
                        'Try a different audio file',
                        'Ensure the file contains valid audio data'
                    ],
                    status_code=500
                )

            # Create song object for database
            uploaded_song = {
                "title": f"Uploaded: {filename}",
                "artist": "User Upload",
                "audio_features": real_features,
                "spotify_metadata": {
                    "popularity": 50,  # Neutral
                    "duration_ms": real_features.get('duration', 0),
                    "explicit": False,
                    "preview_url": None,
                    "has_preview": False,
                    "is_upload": True,
                    "upload_filename": filename
                }
            }

            # Save to database (non-critical, catch errors)
            try:
                save_song_to_db(uploaded_song)
            except Exception as e:
                logging.warning(f"Failed to save to database: {e}")
                # Continue anyway

            # Find similar tracks using existing metadata system
            try:
                sp = get_spotify_client()
                similarity_engine = MetadataSimilarityEngine(sp)
            except Exception as e:
                logging.error(f"Failed to initialize Spotify: {e}")
                return create_error_response(
                    'spotify_error',
                    'Could not connect to Spotify for recommendations',
                    details='Audio was analyzed but recommendations unavailable',
                    suggestions=['Try again later'],
                    status_code=503
                )

            # Create pseudo-metadata for searching
            pseudo_metadata = create_pseudo_metadata_from_audio(real_features, filename)

            # Find candidates using audio characteristics
            try:
                candidates = find_candidates_by_audio_characteristics(sp, real_features, pseudo_metadata)
            except Exception as e:
                logging.error(f"Candidate search failed: {e}")
                candidates = []

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
                    logging.debug(f"Failed to enhance candidate: {e}")
                    continue

            # Compare real features with estimated features
            try:
                recommendations = compare_real_vs_estimated_features(real_features, enhanced_candidates)
            except Exception as e:
                logging.error(f"Comparison failed: {e}")
                recommendations = []

            return jsonify({
                "success": True,
                "message": "Audio file analyzed successfully",
                "original_song": uploaded_song,
                "recommendations": recommendations,
                "analysis_stats": {
                    "analysis_method": "real_audio_upload",
                    "feature_completeness": real_features.get('feature_completeness', 0.95),
                    "candidates_found": len(candidates),
                    "candidates_analyzed": len(enhanced_candidates),
                    "matches_found": len(recommendations),
                    "file_size_kb": file_size / 1024
                }
            }), 200

        finally:
            # Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                logging.warning(f"Failed to cleanup temp file: {e}")

    except Exception as e:
        logging.error(f"Upload processing failed: {e}", exc_info=True)
        return create_error_response(
            'upload_error',
            'Upload failed',
            details='An error occurred while processing your upload',
            suggestions=['Try again', 'Ensure the file is a valid audio file'],
            status_code=500
        )


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




# ============================================================================
# LIBRARY MANAGEMENT API ENDPOINTS
# ============================================================================

@app.route('/library/songs', methods=['GET'])
def get_library():
    """Get all songs in user's library"""
    try:
        sort_by = request.args.get('sort_by', 'added_at')
        order = request.args.get('order', 'desc')
        
        songs = get_library_songs(sort_by=sort_by, order=order)
        
        return jsonify({
            'success': True,
            'songs': songs,
            'count': len(songs)
        }), 200
    except Exception as e:
        logging.error(f"Error getting library: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/songs', methods=['POST'])
def add_to_library():
    """Add a song to user's library"""
    try:
        data = request.json
        
        if not data or 'title' not in data:
            return jsonify({'error': 'Song data with title is required'}), 400
        
        result = add_song_to_library(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 200  # Already exists, not an error
    except Exception as e:
        logging.error(f"Error adding to library: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/songs/<song_id>', methods=['DELETE'])
def remove_from_library(song_id):
    """Remove a song from library"""
    try:
        result = remove_song_from_library(song_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logging.error(f"Error removing from library: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/collections', methods=['GET'])
def get_all_collections():
    """Get all collections"""
    try:
        collections = get_collections()
        
        return jsonify({
            'success': True,
            'collections': collections,
            'count': len(collections)
        }), 200
    except Exception as e:
        logging.error(f"Error getting collections: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/collections', methods=['POST'])
def create_new_collection():
    """Create a new collection"""
    try:
        data = request.json
        
        if not data or 'name' not in data:
            return jsonify({'error': 'Collection name is required'}), 400
        
        name = data['name'].strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': 'Collection name cannot be empty'}), 400
        
        result = create_collection(name, description)
        
        return jsonify(result), 201
    except Exception as e:
        logging.error(f"Error creating collection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/collections/<collection_id>', methods=['GET'])
def get_collection(collection_id):
    """Get a specific collection with full song details"""
    try:
        collection = get_collection_with_songs(collection_id)
        
        if collection:
            return jsonify({
                'success': True,
                'collection': collection
            }), 200
        else:
            return jsonify({'error': 'Collection not found'}), 404
    except Exception as e:
        logging.error(f"Error getting collection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/collections/<collection_id>', methods=['PUT'])
def update_collection_metadata(collection_id):
    """Update collection name or description"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Update data is required'}), 400
        
        name = data.get('name')
        description = data.get('description')
        
        if name is not None:
            name = name.strip()
            if not name:
                return jsonify({'error': 'Collection name cannot be empty'}), 400
        
        result = update_collection(collection_id, name=name, description=description)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logging.error(f"Error updating collection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/collections/<collection_id>', methods=['DELETE'])
def delete_collection_endpoint(collection_id):
    """Delete a collection"""
    try:
        result = delete_collection(collection_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logging.error(f"Error deleting collection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/collections/<collection_id>/songs', methods=['POST'])
def add_song_to_collection_endpoint(collection_id):
    """Add a song to a collection"""
    try:
        data = request.json
        
        if not data or 'song_id' not in data:
            return jsonify({'error': 'song_id is required'}), 400
        
        song_id = data['song_id']
        result = add_song_to_collection(collection_id, song_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404 if 'not found' in result['message'] else 200
    except Exception as e:
        logging.error(f"Error adding song to collection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/collections/<collection_id>/songs/<song_id>', methods=['DELETE'])
def remove_song_from_collection_endpoint(collection_id, song_id):
    """Remove a song from a collection"""
    try:
        result = remove_song_from_collection(collection_id, song_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logging.error(f"Error removing song from collection: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/library/stats', methods=['GET'])
def get_library_statistics():
    """Get library statistics"""
    try:
        stats = get_library_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        logging.error(f"Error getting library stats: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SONG IDENTIFICATION ENDPOINT
# ============================================================================

@app.route('/identify', methods=['POST'])
def identify_song():
    """
    Identify a song from user-provided audio file.
    Returns metadata including title, artist, album, and cover art.
    Enhanced with comprehensive error handling.
    """
    try:
        # Validate file presence
        if 'audio_file' not in request.files:
            return create_error_response(
                'missing_file',
                'No audio file provided',
                suggestions=[
                    'Include an audio file in your request',
                    'Ensure the file field is named "audio_file"'
                ],
                status_code=400
            )

        file = request.files['audio_file']
        
        if not file or file.filename == '':
            return create_error_response(
                'empty_file',
                'No file selected',
                suggestions=['Select a valid audio file to identify'],
                status_code=400
            )

        # Validate file type
        if not allowed_file(file.filename):
            return create_error_response(
                'unsupported_format',
                'File type not supported for identification',
                details=f'Received: {file.filename}',
                suggestions=[
                    'Use MP3, WAV, FLAC, M4A, or OGG format',
                    'Ensure file has correct extension'
                ],
                status_code=400
            )

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(suffix=f'_{filename}', delete=False) as temp_file:
            try:
                file.save(temp_file.name)
                temp_path = temp_file.name
            except Exception as e:
                logging.error(f"Failed to save file for identification: {e}")
                return create_error_response(
                    'save_error',
                    'Failed to save audio file',
                    suggestions=['Try uploading again'],
                    status_code=500
                )

        try:
            # Initialize song identifier with error handling
            try:
                identifier = SongIdentifier()
                
                # Check if API key is available
                if not identifier.acoustid_api_key:
                    return create_error_response(
                        'config_error',
                        'Song identification service not configured',
                        details='ACOUSTID_API_KEY is not set',
                        suggestions=[
                            'Contact administrator to configure AcoustID API key',
                            'Get a free API key at https://acoustid.org'
                        ],
                        status_code=503
                    )
            except Exception as e:
                logging.error(f"Failed to initialize identifier: {e}")
                return create_error_response(
                    'init_error',
                    'Failed to initialize identification service',
                    suggestions=['Try again later', 'Contact support if issue persists'],
                    status_code=503
                )
            
            logging.info(f"Identifying song from: {filename}")
            
            # Identify the song with timeout protection
            try:
                metadata = identifier.identify_song(temp_path)
            except Exception as e:
                logging.error(f"Identification process failed: {e}")
                return create_error_response(
                    'identification_failed',
                    'Could not identify the song',
                    details=str(e),
                    suggestions=[
                        'Ensure the audio quality is good',
                        'Try a 15-30 second clip from a recognizable part of the song',
                        'Reduce background noise if possible',
                        'Try a different song or audio file'
                    ],
                    status_code=404
                )
            
            if not metadata:
                return create_error_response(
                    'no_match',
                    'Could not identify song',
                    details='No matches found in the database',
                    suggestions=[
                        'Ensure the audio quality is good',
                        'Try uploading a 15-30 second clip from the chorus',
                        'Reduce background noise if possible',
                        'The song may not be in the database yet'
                    ],
                    status_code=404
                )
            
            # Enrich metadata with Spotify data if possible
            try:
                sp = get_spotify_client()
                enriched_metadata = identifier.enrich_metadata_from_spotify(metadata, sp)
            except Exception as e:
                logging.warning(f"Spotify enrichment failed: {e}")
                # Continue with basic metadata
                enriched_metadata = metadata
                enriched_metadata['spotify_enriched'] = False
            
            # Save to database (non-critical)
            try:
                song_data = {
                    "title": enriched_metadata.get('title'),
                    "artist": enriched_metadata.get('artist'),
                    "audio_features": {},  # Can be populated later if needed
                    "spotify_metadata": {
                        "album": enriched_metadata.get('album'),
                        "album_art": enriched_metadata.get('album_art'),
                        "cover_art": enriched_metadata.get('cover_art'),
                        "release_date": enriched_metadata.get('release_date'),
                        "spotify_id": enriched_metadata.get('spotify_id'),
                        "spotify_url": enriched_metadata.get('spotify_url'),
                        "preview_url": enriched_metadata.get('preview_url'),
                        "popularity": enriched_metadata.get('popularity'),
                        "duration_ms": enriched_metadata.get('duration_ms'),
                        "explicit": enriched_metadata.get('explicit'),
                        "genres": enriched_metadata.get('artist_genres', []),
                        "label": enriched_metadata.get('label'),
                    }
                }
                save_song_to_db(song_data)
            except Exception as e:
                logging.warning(f"Failed to save identified song: {e}")
                # Non-critical, continue
            
            return jsonify({
                "success": True,
                "message": "Song identified successfully",
                "identified": True,
                "song": {
                    "title": enriched_metadata.get('title'),
                    "artist": enriched_metadata.get('artist'),
                    "album": enriched_metadata.get('album'),
                    "album_art": enriched_metadata.get('album_art'),
                    "cover_art": enriched_metadata.get('cover_art'),
                    "release_date": enriched_metadata.get('release_date'),
                    "label": enriched_metadata.get('label'),
                    "spotify_id": enriched_metadata.get('spotify_id'),
                    "spotify_url": enriched_metadata.get('spotify_url'),
                    "preview_url": enriched_metadata.get('preview_url'),
                    "popularity": enriched_metadata.get('popularity'),
                    "duration_ms": enriched_metadata.get('duration_ms'),
                    "explicit": enriched_metadata.get('explicit'),
                    "genres": enriched_metadata.get('artist_genres', []),
                    "album_details": {
                        "type": enriched_metadata.get('album_type'),
                        "total_tracks": enriched_metadata.get('album_total_tracks'),
                        "release_date": enriched_metadata.get('album_release_date'),
                        "label": enriched_metadata.get('album_label'),
                    },
                    "identification_metadata": {
                        "source": enriched_metadata.get('identification_source'),
                        "confidence_score": enriched_metadata.get('score'),
                        "timecode": enriched_metadata.get('timecode'),
                        "spotify_enriched": enriched_metadata.get('spotify_enriched', False)
                    }
                }
            }), 200

        finally:
            # Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                logging.warning(f"Failed to cleanup temp file: {e}")

    except Exception as e:
        logging.error(f"Song identification failed: {e}", exc_info=True)
        return create_error_response(
            'identification_error',
            'Song identification failed',
            details='An unexpected error occurred',
            suggestions=[
                'Try again with a different audio file',
                'Ensure the file is not corrupted',
                'Contact support if issue persists'
            ],
            status_code=500
        )


@app.route('/privacy', methods=['GET'])
def privacy_policy():
    """Privacy policy page for API compliance (Pinterest, etc.)"""
    return render_template('privacy.html')


@app.route('/now-playing', methods=['GET'])
def get_now_playing():
    """Get the user's currently playing track"""
    try:
        token_info = session.get('token_info')
        if not token_info:
            return create_error_response(
                'auth_error',
                'User not authenticated',
                suggestions=['Please login with Spotify first'],
                status_code=401
            )

        auth_manager = get_auth_manager()
        sp = spotipy.Spotify(auth_manager=auth_manager)

        # Get current playback
        current = sp.current_playback()

        if not current or not current.get('item'):
            return jsonify({
                "success": True,
                "is_playing": False,
                "message": "No track currently playing"
            }), 200

        track = current['item']

        # Format the response
        result = {
            "success": True,
            "is_playing": current.get('is_playing', False),
            "track": {
                "id": track['id'],
                "name": track['name'],
                "artist": ', '.join([artist['name'] for artist in track['artists']]),
                "artists": [{"name": artist['name'], "id": artist['id']} for artist in track['artists']],
                "album": track['album']['name'],
                "album_art": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "spotify_url": track['external_urls']['spotify'],
                "preview_url": track.get('preview_url'),
                "duration_ms": track['duration_ms'],
                "popularity": track.get('popularity'),
                "explicit": track.get('explicit', False)
            },
            "progress_ms": current.get('progress_ms', 0),
            "device": {
                "name": current['device']['name'],
                "type": current['device']['type']
            } if current.get('device') else None,
            "shuffle_state": current.get('shuffle_state', False),
            "repeat_state": current.get('repeat_state', 'off')
        }

        return jsonify(result), 200

    except Exception as e:
        logging.error(f"Error fetching now playing: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to fetch currently playing track',
            details=str(e),
            status_code=500
        )


@app.route('/recently-played', methods=['GET'])
def get_recently_played():
    """Get the user's recently played tracks"""
    try:
        token_info = session.get('token_info')
        if not token_info:
            return create_error_response(
                'auth_error',
                'User not authenticated',
                suggestions=['Please login with Spotify first'],
                status_code=401
            )

        auth_manager = get_auth_manager()
        sp = spotipy.Spotify(auth_manager=auth_manager)

        # Get recently played tracks (limit 50)
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 50)  # Cap at 50

        results = sp.current_user_recently_played(limit=limit)

        tracks = []
        for item in results.get('items', []):
            track = item['track']
            tracks.append({
                "id": track['id'],
                "name": track['name'],
                "artist": ', '.join([artist['name'] for artist in track['artists']]),
                "artists": [{"name": artist['name'], "id": artist['id']} for artist in track['artists']],
                "album": track['album']['name'],
                "album_art": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "spotify_url": track['external_urls']['spotify'],
                "preview_url": track.get('preview_url'),
                "duration_ms": track['duration_ms'],
                "popularity": track.get('popularity'),
                "explicit": track.get('explicit', False),
                "played_at": item['played_at']
            })

        return jsonify({
            "success": True,
            "tracks": tracks,
            "total": len(tracks)
        }), 200

    except Exception as e:
        logging.error(f"Error fetching recently played: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to fetch recently played tracks',
            details=str(e),
            status_code=500
        )


@app.route('/mood-board', methods=['GET'])
def get_mood_board():
    """Generate a mood board with aesthetic images based on user's listening history"""
    try:
        token_info = session.get('token_info')
        if not token_info:
            return create_error_response(
                'auth_error',
                'User not authenticated',
                suggestions=['Please login with Spotify first'],
                status_code=401
            )

        auth_manager = get_auth_manager()
        sp = spotipy.Spotify(auth_manager=auth_manager)

        # Get recently played tracks
        all_tracks = []
        artist_ids = []
        spotify_fallback_images = []

        try:
            # Fetch more tracks for greater variety (50 instead of 20)
            recently_played = sp.current_user_recently_played(limit=50)
            for item in recently_played.get('items', []):
                track = item['track']

                # Collect artist IDs for fetching artist images
                if track['artists'][0]['id']:
                    artist_ids.append(track['artists'][0]['id'])

                all_tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'artist_id': track['artists'][0]['id'],
                    'album': track['album']['name'],
                    'album_art': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'played_at': item['played_at'],
                    'genres': []  # Will be populated if we fetch artist info
                })
        except Exception as e:
            logging.error(f"Could not fetch recently played: {e}")

        # Check if we have any tracks
        if not all_tracks:
            return jsonify({
                "success": True,
                "tracks": [],
                "images": [],
                "track_count": 0,
                "generated_at": datetime.now().isoformat(),
                "message": "No listening history found yet. Start listening to music on Spotify!",
                "source": "none"
            }), 200

        # Fetch artist data for genres and fallback images
        artist_images = {}
        if artist_ids:
            try:
                unique_artist_ids = list(set(artist_ids))[:10]
                artists_data = sp.artists(unique_artist_ids)
                for artist in artists_data.get('artists', []):
                    if artist:
                        # Store artist images for fallback
                        if artist.get('images'):
                            artist_images[artist['id']] = artist['images'][0]['url']

                        # Add genres to tracks
                        genres = artist.get('genres', [])
                        for track in all_tracks:
                            if track['artist_id'] == artist['id']:
                                track['genres'] = genres
            except Exception as e:
                logging.warning(f"Could not fetch artist data: {e}")

        # Prepare Spotify images (PRIMARY SOURCE - artist photos and album covers)
        # Use ALL tracks for maximum variety (was 30, now using all 50)
        for idx, track in enumerate(all_tracks[:50]):
            # Add artist photo every 4 tracks (not every 3) for more variety
            if idx % 4 == 0 and track['artist_id'] in artist_images:
                # Artist photo
                spotify_fallback_images.append({
                    'url': artist_images[track['artist_id']],
                    'thumb_url': artist_images[track['artist_id']],
                    'title': track['artist'],
                    'artist': track['artist'],
                    'type': 'artist',
                    'source': 'spotify'
                })
            if track['album_art']:
                # Album cover
                spotify_fallback_images.append({
                    'url': track['album_art'],
                    'thumb_url': track['album_art'],
                    'title': track['name'],
                    'artist': track['artist'],
                    'type': 'album',
                    'source': 'spotify'
                })

        # MIX Spotify (90%) + Unsplash (10%) - HEAVY Spotify bias
        # Spotify = ACTUAL music content (artist photos, album covers)
        # Unsplash = Just a tiny bit of aesthetic variety until Pinterest API is ready
        images = []
        image_source = 'spotify+unsplash'

        try:
            image_service = get_image_service()
            # Fetch very few Unsplash images (only 10% of total)
            unsplash_images = image_service.fetch_mood_board_images(all_tracks, total_images=12)

            # Mix: 90 Spotify images + 10 Unsplash images = 100 total
            import random

            # Take up to 90 Spotify images (or all if less)
            spotify_portion = spotify_fallback_images[:90]

            # Take up to 10 Unsplash images (or all if less)
            unsplash_portion = unsplash_images[:10] if unsplash_images else []

            # Combine and shuffle for variety
            images = spotify_portion + unsplash_portion
            random.shuffle(images)

            logging.info(f"Mixed mood board: {len(spotify_portion)} Spotify + {len(unsplash_portion)} Unsplash = {len(images)} total")

        except Exception as e:
            # Fallback to 100% Spotify images on error
            logging.warning(f"Error fetching Unsplash images, using Spotify only: {e}")
            images = spotify_fallback_images[:100]
            image_source = 'spotify'

        return jsonify({
            "success": True,
            "tracks": all_tracks[:10],
            "images": images,
            "track_count": len(all_tracks),
            "generated_at": datetime.now().isoformat(),
            "source": image_source
        }), 200

    except Exception as e:
        logging.error(f"Error generating mood board: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to generate mood board',
            details=str(e),
            status_code=500
        )


@app.route('/mood-board/custom-search', methods=['POST'])
def custom_mood_board_search():
    """Custom search for mood board images by user-defined query"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        count = min(int(data.get('count', 120)), 120)  # Max 120 images
        sources = data.get('sources')  # Optional: ['unsplash', 'pexels', 'pixabay']

        if not query:
            return create_error_response(
                'validation_error',
                'Search query is required',
                status_code=400
            )

        image_service = get_image_service()
        images = image_service.search_images(query, count=count, sources=sources)

        return jsonify({
            "success": True,
            "images": images,
            "query": query,
            "count": len(images),
            "sources_used": list(set(img.get('source', 'unknown') for img in images))
        }), 200

    except Exception as e:
        logging.error(f"Error in custom mood board search: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to search images',
            details=str(e),
            status_code=500
        )


@app.route('/mood-board/save', methods=['POST'])
def save_user_mood_board():
    """Save a mood board collection"""
    try:
        token_info = session.get('token_info')
        if not token_info:
            return create_error_response(
                'auth_error',
                'User not authenticated',
                status_code=401
            )

        auth_manager = get_auth_manager()
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user_info = sp.current_user()
        user_id = user_info['id']

        data = request.get_json()
        images = data.get('images', [])
        tracks = data.get('tracks', [])
        board_name = data.get('name')

        if not images:
            return create_error_response(
                'validation_error',
                'No images to save',
                status_code=400
            )

        board_id = save_mood_board(user_id, images, tracks, board_name)
        share_url = generate_share_link(board_id, request.host_url.rstrip('/'))

        return jsonify({
            "success": True,
            "board_id": board_id,
            "share_url": share_url,
            "message": "Mood board saved successfully"
        }), 200

    except Exception as e:
        logging.error(f"Error saving mood board: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to save mood board',
            details=str(e),
            status_code=500
        )


@app.route('/mood-board/my-boards', methods=['GET'])
def get_my_mood_boards():
    """Get all saved mood boards for the current user"""
    try:
        token_info = session.get('token_info')
        if not token_info:
            return create_error_response(
                'auth_error',
                'User not authenticated',
                status_code=401
            )

        auth_manager = get_auth_manager()
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user_info = sp.current_user()
        user_id = user_info['id']

        boards = get_user_mood_boards(user_id)

        return jsonify({
            "success": True,
            "boards": boards,
            "count": len(boards)
        }), 200

    except Exception as e:
        logging.error(f"Error fetching user mood boards: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to fetch mood boards',
            details=str(e),
            status_code=500
        )


@app.route('/mood-board/<board_id>', methods=['GET'])
def get_saved_mood_board(board_id):
    """Get a specific saved mood board"""
    try:
        board = load_mood_board(board_id)

        if not board:
            return create_error_response(
                'not_found',
                'Mood board not found',
                status_code=404
            )

        return jsonify({
            "success": True,
            "board": board
        }), 200

    except Exception as e:
        logging.error(f"Error loading mood board: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to load mood board',
            details=str(e),
            status_code=500
        )


@app.route('/mood-board/<board_id>', methods=['DELETE'])
def delete_user_mood_board(board_id):
    """Delete a saved mood board"""
    try:
        token_info = session.get('token_info')
        if not token_info:
            return create_error_response(
                'auth_error',
                'User not authenticated',
                status_code=401
            )

        auth_manager = get_auth_manager()
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user_info = sp.current_user()
        user_id = user_info['id']

        success = delete_mood_board(board_id, user_id)

        if not success:
            return create_error_response(
                'not_found',
                'Mood board not found or unauthorized',
                status_code=404
            )

        return jsonify({
            "success": True,
            "message": "Mood board deleted successfully"
        }), 200

    except Exception as e:
        logging.error(f"Error deleting mood board: {e}", exc_info=True)
        return create_error_response(
            'api_error',
            'Failed to delete mood board',
            details=str(e),
            status_code=500
        )


@app.route('/shared/mood-board/<board_id>', methods=['GET'])
def view_shared_mood_board(board_id):
    """View a shared mood board (public access)"""
    try:
        board = load_mood_board(board_id)

        if not board:
            return render_template('error.html', message='Mood board not found'), 404

        # Return HTML view for shared mood boards
        return render_template('shared_mood_board.html', board=board)

    except Exception as e:
        logging.error(f"Error viewing shared mood board: {e}", exc_info=True)
        return render_template('error.html', message='Error loading mood board'), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Security: Never run debug mode in production
    flask_env = os.getenv('FLASK_ENV', 'production')
    debug = flask_env == 'development'

    if debug:
        logging.warning("Running in DEBUG mode. This should NEVER be used in production!")
    
    app.run(host='0.0.0.0', port=port, debug=debug)