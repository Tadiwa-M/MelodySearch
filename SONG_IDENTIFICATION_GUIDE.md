# Song Identification Feature Guide 🔍

## Overview

MelodySearch now includes powerful song identification capabilities, similar to Shazam. Upload any audio file, and the system will identify the song and return comprehensive metadata including title, artist, album, and cover art.

## How It Works

The identification feature uses **audio fingerprinting** technology through the AudD API:

1. **Audio Analysis**: Extracts a unique "fingerprint" from your audio file
2. **Database Matching**: Compares the fingerprint against millions of songs
3. **Metadata Retrieval**: Returns detailed information about the identified song
4. **Spotify Enrichment**: Automatically enhances the results with Spotify data

## Setup

### 1. Get Your AudD API Key (Optional but Recommended)

The system works without an API key using the free tier, but for better reliability:

1. Go to https://audd.io/
2. Sign up for a free account
3. Get your API token (50 requests/day free, or paid plans available)
4. Add to your `.env` file:

```bash
AUDD_API_KEY=your-api-key-here
```

### 2. Ensure Spotify Credentials Are Set

The identification feature automatically enriches results with Spotify metadata:

```bash
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
```

## Usage

### Web Interface

1. **Start the Server**
   ```bash
   python server.py
   ```

2. **Open Your Browser**
   ```
   http://127.0.0.1:5000
   ```

3. **Upload Audio**
   - Click the "🔍 Identify Unknown Song" section
   - Drag and drop your audio file or click to browse
   - Supported formats: MP3, WAV, FLAC, M4A, OGG
   - Maximum file size: 16MB

4. **Get Results**
   The system will return:
   - ✓ Song title
   - ✓ Artist name
   - ✓ Album name
   - ✓ Album cover art
   - ✓ Release date
   - ✓ Genres
   - ✓ Spotify link
   - ✓ Popularity score
   - ✓ Record label
   - ✓ Additional metadata

### API Usage

#### Endpoint: `/identify`

**Method:** POST  
**Content-Type:** multipart/form-data

**Request:**
```bash
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@path/to/song.mp3"
```

**Success Response (200 OK):**
```json
{
  "message": "Song identified successfully",
  "identified": true,
  "song": {
    "title": "Blinding Lights",
    "artist": "The Weeknd",
    "album": "After Hours",
    "album_art": "https://i.scdn.co/image/ab67616d0000b273...",
    "cover_art": "https://i.scdn.co/image/ab67616d0000b273...",
    "release_date": "2019-11-29",
    "label": "Republic Records",
    "spotify_id": "0VjIjW4GlUZAMYd2vXMi3b",
    "spotify_url": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b",
    "preview_url": "https://p.scdn.co/mp3-preview/...",
    "popularity": 88,
    "duration_ms": 200040,
    "explicit": false,
    "genres": ["canadian pop", "pop"],
    "album_details": {
      "type": "album",
      "total_tracks": 14,
      "release_date": "2020-03-20",
      "label": "Republic Records"
    },
    "identification_metadata": {
      "source": "audd",
      "confidence_score": 0.95,
      "timecode": 30.5,
      "spotify_enriched": true
    }
  }
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Could not identify song",
  "message": "The song could not be identified. Please try with a clearer audio sample or a different part of the song.",
  "suggestions": [
    "Ensure the audio quality is good",
    "Try uploading a 15-30 second clip from the chorus or most recognizable part",
    "Reduce background noise if possible"
  ]
}
```

### Python SDK Usage

```python
from song_identifier import SongIdentifier
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Initialize identifier
identifier = SongIdentifier(audd_api_key="your-api-key")  # Optional

# Identify a song
metadata = identifier.identify_song("path/to/audio.mp3", method="audd")

if metadata and metadata.get('identified'):
    print(f"Identified: {metadata['title']} by {metadata['artist']}")
    
    # Enrich with Spotify data
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id="your-client-id",
        client_secret="your-client-secret"
    ))
    enriched = identifier.enrich_metadata_from_spotify(metadata, sp)
    
    print(f"Album: {enriched.get('album')}")
    print(f"Cover Art: {enriched.get('cover_art')}")
    print(f"Genres: {', '.join(enriched.get('artist_genres', []))}")
else:
    print("Could not identify the song")
```

## Best Practices

### For Best Identification Results:

1. **Audio Quality**
   - Use clear, high-quality audio recordings
   - Minimize background noise
   - Ensure the music is audible and not too quiet

2. **Clip Selection**
   - The system analyzes the first 15 seconds (configurable)
   - For best results, include the chorus or most recognizable part
   - Full songs work well, but clips of 15-30 seconds are optimal

3. **File Format**
   - MP3 is most widely supported
   - WAV provides best quality
   - FLAC for lossless quality
   - M4A and OGG also supported

4. **File Size**
   - Keep files under 16MB
   - Shorter clips (30-60 seconds) are faster to process

## Limitations

### Free Tier (No API Key)
- Limited to basic requests
- May have rate limiting
- Best for testing and development

### With AudD API Key
- **Free Tier**: 50 identifications per day
- **Paid Plans**: Higher limits available at https://audd.io/

### General Limitations
- Requires internet connection
- Song must be in the AudD database (millions of tracks)
- Very obscure or unreleased songs may not be identified
- Live recordings may be harder to identify than studio versions

## Troubleshooting

### "Could not identify song"

**Possible causes:**
1. Song not in database (too obscure or very new)
2. Audio quality too poor
3. Too much background noise
4. Wrong section of the song (try the chorus)

**Solutions:**
- Try a different 15-30 second clip from the song
- Use a clearer recording
- Ensure the music is prominent in the audio

### "Rate limit exceeded"

**Cause:** Too many requests to AudD API

**Solutions:**
1. Wait 24 hours for free tier reset
2. Get an AudD API key for higher limits
3. Upgrade to a paid AudD plan

### "API key invalid"

**Cause:** Incorrect or expired AudD API key

**Solution:** Check your API key at https://audd.io/ and update `.env`

## Technical Details

### Audio Processing

1. **Snippet Extraction**: Extracts 15-second clip from audio (configurable offset)
2. **Fingerprint Generation**: Creates unique audio fingerprint
3. **Database Query**: Matches fingerprint against AudD database
4. **Metadata Retrieval**: Gets song information
5. **Spotify Enrichment**: Adds additional metadata from Spotify

### Supported Formats

| Format | Extension | Quality | Recommended |
|--------|-----------|---------|-------------|
| MP3    | .mp3      | Good    | ✓ Yes       |
| WAV    | .wav      | Best    | ✓ Yes       |
| FLAC   | .flac     | Best    | ✓ Yes       |
| M4A    | .m4a      | Good    | ✓ Yes       |
| OGG    | .ogg      | Good    | ✓ Yes       |

### Response Time

- Typical identification: 2-5 seconds
- With Spotify enrichment: 3-6 seconds
- Upload time varies by file size

## Security & Privacy

- Audio files are processed temporarily and not stored permanently
- Files are deleted immediately after processing
- Only metadata is saved to the local database
- API keys are stored securely in environment variables
- All API communication uses HTTPS

## Comparison with Similar Songs Feature

| Feature | Song Identification | Similarity Search |
|---------|-------------------|-------------------|
| Purpose | Identify unknown songs | Find similar songs |
| Input | Any audio recording | Song name or audio |
| Output | Song metadata | List of similar tracks |
| Technology | Audio fingerprinting | Feature extraction & matching |
| Use Case | "What song is this?" | "Songs like this one?" |

Both features complement each other:
1. Use **Identification** to find out what a song is
2. Use **Similarity Search** to discover similar music

## Examples

### Example 1: Identify a Recording

```bash
# You recorded a song from the radio
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@recording.mp3"

# Result: "Blinding Lights by The Weeknd"
```

### Example 2: Identify Background Music

```bash
# You have a video with background music
# Extract audio first, then:
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@background_music.wav"
```

### Example 3: Batch Processing (Python)

```python
import os
from song_identifier import SongIdentifier

identifier = SongIdentifier()
audio_folder = "path/to/audio/files"

for filename in os.listdir(audio_folder):
    if filename.endswith(('.mp3', '.wav')):
        filepath = os.path.join(audio_folder, filename)
        result = identifier.identify_song(filepath)
        
        if result and result.get('identified'):
            print(f"{filename} -> {result['title']} by {result['artist']}")
        else:
            print(f"{filename} -> Could not identify")
```

## Support & Resources

- **Documentation**: See README.md for full project documentation
- **API Reference**: https://audd.io/api
- **Spotify API**: https://developer.spotify.com/documentation/web-api
- **GitHub Issues**: Report bugs and request features

## License & Attribution

This feature uses:
- **AudD API** for song identification (https://audd.io/)
- **Spotify Web API** for metadata enrichment
- **librosa** for audio processing

Make sure to comply with the terms of service of each API you use.

---

**Enjoy discovering music with MelodySearch! 🎵**
