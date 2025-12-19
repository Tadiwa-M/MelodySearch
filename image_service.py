"""
Image Service for Mood Board
Fetches aesthetic images from Unsplash API based on music metadata
Supports fallback to Spotify images if external API fails
"""

import os
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import quote


class ImageService:
    """Service for fetching aesthetic images from external sources"""

    def __init__(self):
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        self.unsplash_base_url = 'https://api.unsplash.com'
        self.session = requests.Session()

        # Set up headers for Unsplash API
        if self.unsplash_access_key:
            self.session.headers.update({
                'Authorization': f'Client-ID {self.unsplash_access_key}',
                'Accept-Version': 'v1'
            })

    def search_images(self, query: str, count: int = 5, orientation: str = 'portrait') -> List[Dict]:
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
            logging.warning("Unsplash API key not configured")
            return []

        try:
            # Unsplash API endpoint for photo search
            endpoint = f'{self.unsplash_base_url}/search/photos'

            params = {
                'query': query,
                'per_page': min(count, 30),  # Unsplash max is 30
                'orientation': orientation,
                'content_filter': 'high',  # Filter out inappropriate content
            }

            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            images = []

            for photo in data.get('results', []):
                images.append({
                    'url': photo['urls']['regular'],  # 1080px wide
                    'thumb_url': photo['urls']['small'],  # 400px wide
                    'title': photo.get('description') or photo.get('alt_description') or query,
                    'photographer': photo['user']['name'],
                    'photographer_url': photo['user']['links']['html'],
                    'download_location': photo['links']['download_location'],  # Required for API compliance
                    'type': 'unsplash',
                    'keywords': query,
                    'color': photo.get('color', '#000000'),
                    'width': photo['width'],
                    'height': photo['height']
                })

            logging.info(f"Fetched {len(images)} images from Unsplash for query: {query}")
            return images

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching images from Unsplash: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in image search: {e}", exc_info=True)
            return []

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

        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            genres: List of genre tags (optional)

        Returns:
            List of search keyword combinations
        """
        keywords = []

        # Strategy 1: Artist + aesthetic
        keywords.append(f"{artist_name} aesthetic")

        # Strategy 2: Genre + vibes/aesthetic
        if genres:
            for genre in genres[:2]:  # Limit to first 2 genres
                keywords.append(f"{genre} vibes")
                keywords.append(f"{genre} aesthetic")

        # Strategy 3: Track name + mood
        keywords.append(f"{track_name} mood")

        # Strategy 4: Generic mood keywords based on common music vibes
        mood_keywords = [
            "music aesthetic",
            "indie aesthetic",
            "retro vibes",
            "neon lights aesthetic",
            "concert aesthetic",
            "vinyl aesthetic"
        ]
        keywords.extend(mood_keywords[:2])

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
        all_images = []
        images_per_track = max(1, total_images // len(tracks)) if tracks else 1

        for track in tracks:
            if len(all_images) >= total_images:
                break

            # Generate keywords for this track
            keywords = self.generate_mood_keywords(
                track.get('name', ''),
                track.get('artist', ''),
                track.get('genres', [])
            )

            # Try each keyword until we get images
            for keyword in keywords:
                if len(all_images) >= total_images:
                    break

                images = self.search_images(
                    keyword,
                    count=images_per_track,
                    orientation='portrait'
                )

                # Add track context to images
                for img in images:
                    img['related_track'] = track.get('name')
                    img['related_artist'] = track.get('artist')

                all_images.extend(images)

                # If we got images, move to next track
                if images:
                    break

        # Return up to total_images, shuffled for variety
        import random
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
