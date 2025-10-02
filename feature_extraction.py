# enhanced_feature_extraction.py
import logging
import requests
import tempfile
import os
import numpy as np
from typing import Dict, Optional, Any
import spotipy


class HybridFeatureExtractor:
    """
    Hybrid audio feature extraction using:
    1. Spotify's Audio Analysis API (still available)
    2. Essentia.js fallback for tracks without Spotify data
    3. Mathematical feature comparison for cross-genre similarity
    """

    def __init__(self, spotify_client: spotipy.Spotify):
        self.sp = spotify_client

    def extract_comprehensive_features(self, track_id: str, preview_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Main extraction method - tries Spotify first, falls back to Essentia.js
        """
        features = {}

        # Phase 1: Try Spotify Audio Analysis API (the one that still works)
        spotify_features = self.extract_spotify_audio_analysis(track_id)
        if spotify_features:
            features.update(spotify_features)
            features['primary_source'] = 'spotify_analysis'
            logging.info(f"✓ Spotify Audio Analysis successful for track {track_id}")
        else:
            logging.warning(f"✗ Spotify Audio Analysis failed for track {track_id}")

        # Phase 2: If Spotify failed or incomplete, try Essentia.js on preview
        if preview_url and (not spotify_features or self._needs_essentia_supplement(spotify_features)):
            essentia_features = self.extract_essentia_features(preview_url)
            if essentia_features:
                features.update(essentia_features)
                features['secondary_source'] = 'essentia'
                logging.info(f"✓ Essentia.js analysis successful for preview")

        # Phase 3: Create mathematical feature vectors for similarity
        if features:
            features['similarity_vector'] = self._create_similarity_vector(features)
            features['feature_completeness'] = self._calculate_completeness(features)

        return features if features else self._create_minimal_fallback()

    def extract_spotify_audio_analysis(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract features using Spotify's Audio Analysis API (not the deprecated Audio Features)
        This endpoint provides: tempo, key, mode, time_signature, beats, bars, sections
        """
        try:
            # Get audio analysis (detailed breakdown)
            analysis = self.sp.audio_analysis(track_id)

            # Get basic audio features (try both endpoints)
            audio_features = {}
            try:
                # Try the audio_features endpoint first
                features_result = self.sp.audio_features([track_id])
                if features_result and features_result[0]:
                    audio_features = features_result[0]
            except Exception as e:
                logging.warning(f"Audio features endpoint failed: {e}")

            # If audio_features failed, try getting track details for basic info
            if not audio_features:
                try:
                    track_details = self.sp.track(track_id)
                    audio_features = {
                        'energy': None,
                        'valence': None,
                        'danceability': None,
                        'acousticness': None,
                        'instrumentalness': None,
                        'speechiness': None,
                        'liveness': None,
                        'duration_ms': track_details.get('duration_ms'),
                        'popularity': track_details.get('popularity', 50) / 100  # Normalize to 0-1
                    }
                except Exception as e2:
                    logging.warning(f"Track details fallback failed: {e2}")
                    audio_features = {}

            # Extract mathematical features from analysis
            features = {
                # Rhythm features
                'tempo': analysis['track']['tempo'],
                'time_signature': analysis['track']['time_signature'],
                'rhythm_stability': self._calculate_rhythm_stability(analysis['beats']),
                'beat_strength': self._calculate_beat_strength(analysis['beats']),

                # Tonal features
                'key': analysis['track']['key'],
                'mode': analysis['track']['mode'],  # Major/Minor
                'key_confidence': analysis['track']['key_confidence'],
                'mode_confidence': analysis['track']['mode_confidence'],

                # Structural features
                'loudness': analysis['track']['loudness'],
                'duration': analysis['track']['duration'],
                'fade_in': analysis['track']['start_of_fade_in'],
                'fade_out': analysis['track']['start_of_fade_out'],

                # Section-based features
                'section_count': len(analysis['sections']),
                'avg_section_duration': np.mean([s['duration'] for s in analysis['sections']]),
                'section_tempo_variance': np.var([s['tempo'] for s in analysis['sections']]),
                'section_loudness_variance': np.var([s['loudness'] for s in analysis['sections']]),

                # Advanced timbral features from segments
                'timbral_vector': self._extract_timbral_features(analysis['segments']),
                'pitch_vector': self._extract_pitch_features(analysis['segments']),

                # Available audio features (if endpoint still works)
                'energy': audio_features.get('energy'),
                'valence': audio_features.get('valence'),
                'danceability': audio_features.get('danceability'),
                'acousticness': audio_features.get('acousticness'),
                'instrumentalness': audio_features.get('instrumentalness'),
                'speechiness': audio_features.get('speechiness'),
                'liveness': audio_features.get('liveness'),
            }

            # Clean up None values
            return {k: v for k, v in features.items() if v is not None}

        except Exception as e:
            logging.error(f"Spotify Audio Analysis failed: {e}")
            return None

    def extract_essentia_features(self, preview_url: str) -> Optional[Dict[str, Any]]:
        """
        Use Essentia.js for client-side audio analysis when Spotify data unavailable
        """
        try:
            # Download preview for analysis
            response = requests.get(preview_url, timeout=30)
            if response.status_code != 200:
                return None

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name

            try:
                # This would integrate with your frontend Essentia.js analysis
                # For now, placeholder for the structure you'd get
                features = {
                    'essentia_tempo': None,  # Will be filled by frontend
                    'essentia_key': None,
                    'essentia_energy': None,
                    'essentia_danceability': None,
                    'essentia_spectral_centroid': None,
                    'essentia_spectral_rolloff': None,
                    'essentia_mfcc': None,  # 13 coefficients
                    'essentia_chroma': None,  # 12 pitch classes
                    'preview_analyzed_path': temp_path  # Pass to frontend
                }
                return features

            finally:
                # Don't delete yet - frontend needs it
                pass

        except Exception as e:
            logging.error(f"Essentia analysis prep failed: {e}")
            return None

    def _extract_timbral_features(self, segments) -> list:
        """Extract average timbral characteristics from segments"""
        if not segments:
            return [0] * 12

        # Each segment has 12 timbral features
        timbral_matrix = np.array([seg['timbre'] for seg in segments])
        return np.mean(timbral_matrix, axis=0).tolist()

    def _extract_pitch_features(self, segments) -> list:
        """Extract average pitch characteristics from segments"""
        if not segments:
            return [0] * 12

        # Each segment has 12 pitch features (chroma)
        pitch_matrix = np.array([seg['pitches'] for seg in segments])
        return np.mean(pitch_matrix, axis=0).tolist()

    def _calculate_rhythm_stability(self, beats) -> float:
        """Calculate how stable the rhythm is (lower variance = more stable)"""
        if len(beats) < 2:
            return 0.5

        intervals = [beats[i]['start'] - beats[i - 1]['start'] for i in range(1, len(beats))]
        return float(1.0 / (1.0 + np.var(intervals)))

    def _calculate_beat_strength(self, beats) -> float:
        """Calculate average beat confidence/strength"""
        if not beats:
            return 0.5

        confidences = [beat['confidence'] for beat in beats]
        return float(np.mean(confidences))

    def _create_similarity_vector(self, features: Dict[str, Any]) -> list:
        """
        Create a standardized vector for mathematical similarity comparison
        This is the core of cross-genre similarity!
        """
        vector = []

        # Rhythm features (normalized)
        tempo = features.get('tempo', 120)
        vector.extend([
            tempo / 200.0,  # Normalize tempo to 0-1
            features.get('rhythm_stability', 0.5),
            features.get('beat_strength', 0.5),
            features.get('time_signature', 4) / 7.0  # Most common: 4/4, max reasonable: 7/4
        ])

        # Tonal features
        key = features.get('key', 6)  # C major = 0, normalize to 0-1
        mode = features.get('mode', 1)  # Major=1, Minor=0
        vector.extend([
            key / 11.0,  # 12 keys: 0-11
            mode,  # Already 0 or 1
            features.get('key_confidence', 0.5),
            features.get('mode_confidence', 0.5)
        ])

        # Energy/Mood features
        vector.extend([
            max(0, min(1, (features.get('loudness', -10) + 60) / 60)),  # Normalize loudness
            features.get('energy', 0.5),
            features.get('valence', 0.5),
            features.get('danceability', 0.5)
        ])

        # Texture features
        vector.extend([
            features.get('acousticness', 0.5),
            features.get('instrumentalness', 0.5),
            features.get('speechiness', 0.5)
        ])

        # Timbral features (if available)
        timbral = features.get('timbral_vector', [0] * 12)
        # Normalize timbral features to reasonable range
        timbral_normalized = [(t + 100) / 200 for t in timbral[:12]]  # Rough normalization
        vector.extend(timbral_normalized)

        # Pitch features (already 0-1 from Spotify)
        pitch = features.get('pitch_vector', [0] * 12)
        vector.extend(pitch[:12])

        return vector

    def _needs_essentia_supplement(self, spotify_features: Dict[str, Any]) -> bool:
        """Check if we need Essentia.js to supplement missing Spotify data"""
        critical_features = ['tempo', 'energy', 'timbral_vector', 'pitch_vector']
        missing_count = sum(1 for f in critical_features if not spotify_features.get(f))
        return missing_count > 1  # If more than 1 critical feature missing

    def _calculate_completeness(self, features: Dict[str, Any]) -> float:
        """Calculate how complete our feature extraction is (0-1)"""
        total_features = [
            'tempo', 'key', 'mode', 'energy', 'valence', 'danceability',
            'acousticness', 'instrumentalness', 'timbral_vector', 'pitch_vector',
            'rhythm_stability', 'beat_strength'
        ]

        present_features = sum(1 for f in total_features if features.get(f) is not None)
        return present_features / len(total_features)

    def _create_minimal_fallback(self) -> Dict[str, Any]:
        """Last resort fallback with minimal features"""
        return {
            'tempo': 120,
            'key': 6,  # C major
            'mode': 1,  # Major
            'energy': 0.5,
            'valence': 0.5,
            'similarity_vector': [0.5] * 43,  # Average values
            'feature_completeness': 0.1,
            'primary_source': 'fallback'
        }


# Usage example in your server.py:
def analyze_track_comprehensive(sp, track_id, preview_url=None):
    """Updated analysis function using hybrid approach"""
    extractor = HybridFeatureExtractor(sp)
    features = extractor.extract_comprehensive_features(track_id, preview_url)

    logging.info(f"Feature completeness: {features.get('feature_completeness', 0):.2%}")
    logging.info(f"Primary source: {features.get('primary_source', 'unknown')}")

    return features