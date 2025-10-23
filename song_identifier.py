"""
Song identification module using audio fingerprinting.
Uses AcoustID for fingerprinting and MusicBrainz for metadata.
"""

import logging
import acoustid
import musicbrainzngs
from typing import Dict, Optional, Any, List
import os

# Configure MusicBrainz user agent
musicbrainzngs.set_useragent(
    "MelodySearch",
    "1.0",
    "https://github.com/Tadiwa-M/MelodySearch"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SongIdentifier:
    """
    Identifies songs from audio files using acoustic fingerprinting.
    Returns metadata including title, artist, album, and cover art.
    """
    
    def __init__(self, acoustid_api_key: Optional[str] = None):
        """
        Initialize the song identifier.
        
        Args:
            acoustid_api_key: AcoustID API key. If not provided, will try to get from environment.
        """
        self.acoustid_api_key = acoustid_api_key or os.getenv('ACOUSTID_API_KEY')
        if not self.acoustid_api_key:
            logger.warning("No AcoustID API key provided. Song identification will not work.")
    
    def identify_song(self, audio_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Identify a song from an audio file with comprehensive error handling.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary with song metadata or None if identification fails
        """
        if not self.acoustid_api_key:
            logger.error("AcoustID API key is required for song identification")
            logger.info("Get a free API key at https://acoustid.org/new-application")
            return None
        
        # Validate file exists
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None
        
        # Validate file is not empty
        try:
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                logger.error(f"Audio file is empty: {audio_file_path}")
                return None
            if file_size < 1024:  # Less than 1KB
                logger.warning(f"Audio file is very small ({file_size} bytes), may not contain enough data")
        except OSError as e:
            logger.error(f"Cannot access audio file: {e}")
            return None
        
        try:
            logger.info(f"Identifying song from: {audio_file_path}")
            
            # Generate fingerprint and match against AcoustID database with timeout
            try:
                matches = list(acoustid.match(self.acoustid_api_key, audio_file_path))
            except acoustid.FingerprintGenerationError as e:
                logger.error(f"Failed to generate audio fingerprint: {e}")
                logger.info("This may happen if:")
                logger.info("  - The audio file is corrupted")
                logger.info("  - The audio format is not supported")
                logger.info("  - The 'fpcalc' tool is not installed")
                return None
            except acoustid.WebServiceError as e:
                logger.error(f"AcoustID web service error: {e}")
                logger.info("This may be a temporary issue. Try again in a few moments.")
                return None
            except acoustid.NoBackendError as e:
                logger.error(f"Audio backend not available: {e}")
                logger.info("Install chromaprint (fpcalc) to enable fingerprinting:")
                logger.info("  Ubuntu/Debian: sudo apt-get install libchromaprint-tools")
                logger.info("  macOS: brew install chromaprint")
                return None
            except Exception as e:
                logger.error(f"Error during fingerprint matching: {e}")
                return None
            
            if not matches:
                logger.warning("No matches found for the audio file")
                logger.info("This could mean:")
                logger.info("  - The song is not in the AcoustID database")
                logger.info("  - The audio quality is too poor")
                logger.info("  - The audio clip is too short (try 15-30 seconds)")
                logger.info("  - There's too much background noise")
                return None
            
            # Get the best match (highest score)
            try:
                best_match = max(matches, key=lambda x: x[0])
                score, recording_id, title, artist = best_match
            except (ValueError, IndexError, TypeError) as e:
                logger.error(f"Invalid match data structure: {e}")
                return None
            
            logger.info(f"Match found with score {score:.2f}: {title} by {artist}")
            
            # Warn if confidence is low
            if score < 0.5:
                logger.warning(f"Low confidence score ({score:.2f}). Results may be inaccurate.")
            elif score < 0.7:
                logger.info(f"Medium confidence score ({score:.2f}). Results are likely correct.")
            else:
                logger.info(f"High confidence score ({score:.2f}). Results are very likely correct.")
            
            # Get detailed metadata from MusicBrainz
            metadata = self._fetch_musicbrainz_metadata(recording_id)
            
            if metadata:
                metadata['identification_score'] = score
                metadata['score'] = score  # Alias for compatibility
                metadata['identification_source'] = 'acoustid'
                return metadata
            else:
                # Return basic info if MusicBrainz fetch fails
                logger.warning("Could not fetch detailed metadata, returning basic info")
                return {
                    'title': title,
                    'artist': artist,
                    'identification_score': score,
                    'score': score,
                    'identification_source': 'acoustid',
                    'recording_id': recording_id
                }
                
        except KeyboardInterrupt:
            logger.info("Song identification cancelled by user")
            return None
        except Exception as e:
            logger.error(f"Unexpected error identifying song: {e}", exc_info=True)
            return None
    
    def _fetch_musicbrainz_metadata(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed metadata from MusicBrainz with error handling and retries.
        
        Args:
            recording_id: MusicBrainz recording ID
            
        Returns:
            Dictionary with detailed metadata
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Fetch recording details
                recording = musicbrainzngs.get_recording_by_id(
                    recording_id,
                    includes=['artists', 'releases', 'isrcs', 'tags', 'ratings']
                )
                
                rec = recording.get('recording')
                if not rec:
                    logger.error("Invalid recording data from MusicBrainz")
                    return None
                
                # Extract basic info with safe defaults
                title = rec.get('title', 'Unknown')
                
                # Safely extract artist name
                artist = 'Unknown'
                if rec.get('artist-credit') and len(rec['artist-credit']) > 0:
                    try:
                        artist = rec['artist-credit'][0]['artist']['name']
                    except (KeyError, IndexError, TypeError):
                        logger.warning("Could not extract artist name from metadata")
                
                # Extract album info from releases
                album = None
                release_date = None
                cover_art_url = None
                
                if 'release-list' in rec and rec['release-list']:
                    try:
                        # Get the primary release
                        release = rec['release-list'][0]
                        album = release.get('title', 'Unknown')
                        release_date = release.get('date', None)
                        release_id = release.get('id', None)
                        
                        # Try to get cover art
                        if release_id:
                            cover_art_url = self._get_cover_art(release_id)
                    except (KeyError, IndexError, TypeError) as e:
                        logger.warning(f"Error extracting release info: {e}")
                
                # Extract ISRC (International Standard Recording Code)
                isrc = None
                if 'isrc-list' in rec and rec['isrc-list']:
                    try:
                        isrc = rec['isrc-list'][0]
                    except (IndexError, TypeError):
                        logger.debug("Could not extract ISRC")
                
                # Extract genres/tags
                tags = []
                if 'tag-list' in rec:
                    try:
                        tags = [tag['name'] for tag in rec['tag-list'][:5]]  # Top 5 tags
                    except (KeyError, TypeError):
                        logger.debug("Could not extract tags")
                
                metadata = {
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'release_date': release_date,
                    'cover_art_url': cover_art_url,
                    'album_art': cover_art_url,  # Alias
                    'recording_id': recording_id,
                    'isrc': isrc,
                    'tags': tags,
                    'musicbrainz_url': f"https://musicbrainz.org/recording/{recording_id}"
                }
                
                logger.info(f"Fetched metadata for: {title} by {artist}")
                return metadata
                
            except musicbrainzngs.WebServiceError as e:
                logger.warning(f"MusicBrainz web service error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("Failed to fetch metadata after multiple attempts")
                    return None
            except musicbrainzngs.NetworkError as e:
                logger.error(f"Network error connecting to MusicBrainz: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    return None
            except musicbrainzngs.ResponseError as e:
                logger.error(f"Invalid response from MusicBrainz: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error fetching MusicBrainz metadata: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    return None
        
        return None
    
    def _get_cover_art(self, release_id: str) -> Optional[str]:
        """
        Get cover art URL from Cover Art Archive.
        
        Args:
            release_id: MusicBrainz release ID
            
        Returns:
            URL to cover art image or None
        """
        try:
            # Cover Art Archive API
            cover_art_url = f"https://coverartarchive.org/release/{release_id}/front-500"
            return cover_art_url
        except Exception as e:
            logger.error(f"Error getting cover art: {e}")
            return None
    
    def enrich_metadata_from_spotify(self, metadata: Dict[str, Any], spotify_client=None) -> Dict[str, Any]:
        """
        Enrich existing metadata with Spotify data.
        Enhanced with comprehensive error handling and graceful degradation.
        
        Args:
            metadata: Existing song metadata from identification
            spotify_client: Spotipy client instance for additional metadata
            
        Returns:
            Enriched metadata with Spotify data (or original if enrichment fails)
        """
        if not metadata:
            return metadata
        
        # Map identification_score to score for compatibility
        if 'identification_score' in metadata and 'score' not in metadata:
            metadata['score'] = metadata['identification_score']
            
        # If we have Spotify client, try to enrich with Spotify data
        if spotify_client and metadata.get('title') and metadata.get('artist'):
            try:
                # Search Spotify for the song
                query = f"{metadata['title']} {metadata['artist']}"
                
                try:
                    results = spotify_client.search(q=query, type='track', limit=1)
                except Exception as e:
                    logger.warning(f"Spotify search failed: {e}")
                    metadata['spotify_enriched'] = False
                    return metadata
                
                if not results or not results.get('tracks') or not results['tracks'].get('items'):
                    logger.info("No Spotify results found for this song")
                    metadata['spotify_enriched'] = False
                    return metadata
                
                spotify_track = results['tracks']['items'][0]
                
                # Verify it's likely the same song (basic check)
                spotify_title = spotify_track.get('name', '').lower()
                original_title = metadata['title'].lower()
                
                if spotify_title not in original_title and original_title not in spotify_title:
                    logger.warning(f"Spotify result '{spotify_title}' may not match '{original_title}'")
                    # Continue anyway, but note the mismatch
                
                # Add Spotify-specific metadata with safe defaults
                metadata['spotify_id'] = spotify_track.get('id')
                
                if spotify_track.get('external_urls'):
                    metadata['spotify_url'] = spotify_track['external_urls'].get('spotify')
                
                metadata['preview_url'] = spotify_track.get('preview_url')
                metadata['popularity'] = spotify_track.get('popularity', 0)
                metadata['duration_ms'] = spotify_track.get('duration_ms')
                metadata['explicit'] = spotify_track.get('explicit', False)
                
                # Prefer Spotify's cover art if available (usually higher quality)
                if spotify_track.get('album') and spotify_track['album'].get('images'):
                    try:
                        images = spotify_track['album']['images']
                        if images:
                            metadata['cover_art_url'] = images[0]['url']
                            metadata['album_art'] = images[0]['url']
                            metadata['cover_art'] = images[0]['url']
                            if len(images) > 1:
                                metadata['cover_art_thumbnail'] = images[-1]['url']
                    except (KeyError, IndexError, TypeError) as e:
                        logger.debug(f"Could not extract cover art: {e}")
                
                # Update album info from Spotify
                if spotify_track.get('album'):
                    album_info = spotify_track['album']
                    metadata['album'] = album_info.get('name')
                    metadata['album_type'] = album_info.get('album_type')
                    metadata['album_total_tracks'] = album_info.get('total_tracks')
                    metadata['album_release_date'] = album_info.get('release_date')
                    
                    # Get label if available
                    if album_info.get('label'):
                        metadata['album_label'] = album_info['label']
                
                # Get artist info with error handling
                if spotify_track.get('artists') and len(spotify_track['artists']) > 0:
                    try:
                        artist_id = spotify_track['artists'][0]['id']
                        if artist_id:
                            try:
                                artist_info = spotify_client.artist(artist_id)
                                metadata['artist_genres'] = artist_info.get('genres', [])
                                metadata['artist_popularity'] = artist_info.get('popularity', 0)
                            except Exception as e:
                                logger.warning(f"Could not fetch artist details: {e}")
                    except (KeyError, IndexError, TypeError) as e:
                        logger.warning(f"Could not extract artist ID: {e}")
                
                # Mark as enriched
                metadata['spotify_enriched'] = True
                
                logger.info(f"Successfully enriched with Spotify data: {metadata['title']}")
                    
            except Exception as e:
                logger.warning(f"Could not enrich with Spotify data: {e}")
                metadata['spotify_enriched'] = False
        else:
            metadata['spotify_enriched'] = False
            if not spotify_client:
                logger.debug("No Spotify client provided for enrichment")
            elif not metadata.get('title') or not metadata.get('artist'):
                logger.debug("Missing title or artist for Spotify enrichment")
        
        return metadata
    
    def identify_with_spotify_fallback(self, audio_file_path: str, spotify_client=None) -> Optional[Dict[str, Any]]:
        """
        Identify song with Spotify fallback for additional metadata.
        
        Args:
            audio_file_path: Path to the audio file
            spotify_client: Spotipy client instance for additional metadata
            
        Returns:
            Combined metadata from AcoustID/MusicBrainz and Spotify
        """
        # First, try AcoustID identification
        metadata = self.identify_song(audio_file_path)
        
        if not metadata:
            return None
        
        # Enrich with Spotify data
        return self.enrich_metadata_from_spotify(metadata, spotify_client)
    
    def batch_identify(self, audio_file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Identify multiple songs in batch.
        
        Args:
            audio_file_paths: List of paths to audio files
            
        Returns:
            List of metadata dictionaries
        """
        results = []
        for audio_path in audio_file_paths:
            result = self.identify_song(audio_path)
            if result:
                results.append(result)
        return results


# Utility function for quick identification
def identify_song_from_file(audio_file_path: str, acoustid_api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Quick utility function to identify a song from a file.
    
    Args:
        audio_file_path: Path to the audio file
        acoustid_api_key: AcoustID API key (optional, will use environment variable)
        
    Returns:
        Dictionary with song metadata or None
    """
    identifier = SongIdentifier(acoustid_api_key)
    return identifier.identify_song(audio_file_path)
