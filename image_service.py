"""
Image Service for Mood Board
Fetches aesthetic images from multiple sources: Unsplash, Pexels, Pixabay
Supports fallback to Spotify images if external APIs fail
"""

import os
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import quote


class ImageService:
    """Service for fetching aesthetic images from external sources"""

    def __init__(self):
        # Unsplash API
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        self.unsplash_base_url = 'https://api.unsplash.com'

        # Pexels API
        self.pexels_api_key = os.getenv('PEXELS_API_KEY')
        self.pexels_base_url = 'https://api.pexels.com/v1'

        # Pixabay API
        self.pixabay_api_key = os.getenv('PIXABAY_API_KEY')
        self.pixabay_base_url = 'https://pixabay.com/api'

        self.session = requests.Session()

    def search_unsplash(self, query: str, count: int = 5, orientation: str = 'portrait') -> List[Dict]:
        """
        Search for images on Unsplash by query

        Args:
            query: Search term (e.g., "indie rock aesthetic", "chill vibes")
            count: Number of images to fetch (default: 5)
            orientation: Image orientation - 'portrait', 'landscape', or 'squarish' (default: 'portrait')

        Returns:
            List of image dictionaries with url, title, artist, photographer info
        """
        if not self.unsplash_access_key:
            return []

        try:
            import random

            endpoint = f'{self.unsplash_base_url}/search/photos'
            headers = {
                'Authorization': f'Client-ID {self.unsplash_access_key}',
                'Accept-Version': 'v1'
            }

            # Request MORE images than needed, then randomly sample
            # This prevents getting the same top results every time
            request_count = min(count * 3, 30)  # Request 3x what we need (max 30)

            params = {
                'query': query,
                'per_page': request_count,
                'orientation': orientation,
                'content_filter': 'high',
            }

            response = self.session.get(endpoint, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            images = []

            for photo in data.get('results', []):
                images.append({
                    'url': photo['urls']['regular'],
                    'thumb_url': photo['urls']['small'],
                    'title': photo.get('description') or photo.get('alt_description') or query,
                    'photographer': photo['user']['name'],
                    'photographer_url': photo['user']['links']['html'] + '?utm_source=MelodySearch&utm_medium=referral',
                    'download_location': photo['links']['download_location'],
                    'type': 'unsplash',
                    'source': 'unsplash',
                    'keywords': query,
                    'color': photo.get('color', '#000000'),
                    'width': photo['width'],
                    'height': photo['height']
                })

            # Randomly sample to get variety (not just top results)
            if len(images) > count:
                images = random.sample(images, count)

            logging.info(f"Fetched {len(images)} images from Unsplash for query: {query}")
            return images

        except Exception as e:
            logging.error(f"Error fetching images from Unsplash: {e}")
            return []

    def search_pexels(self, query: str, count: int = 5, orientation: str = 'portrait') -> List[Dict]:
        """Search for images on Pexels"""
        if not self.pexels_api_key:
            return []

        try:
            endpoint = f'{self.pexels_base_url}/search'
            headers = {'Authorization': self.pexels_api_key}

            params = {
                'query': query,
                'per_page': min(count, 80),
                'orientation': orientation
            }

            response = self.session.get(endpoint, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            images = []

            for photo in data.get('photos', []):
                images.append({
                    'url': photo['src']['large'],
                    'thumb_url': photo['src']['medium'],
                    'title': photo.get('alt') or query,
                    'photographer': photo['photographer'],
                    'photographer_url': photo['photographer_url'] + '?utm_source=MelodySearch&utm_medium=referral',
                    'type': 'pexels',
                    'source': 'pexels',
                    'keywords': query,
                    'color': photo.get('avg_color', '#000000'),
                    'width': photo['width'],
                    'height': photo['height']
                })

            logging.info(f"Fetched {len(images)} images from Pexels for query: {query}")
            return images

        except Exception as e:
            logging.error(f"Error fetching images from Pexels: {e}")
            return []

    def search_pixabay(self, query: str, count: int = 5, orientation: str = 'vertical') -> List[Dict]:
        """Search for images on Pixabay"""
        if not self.pixabay_api_key:
            return []

        try:
            endpoint = self.pixabay_base_url

            params = {
                'key': self.pixabay_api_key,
                'q': query,
                'per_page': min(count, 200),
                'orientation': orientation,
                'safesearch': 'true',
                'image_type': 'photo'
            }

            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            images = []

            for photo in data.get('hits', []):
                images.append({
                    'url': photo['largeImageURL'],
                    'thumb_url': photo['webformatURL'],
                    'title': photo.get('tags') or query,
                    'photographer': photo['user'],
                    'photographer_url': f"https://pixabay.com/users/{photo['user']}-{photo['user_id']}/?utm_source=MelodySearch&utm_medium=referral",
                    'type': 'pixabay',
                    'source': 'pixabay',
                    'keywords': query,
                    'color': '#000000',
                    'width': photo['imageWidth'],
                    'height': photo['imageHeight']
                })

            logging.info(f"Fetched {len(images)} images from Pixabay for query: {query}")
            return images

        except Exception as e:
            logging.error(f"Error fetching images from Pixabay: {e}")
            return []

    def search_images(self, query: str, count: int = 5, orientation: str = 'portrait', sources: List[str] = None) -> List[Dict]:
        """
        Search for images across multiple sources

        Args:
            query: Search term
            count: Number of images to fetch
            orientation: Image orientation
            sources: List of sources to search ['unsplash', 'pexels', 'pixabay']. If None, tries all available.

        Returns:
            Mixed list of images from multiple sources
        """
        if sources is None:
            sources = ['unsplash', 'pexels', 'pixabay']

        all_images = []
        images_per_source = max(1, count // len(sources))

        for source in sources:
            if source == 'unsplash' and self.unsplash_access_key:
                images = self.search_unsplash(query, images_per_source, orientation)
                all_images.extend(images)
            elif source == 'pexels' and self.pexels_api_key:
                images = self.search_pexels(query, images_per_source, orientation)
                all_images.extend(images)
            elif source == 'pixabay' and self.pixabay_api_key:
                pix_orientation = 'vertical' if orientation == 'portrait' else 'horizontal'
                images = self.search_pixabay(query, images_per_source, pix_orientation)
                all_images.extend(images)

        # Shuffle to mix sources
        import random
        random.shuffle(all_images)

        return all_images[:count]

    def trigger_download(self, download_location: str):
        """
        Trigger download tracking for Unsplash API compliance
        Must be called when an image is displayed to the user

        Args:
            download_location: The download_location URL from the photo object
        """
        if not self.unsplash_access_key or not download_location:
            return

        try:
            # Trigger download endpoint (required by Unsplash API guidelines)
            self.session.get(download_location, timeout=5)
        except Exception as e:
            logging.warning(f"Failed to trigger Unsplash download tracking: {e}")

    def generate_mood_keywords(self, track_name: str, artist_name: str, genres: List[str] = None) -> List[str]:
        """
        Generate search keywords for mood board based on track metadata

        Focus on ACTUAL music-related content: artists, albums, songs
        NOT generic aesthetics

        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            genres: List of genre tags (optional)

        Returns:
            List of search keyword combinations
        """
        keywords = []

        # PRIMARY: Actual artist/music searches (80% of keywords)
        if artist_name:
            keywords.append(f"{artist_name}")  # Direct artist search
            keywords.append(f"{artist_name} album")
            keywords.append(f"{artist_name} concert")
            keywords.append(f"{artist_name} performance")
            keywords.append(f"{artist_name} photoshoot")
            keywords.append(f"{artist_name} rapper")  # For hip-hop artists

        # SECONDARY: Genre-specific but still music-focused (15% of keywords)
        if genres:
            for genre in genres[:2]:  # Top 2 genres only
                genre_lower = genre.lower()
                # Keep it music-focused, not just "aesthetic vibes"
                if 'hip hop' in genre_lower or 'rap' in genre_lower:
                    keywords.extend([f'{genre} artist', 'rap concert'])
                elif 'indie' in genre_lower or 'alternative' in genre_lower:
                    keywords.extend([f'{genre} band', 'indie concert'])
                elif 'electronic' in genre_lower or 'edm' in genre_lower:
                    keywords.extend([f'{genre} artist', 'electronic music festival'])
                elif 'rock' in genre_lower:
                    keywords.extend([f'{genre} band', 'rock concert'])
                elif 'pop' in genre_lower:
                    keywords.extend([f'{genre} artist', 'pop music'])
                elif 'r&b' in genre_lower or 'soul' in genre_lower:
                    keywords.extend([f'{genre} artist', 'r&b performance'])
                else:
                    keywords.append(f"{genre} music")

        # MINIMAL: Only a FEW generic music keywords (5% of keywords)
        # Just to add variety, but keep it music-related
        music_keywords = [
            "music studio",
            "vinyl records",
            "concert crowd"
        ]
        keywords.extend(music_keywords[:1])  # Only add 1 generic keyword

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)

        return unique_keywords

    def fetch_mood_board_images(self, tracks: List[Dict], total_images: int = 15) -> List[Dict]:
        """
        Fetch a collection of aesthetic images based on listening history

        Args:
            tracks: List of track dictionaries with 'name', 'artist', 'genres' etc.
            total_images: Total number of images to fetch

        Returns:
            List of image dictionaries
        """
        import random

        all_images = []

        # Deduplicate by (artist, album) to avoid repetitive searches
        seen_combinations = set()
        unique_tracks = []

        for track in tracks:
            key = (track.get('artist', '').lower(), track.get('album', '').lower())
            if key not in seen_combinations and key != ('', ''):
                seen_combinations.add(key)
                unique_tracks.append(track)

        if not unique_tracks:
            unique_tracks = tracks[:5]  # Fallback to first 5 if deduplication fails

        # Calculate images per unique track
        images_per_track = max(1, total_images // len(unique_tracks)) if unique_tracks else 1

        # Generate diverse keywords from all tracks
        all_keywords = []
        for track in unique_tracks:
            keywords = self.generate_mood_keywords(
                track.get('name', ''),
                track.get('artist', ''),
                track.get('genres', [])
            )
            # Include MORE artist/song-related keywords (not just generic aesthetics)
            # Prioritize keywords that include artist name, album, or music-specific terms
            all_keywords.extend(keywords[:4])  # Take top 4 per track (increased from 2)

        # MINIMAL generic keywords - only if we don't have enough artist keywords
        # Photos should be ABOUT the music, not random aesthetics
        if len(all_keywords) < 20:  # Only add if we need more keywords
            generic_keywords = ["music studio", "vinyl records", "concert stage"]
            all_keywords.extend(random.sample(generic_keywords, min(1, len(generic_keywords))))

        # Shuffle keywords for randomness
        random.shuffle(all_keywords)

        # Fetch images using diverse keywords
        keywords_used = set()
        for keyword in all_keywords:
            if len(all_images) >= total_images:
                break

            # Skip if we already used this exact keyword
            if keyword.lower() in keywords_used:
                continue
            keywords_used.add(keyword.lower())

            images = self.search_images(
                keyword,
                count=min(images_per_track, total_images - len(all_images)),
                orientation='portrait'
            )

            # Add track context to images (use first unique track)
            if unique_tracks:
                track = unique_tracks[len(all_images) % len(unique_tracks)]
                for img in images:
                    img['related_track'] = track.get('name')
                    img['related_artist'] = track.get('artist')

            all_images.extend(images)

        # Shuffle for variety
        random.shuffle(all_images)
        return all_images[:total_images]


# Global instance
_image_service = None

def get_image_service() -> ImageService:
    """Get or create the global ImageService instance"""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service
