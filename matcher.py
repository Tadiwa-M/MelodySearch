# metadata_similarity_engine.py
import spotipy
import requests
import logging
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


class MetadataSimilarityEngine:
    """
    Cross-genre similarity engine using metadata instead of audio analysis
    Since Spotify's audio APIs are dead, we use available metadata creatively
    """

    def __init__(self, spotify_client: spotipy.Spotify, lastfm_api_key: Optional[str] = None):
        self.sp = spotify_client
        self.lastfm_key = lastfm_api_key
        self.genre_embeddings = self._create_genre_embeddings()

    def extract_comprehensive_metadata(self, track_id: str, track_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract rich metadata for similarity matching
        """
        if not track_info:
            track_info = self.sp.track(track_id)

        artist_id = track_info['artists'][0]['id']
        album_id = track_info['album']['id']

        # Get artist info (genres, popularity, followers)
        artist_info = self.sp.artist(artist_id)

        # Get album info (release date, genre context)
        album_info = self.sp.album(album_id)

        # Extract features
        features = {
            # Basic track features
            'title': track_info['name'],
            'artist': track_info['artists'][0]['name'],
            'duration_ms': track_info['duration_ms'],
            'popularity': track_info['popularity'],
            'explicit': track_info['explicit'],
            'release_year': int(track_info['album']['release_date'][:4]),

            # Artist features
            'artist_genres': artist_info['genres'],
            'artist_popularity': artist_info['popularity'],
            'artist_followers': artist_info['followers']['total'],

            # Album context
            'album_type': album_info['album_type'],  # album, single, compilation
            'total_tracks': album_info['total_tracks'],

            # Derived features
            'duration_category': self._categorize_duration(track_info['duration_ms']),
            'era': self._categorize_era(int(track_info['album']['release_date'][:4])),
            'mainstream_level': self._categorize_mainstream(track_info['popularity']),
            'genre_primary': self._extract_primary_genre(artist_info['genres']),
            'genre_secondary': self._extract_secondary_genres(artist_info['genres']),

            # Text features for analysis
            'title_words': self._extract_title_keywords(track_info['name']),
            'artist_name_style': self._analyze_artist_name(track_info['artists'][0]['name']),
        }

        # Try to get Last.fm data if available
        if self.lastfm_key:
            lastfm_data = self._get_lastfm_data(
                track_info['artists'][0]['name'],
                track_info['name']
            )
            features.update(lastfm_data)

        # Create similarity vector
        features['similarity_vector'] = self._create_metadata_vector(features)
        features['feature_completeness'] = self._calculate_metadata_completeness(features)

        return features

    def find_metadata_similarities(self,
                                   target_features: Dict[str, Any],
                                   candidate_pool: List[Dict[str, Any]],
                                   top_n: int = 10) -> List[Tuple[str, float, Dict[str, float]]]:
        """
        Find similar tracks using metadata-based similarity
        """
        similarities = []
        target_vector = np.array(target_features.get('similarity_vector', []))

        if len(target_vector) == 0:
            logging.warning("Target features missing similarity vector")
            return []

        for candidate in candidate_pool:
            try:
                candidate_features = candidate.get('metadata_features', {})
                if not candidate_features:
                    continue

                candidate_vector = np.array(candidate_features.get('similarity_vector', []))

                if len(candidate_vector) != len(target_vector):
                    continue

                # Calculate different types of similarity
                similarity_scores = self._calculate_metadata_similarities(
                    target_features, candidate_features, target_vector, candidate_vector
                )

                overall_similarity = self._weighted_metadata_score(similarity_scores)

                similarities.append((
                    candidate.get('title', 'Unknown'),
                    overall_similarity,
                    similarity_scores,
                    candidate
                ))

            except Exception as e:
                logging.error(f"Error calculating similarity for {candidate.get('title', 'Unknown')}: {e}")
                continue

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [(title, sim, breakdown) for title, sim, breakdown, _ in similarities[:top_n]]

    def _calculate_metadata_similarities(self,
                                         target: Dict[str, Any],
                                         candidate: Dict[str, Any],
                                         target_vector: np.ndarray,
                                         candidate_vector: np.ndarray) -> Dict[str, float]:
        """Calculate various metadata similarities"""

        similarities = {}

        # 1. GENRE SIMILARITY (using semantic embeddings)
        similarities['genre'] = self._genre_similarity(
            target.get('artist_genres', []),
            candidate.get('artist_genres', [])
        )

        # 2. TEMPORAL SIMILARITY (era-based)
        similarities['temporal'] = self._temporal_similarity(
            target.get('release_year', 2000),
            candidate.get('release_year', 2000)
        )

        # 3. POPULARITY/MAINSTREAM SIMILARITY
        similarities['mainstream'] = self._mainstream_similarity(
            target.get('popularity', 50),
            candidate.get('popularity', 50)
        )

        # 4. DURATION SIMILARITY
        similarities['duration'] = self._duration_similarity(
            target.get('duration_ms', 180000),
            candidate.get('duration_ms', 180000)
        )

        # 5. ARTIST STYLE SIMILARITY
        similarities['artist_style'] = self._artist_style_similarity(
            target.get('artist_name_style', {}),
            candidate.get('artist_name_style', {})
        )

        # 6. TITLE CONTENT SIMILARITY
        similarities['title_content'] = self._title_similarity(
            target.get('title_words', []),
            candidate.get('title_words', [])
        )

        # 7. VECTOR SIMILARITY (overall metadata)
        similarities['vector_cosine'] = self._safe_cosine_similarity(target_vector, candidate_vector)

        # 8. LAST.FM SIMILARITY (if available)
        if 'lastfm_tags' in target and 'lastfm_tags' in candidate:
            similarities['lastfm_tags'] = self._lastfm_tag_similarity(
                target['lastfm_tags'], candidate['lastfm_tags']
            )

        return similarities

    def _create_genre_embeddings(self) -> Dict[str, np.ndarray]:
        """Create semantic embeddings for music genres"""
        # Simplified genre relationships (in reality, you'd use Word2Vec or similar)
        genre_groups = {
            'electronic': ['electronic', 'techno', 'house', 'ambient', 'edm', 'dubstep', 'trance'],
            'rock': ['rock', 'alternative rock', 'indie rock', 'punk', 'metal', 'grunge'],
            'hip_hop': ['hip hop', 'rap', 'trap', 'drill', 'grime', 'uk hip hop'],
            'pop': ['pop', 'dance pop', 'electropop', 'synthpop', 'art pop'],
            'jazz': ['jazz', 'smooth jazz', 'fusion', 'bebop', 'contemporary jazz'],
            'classical': ['classical', 'orchestral', 'chamber', 'baroque', 'romantic'],
            'folk': ['folk', 'indie folk', 'americana', 'country', 'bluegrass'],
            'r&b': ['r&b', 'soul', 'funk', 'motown', 'contemporary r&b'],
            'latin': ['latin', 'reggaeton', 'salsa', 'bachata', 'latin pop']
        }

        embeddings = {}
        for group_name, genres in genre_groups.items():
            # Create simple embedding based on group relationships
            base_vector = np.random.seed(hash(group_name) % 1000)  # Consistent randomness
            np.random.seed(hash(group_name) % 1000)
            group_embedding = np.random.rand(20)  # 20-dimensional embedding

            for genre in genres:
                # Add some noise for individual genres
                np.random.seed(hash(genre) % 1000)
                noise = np.random.rand(20) * 0.3
                embeddings[genre.lower()] = group_embedding + noise

        return embeddings

    def _genre_similarity(self, genres1: List[str], genres2: List[str]) -> float:
        """Calculate semantic similarity between genre lists"""
        if not genres1 or not genres2:
            return 0.3  # Neutral similarity

        # Convert to embeddings
        embeddings1 = [self.genre_embeddings.get(g.lower(), np.zeros(20)) for g in genres1]
        embeddings2 = [self.genre_embeddings.get(g.lower(), np.zeros(20)) for g in genres2]

        if not embeddings1 or not embeddings2:
            return 0.3

        # Calculate average embeddings
        avg_emb1 = np.mean(embeddings1, axis=0)
        avg_emb2 = np.mean(embeddings2, axis=0)

        # Cosine similarity
        return self._safe_cosine_similarity(avg_emb1, avg_emb2)

    def _temporal_similarity(self, year1: int, year2: int) -> float:
        """Similarity based on release years"""
        year_diff = abs(year1 - year2)

        if year_diff == 0:
            return 1.0
        elif year_diff <= 2:
            return 0.9
        elif year_diff <= 5:
            return 0.7
        elif year_diff <= 10:
            return 0.5
        elif year_diff <= 20:
            return 0.3
        else:
            return 0.1

    def _mainstream_similarity(self, pop1: int, pop2: int) -> float:
        """Similarity based on popularity scores"""
        pop_diff = abs(pop1 - pop2)
        return max(0, 1 - pop_diff / 100)

    def _duration_similarity(self, dur1: int, dur2: int) -> float:
        """Similarity based on song duration"""
        dur_diff_seconds = abs(dur1 - dur2) / 1000

        if dur_diff_seconds <= 30:
            return 1.0
        elif dur_diff_seconds <= 60:
            return 0.8
        elif dur_diff_seconds <= 120:
            return 0.6
        else:
            return max(0.2, 1 - dur_diff_seconds / 600)  # Max 10 minutes difference

    def _create_metadata_vector(self, features: Dict[str, Any]) -> List[float]:
        """Create numerical vector from metadata features"""
        vector = []

        # Numerical features (normalized)
        vector.append(features.get('duration_ms', 180000) / 600000)  # Max 10 minutes
        vector.append(features.get('popularity', 50) / 100)
        vector.append(features.get('artist_popularity', 50) / 100)
        vector.append(min(features.get('artist_followers', 0) / 1000000, 1))  # Max 1M followers
        vector.append(features.get('release_year', 2000) / 2025)  # Normalized to current year
        vector.append(features.get('total_tracks', 1) / 50)  # Max 50 tracks per album

        # Categorical features (one-hot style)
        vector.append(1 if features.get('explicit', False) else 0)

        # Duration category
        duration_cats = {'short': [1, 0, 0], 'medium': [0, 1, 0], 'long': [0, 0, 1]}
        vector.extend(duration_cats.get(features.get('duration_category', 'medium'), [0, 1, 0]))

        # Era category
        era_cats = {'classic': [1, 0, 0, 0], 'vintage': [0, 1, 0, 0], 'modern': [0, 0, 1, 0], 'current': [0, 0, 0, 1]}
        vector.extend(era_cats.get(features.get('era', 'modern'), [0, 0, 1, 0]))

        # Mainstream level
        main_cats = {'underground': [1, 0, 0], 'mid_tier': [0, 1, 0], 'mainstream': [0, 0, 1]}
        vector.extend(main_cats.get(features.get('mainstream_level', 'mid_tier'), [0, 1, 0]))

        # Genre embeddings (if available)
        if features.get('genre_primary') and features['genre_primary'].lower() in self.genre_embeddings:
            primary_emb = self.genre_embeddings[features['genre_primary'].lower()]
            vector.extend(primary_emb[:10])  # First 10 dimensions
        else:
            vector.extend([0.5] * 10)  # Neutral values

        return vector

    def _categorize_duration(self, duration_ms: int) -> str:
        """Categorize song duration"""
        duration_sec = duration_ms / 1000
        if duration_sec < 150:
            return 'short'
        elif duration_sec < 300:
            return 'medium'
        else:
            return 'long'

    def _categorize_era(self, year: int) -> str:
        """Categorize release era"""
        if year < 1980:
            return 'classic'
        elif year < 2000:
            return 'vintage'
        elif year < 2015:
            return 'modern'
        else:
            return 'current'

    def _categorize_mainstream(self, popularity: int) -> str:
        """Categorize mainstream level"""
        if popularity < 30:
            return 'underground'
        elif popularity < 70:
            return 'mid_tier'
        else:
            return 'mainstream'

    def _extract_primary_genre(self, genres: List[str]) -> Optional[str]:
        """Extract primary genre from genre list"""
        if not genres:
            return None
        return genres[0]  # First genre is usually primary

    def _extract_secondary_genres(self, genres: List[str]) -> List[str]:
        """Extract secondary genres"""
        return genres[1:4] if len(genres) > 1 else []

    def _extract_title_keywords(self, title: str) -> List[str]:
        """Extract meaningful keywords from title"""
        # Remove common words and punctuation
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is',
                      'are', 'was', 'were'}
        words = re.findall(r'\b[a-zA-Z]+\b', title.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _analyze_artist_name(self, artist_name: str) -> Dict[str, Any]:
        """Analyze artist name characteristics"""
        return {
            'length': len(artist_name),
            'word_count': len(artist_name.split()),
            'has_numbers': bool(re.search(r'\d', artist_name)),
            'has_special_chars': bool(re.search(r'[^a-zA-Z0-9\s]', artist_name)),
            'is_uppercase': artist_name.isupper(),
            'is_lowercase': artist_name.islower()
        }

    def _safe_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Safe cosine similarity calculation"""
        try:
            if len(vec1) != len(vec2) or np.allclose(vec1, 0) or np.allclose(vec2, 0):
                return 0.5
            similarity = cosine_similarity(vec1.reshape(1, -1), vec2.reshape(1, -1))[0][0]
            return max(0, min(1, similarity))
        except:
            return 0.5

    def _weighted_metadata_score(self, similarities: Dict[str, float]) -> float:
        """Calculate weighted overall similarity"""
        weights = {
            'genre': 0.35,  # Most important for cross-genre discovery
            'temporal': 0.15,  # Era matters
            'mainstream': 0.10,  # Underground vs mainstream
            'duration': 0.05,  # Song length
            'artist_style': 0.10,  # Artist characteristics
            'title_content': 0.05,  # Title similarity
            'vector_cosine': 0.20,  # Overall metadata vector
        }

        weighted_sum = 0
        total_weight = 0

        for feature, weight in weights.items():
            if feature in similarities:
                weighted_sum += similarities[feature] * weight
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def explain_metadata_similarity(self, similarity_scores: Dict[str, float]) -> str:
        """Generate explanation for metadata similarity"""
        explanations = []

        sorted_scores = sorted(similarity_scores.items(), key=lambda x: x[1], reverse=True)

        for aspect, score in sorted_scores[:3]:
            if score > 0.6:
                if aspect == 'genre':
                    explanations.append(f"Similar musical genres (match: {score:.1%})")
                elif aspect == 'temporal':
                    explanations.append(f"From similar time period (match: {score:.1%})")
                elif aspect == 'mainstream':
                    explanations.append(f"Similar popularity level (match: {score:.1%})")
                elif aspect == 'duration':
                    explanations.append(f"Similar song length (match: {score:.1%})")

        return " • ".join(explanations) if explanations else "Similar overall characteristics"