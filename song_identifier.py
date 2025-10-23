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
        Identify a song from an audio file.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary with song metadata or None if identification fails
        """
        if not self.acoustid_api_key:
            logger.error("AcoustID API key is required for song identification")
            return None
        
        try:
            logger.info(f"Identifying song from: {audio_file_path}")
            
            # Generate fingerprint and match against AcoustID database
            matches = list(acoustid.match(self.acoustid_api_key, audio_file_path))
            
            if not matches:
                logger.warning("No matches found for the audio file")
                return None
            
            # Get the best match (highest score)
            best_match = max(matches, key=lambda x: x[0])
            score, recording_id, title, artist = best_match
            
            logger.info(f"Match found with score {score:.2f}: {title} by {artist}")
            
            # Get detailed metadata from MusicBrainz
            metadata = self._fetch_musicbrainz_metadata(recording_id)
            
            if metadata:
                metadata['identification_score'] = score
                metadata['identification_source'] = 'acoustid'
                return metadata
            else:
                # Return basic info if MusicBrainz fetch fails
                return {
                    'title': title,
                    'artist': artist,
                    'identification_score': score,
                    'identification_source': 'acoustid',
                    'recording_id': recording_id
                }
                
        except Exception as e:
            logger.error(f"Error identifying song: {e}")
            return None
    
    def _fetch_musicbrainz_metadata(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed metadata from MusicBrainz.
        
        Args:
            recording_id: MusicBrainz recording ID
            
        Returns:
            Dictionary with detailed metadata
        """
        try:
            # Fetch recording details
            recording = musicbrainzngs.get_recording_by_id(
                recording_id,
                includes=['artists', 'releases', 'isrcs', 'tags', 'ratings']
            )
            
            rec = recording['recording']
            
            # Extract basic info
            title = rec.get('title', 'Unknown')
            artist = rec['artist-credit'][0]['artist']['name'] if rec.get('artist-credit') else 'Unknown'
            
            # Extract album info from releases
            album = None
            release_date = None
            cover_art_url = None
            
            if 'release-list' in rec and rec['release-list']:
                # Get the primary release
                release = rec['release-list'][0]
                album = release.get('title', 'Unknown')
                release_date = release.get('date', None)
                release_id = release.get('id', None)
                
                # Try to get cover art
                if release_id:
                    cover_art_url = self._get_cover_art(release_id)
            
            # Extract ISRC (International Standard Recording Code)
            isrc = None
            if 'isrc-list' in rec and rec['isrc-list']:
                isrc = rec['isrc-list'][0]
            
            # Extract genres/tags
            tags = []
            if 'tag-list' in rec:
                tags = [tag['name'] for tag in rec['tag-list'][:5]]  # Top 5 tags
            
            metadata = {
                'title': title,
                'artist': artist,
                'album': album,
                'release_date': release_date,
                'cover_art_url': cover_art_url,
                'recording_id': recording_id,
                'isrc': isrc,
                'tags': tags,
                'musicbrainz_url': f"https://musicbrainz.org/recording/{recording_id}"
            }
            
            logger.info(f"Fetched metadata for: {title} by {artist}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error fetching MusicBrainz metadata: {e}")
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
        
        Args:
            metadata: Existing song metadata from identification
            spotify_client: Spotipy client instance for additional metadata
            
        Returns:
            Enriched metadata with Spotify data
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
                results = spotify_client.search(q=query, type='track', limit=1)
                
                if results['tracks']['items']:
                    spotify_track = results['tracks']['items'][0]
                    
                    # Add Spotify-specific metadata
                    metadata['spotify_id'] = spotify_track['id']
                    metadata['spotify_url'] = spotify_track['external_urls']['spotify']
                    metadata['preview_url'] = spotify_track.get('preview_url')
                    metadata['popularity'] = spotify_track['popularity']
                    metadata['duration_ms'] = spotify_track.get('duration_ms')
                    metadata['explicit'] = spotify_track.get('explicit', False)
                    
                    # Prefer Spotify's cover art if available (usually higher quality)
                    if spotify_track['album']['images']:
                        metadata['cover_art_url'] = spotify_track['album']['images'][0]['url']
                        metadata['album_art'] = spotify_track['album']['images'][0]['url']
                        metadata['cover_art'] = spotify_track['album']['images'][0]['url']
                        metadata['cover_art_thumbnail'] = spotify_track['album']['images'][-1]['url']
                    
                    # Update album info from Spotify
                    metadata['album'] = spotify_track['album']['name']
                    metadata['album_type'] = spotify_track['album']['album_type']
                    metadata['album_total_tracks'] = spotify_track['album'].get('total_tracks')
                    metadata['album_release_date'] = spotify_track['album'].get('release_date')
                    
                    # Get artist info
                    if spotify_track.get('artists'):
                        artist_id = spotify_track['artists'][0]['id']
                        try:
                            artist_info = spotify_client.artist(artist_id)
                            metadata['artist_genres'] = artist_info.get('genres', [])
                        except Exception as e:
                            logger.warning(f"Could not fetch artist genres: {e}")
                    
                    # Mark as enriched
                    metadata['spotify_enriched'] = True
                    
                    logger.info(f"Enriched with Spotify data: {metadata['title']}")
                    
            except Exception as e:
                logger.warning(f"Could not enrich with Spotify data: {e}")
                metadata['spotify_enriched'] = False
        else:
            metadata['spotify_enriched'] = False
        
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
