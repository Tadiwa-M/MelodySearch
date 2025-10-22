"""
Song Identification Module

This module provides song identification functionality using audio fingerprinting.
It can identify songs from user-provided audio files and return metadata including
title, artist, album, and cover art.

Supports multiple identification services:
- AudD API (default, free tier available)
- ACRCloud (requires paid account)
- Local fingerprinting (using dejavu library)
"""

import logging
import requests
import os
from typing import Dict, Optional, Any
import tempfile
import librosa
import numpy as np


class SongIdentifier:
    """
    Identifies songs from audio files using audio fingerprinting technology.
    """

    def __init__(self, audd_api_key: Optional[str] = None, acrcloud_config: Optional[Dict] = None):
        """
        Initialize the song identifier.
        
        Args:
            audd_api_key: API key for AudD service (get from https://audd.io/)
            acrcloud_config: Configuration dict for ACRCloud service
        """
        self.audd_api_key = audd_api_key or os.getenv('AUDD_API_KEY')
        self.acrcloud_config = acrcloud_config
        
        # AudD API endpoint
        self.audd_endpoint = "https://api.audd.io/"
        
    def identify_song(self, audio_file_path: str, method: str = "audd") -> Optional[Dict[str, Any]]:
        """
        Identify a song from an audio file.
        
        Args:
            audio_file_path: Path to the audio file
            method: Identification method to use ("audd", "acrcloud", or "local")
            
        Returns:
            Dict containing song metadata or None if identification failed
        """
        try:
            if method == "audd":
                return self._identify_with_audd(audio_file_path)
            elif method == "acrcloud":
                return self._identify_with_acrcloud(audio_file_path)
            elif method == "local":
                return self._identify_locally(audio_file_path)
            else:
                logging.error(f"Unknown identification method: {method}")
                return None
                
        except Exception as e:
            logging.error(f"Song identification failed: {e}")
            return None
    
    def _identify_with_audd(self, audio_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Identify song using AudD API.
        
        AudD provides:
        - Song title
        - Artist name
        - Album name
        - Release date
        - Album art URL
        - Spotify ID (if available)
        - Apple Music ID (if available)
        """
        try:
            # Check if API key is available
            if not self.audd_api_key:
                logging.warning("AudD API key not configured. Using free tier (limited requests).")
            
            # Prepare the audio file - AudD accepts audio files directly
            # For better results, we can extract a 10-15 second snippet
            audio_snippet = self._extract_audio_snippet(audio_file_path, duration=15)
            
            if not audio_snippet:
                # Fallback to original file if snippet extraction fails
                audio_snippet = audio_file_path
            
            # Prepare the request
            data = {
                'return': 'apple_music,spotify'  # Request additional metadata
            }
            
            if self.audd_api_key:
                data['api_token'] = self.audd_api_key
            
            files = {
                'file': open(audio_snippet, 'rb')
            }
            
            # Make the API request
            logging.info("Sending audio to AudD API for identification...")
            response = requests.post(self.audd_endpoint, data=data, files=files, timeout=30)
            
            # Close the file
            files['file'].close()
            
            # Clean up temporary snippet if created
            if audio_snippet != audio_file_path and os.path.exists(audio_snippet):
                os.unlink(audio_snippet)
            
            if response.status_code != 200:
                logging.error(f"AudD API returned status code {response.status_code}")
                return None
            
            result = response.json()
            
            # Check if song was identified
            if result.get('status') != 'success':
                logging.warning(f"AudD identification failed: {result.get('error', {}).get('error_message', 'Unknown error')}")
                return None
            
            if not result.get('result'):
                logging.info("AudD could not identify the song")
                return None
            
            # Extract metadata from result
            song_data = result['result']
            
            metadata = {
                'title': song_data.get('title'),
                'artist': song_data.get('artist'),
                'album': song_data.get('album'),
                'release_date': song_data.get('release_date'),
                'label': song_data.get('label'),
                
                # Cover art
                'cover_art': song_data.get('song_link'),  # AudD provides album art URL
                'album_art': song_data.get('song_link'),
                
                # Additional metadata
                'spotify_id': song_data.get('spotify', {}).get('id') if song_data.get('spotify') else None,
                'apple_music_id': song_data.get('apple_music', {}).get('id') if song_data.get('apple_music') else None,
                'timecode': song_data.get('timecode'),  # Where in the song the match was found
                'score': song_data.get('score', 0),  # Confidence score
                
                # Source information
                'identification_source': 'audd',
                'identified': True
            }
            
            logging.info(f"Successfully identified: {metadata['title']} by {metadata['artist']}")
            return metadata
            
        except Exception as e:
            logging.error(f"AudD identification error: {e}")
            return None
    
    def _identify_with_acrcloud(self, audio_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Identify song using ACRCloud API.
        
        Note: Requires ACRCloud account and configuration.
        """
        if not self.acrcloud_config:
            logging.error("ACRCloud configuration not provided")
            return None
        
        try:
            # ACRCloud implementation would go here
            # This requires the acrcloud SDK
            # For now, return None as it requires paid account
            logging.warning("ACRCloud identification not implemented (requires paid account)")
            return None
            
        except Exception as e:
            logging.error(f"ACRCloud identification error: {e}")
            return None
    
    def _identify_locally(self, audio_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Identify song using local fingerprinting (dejavu library).
        
        Note: Requires a pre-built fingerprint database.
        """
        try:
            # Local fingerprinting would require:
            # 1. A database of fingerprints
            # 2. dejavu library
            # 3. Significant setup
            
            logging.warning("Local identification not implemented (requires fingerprint database)")
            return None
            
        except Exception as e:
            logging.error(f"Local identification error: {e}")
            return None
    
    def _extract_audio_snippet(self, audio_file_path: str, duration: int = 15, offset: int = 30) -> Optional[str]:
        """
        Extract a snippet from the audio file for identification.
        
        Args:
            audio_file_path: Path to the audio file
            duration: Duration of snippet in seconds
            offset: Offset from start in seconds (middle of song often works better)
            
        Returns:
            Path to the temporary snippet file
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_file_path, sr=None, mono=True)
            
            # Calculate snippet boundaries
            total_duration = len(y) / sr
            
            # If audio is shorter than offset + duration, use what we have
            if total_duration < offset:
                offset = 0
            
            if total_duration < offset + duration:
                duration = int(total_duration - offset)
            
            # Extract snippet
            start_sample = int(offset * sr)
            end_sample = int((offset + duration) * sr)
            snippet = y[start_sample:end_sample]
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Save snippet
            import soundfile as sf
            sf.write(temp_path, snippet, sr)
            
            logging.debug(f"Created audio snippet: {duration}s starting at {offset}s")
            return temp_path
            
        except Exception as e:
            logging.warning(f"Could not extract audio snippet: {e}")
            return None
    
    def enrich_metadata_from_spotify(self, metadata: Dict[str, Any], spotify_client) -> Dict[str, Any]:
        """
        Enrich identified song metadata with additional data from Spotify.
        
        Args:
            metadata: Initial metadata from identification
            spotify_client: Spotipy client instance
            
        Returns:
            Enriched metadata dict
        """
        try:
            spotify_id = metadata.get('spotify_id')
            
            if not spotify_id:
                # Try to search for the song on Spotify
                query = f"{metadata.get('title', '')} {metadata.get('artist', '')}"
                results = spotify_client.search(q=query, type='track', limit=1)
                
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    spotify_id = track['id']
                else:
                    logging.warning("Could not find song on Spotify")
                    return metadata
            
            # Get full track details
            track = spotify_client.track(spotify_id)
            album = spotify_client.album(track['album']['id'])
            
            # Enrich metadata
            metadata.update({
                'title': track['name'],  # Use Spotify's official title
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'album_art': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'cover_art': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'release_date': track['album']['release_date'],
                'spotify_id': track['id'],
                'spotify_url': track['external_urls']['spotify'],
                'preview_url': track.get('preview_url'),
                'popularity': track['popularity'],
                'duration_ms': track['duration_ms'],
                'explicit': track['explicit'],
                
                # Album details
                'album_type': album['album_type'],
                'album_artist': album['artists'][0]['name'],
                'album_release_date': album['release_date'],
                'album_total_tracks': album['total_tracks'],
                'album_genres': album.get('genres', []),
                'album_label': album.get('label'),
                
                # Artist details
                'artist_id': track['artists'][0]['id'],
                
                # Enriched flag
                'spotify_enriched': True
            })
            
            # Get artist info for genres
            artist = spotify_client.artist(track['artists'][0]['id'])
            metadata['artist_genres'] = artist['genres']
            metadata['artist_popularity'] = artist['popularity']
            metadata['artist_followers'] = artist['followers']['total']
            
            logging.info(f"Successfully enriched metadata from Spotify")
            return metadata
            
        except Exception as e:
            logging.error(f"Failed to enrich metadata from Spotify: {e}")
            return metadata
