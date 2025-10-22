# Song Identification Feature

MelodySearch now includes powerful song identification capabilities using acoustic fingerprinting technology - just like Shazam!

## Overview

The song identification feature allows you to identify songs in two ways:

### 🎤 Real-time Microphone Recording (NEW!)
- Record audio directly from your device's microphone
- Identify songs playing around you in real-time
- Works just like Shazam - press record, let it listen, and get instant results
- No file upload needed

### 📁 Audio File Upload
- Upload any audio file and get complete metadata about the song
- Supports: MP3, WAV, FLAC, M4A, OGG, WEBM

**Metadata Returned:**
- Title
- Artist
- Album
- Release date
- High-quality cover art
- ISRC code
- Genre tags
- Direct links to Spotify and MusicBrainz

## How It Works

### Microphone Recording Flow
1. **Capture Audio**: Records audio from your device's microphone using Web Audio API
2. **Audio Fingerprinting**: Generates a unique acoustic fingerprint from the recording
3. **Database Matching**: Compares the fingerprint against AcoustID's database of millions of songs
4. **Metadata Retrieval**: Fetches detailed information from MusicBrainz
5. **Spotify Enrichment**: Enhances metadata with Spotify data when available

### File Upload Flow
1. **Audio Fingerprinting**: Uses Chromaprint to generate a unique acoustic fingerprint from the audio file
2. **Database Matching**: Compares the fingerprint against AcoustID's database of millions of songs
3. **Metadata Retrieval**: Fetches detailed information from MusicBrainz
4. **Spotify Enrichment**: Enhances metadata with Spotify data when available

## Technology Stack

- **Chromaprint/fpcalc**: Open-source audio fingerprinting library
- **AcoustID**: Free acoustic fingerprint database with millions of songs
- **MusicBrainz**: Open music encyclopedia providing detailed metadata
- **Spotify API**: Additional metadata and high-quality cover art

## Setup Instructions

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libchromaprint-tools
```

**macOS:**
```bash
brew install chromaprint
```

**Windows:**
Download from https://acoustid.org/chromaprint

### 2. Install Python Dependencies

```bash
pip install pyacoustid musicbrainzngs
```

### 3. Get AcoustID API Key

1. Visit: https://acoustid.org/new-application
2. Fill in the form:
   - Name: MelodySearch (or your app name)
   - Version: 1.0
   - Email: your@email.com
3. Submit to receive your API key (instant and free)

### 4. Configure API Key

**Option A: Environment Variable**
```bash
export ACOUSTID_API_KEY='your-api-key-here'
```

**Option B: .env File**
```
ACOUSTID_API_KEY=your-api-key-here
```

## Usage

### Web Interface

#### Option A: Record from Microphone (Recommended - Like Shazam!)

1. Start the server:
   ```bash
   python server.py
   ```

2. Open http://127.0.0.1:5000

3. Scroll to the "Identify Unknown Song" section

4. Click "🎤 Record from Microphone"

5. Allow microphone access when your browser prompts

6. Play the song you want to identify near your device (or let it play from speakers/radio)

7. Record for 10-15 seconds for best results

8. Click "⏹️ Stop & Identify"

9. View results with cover art and metadata

**Tips for best results:**
- Record for at least 10 seconds
- Minimize background noise
- Hold your device close to the audio source
- Works great with music playing from speakers, radio, or other devices

#### Option B: Upload an Audio File

1. Start the server:
   ```bash
   python server.py
   ```

2. Open http://127.0.0.1:5000

3. Scroll to the "Identify Unknown Song" section

4. Upload an audio file (MP3, WAV, FLAC, M4A, OGG, WEBM)

5. Click "Identify Song"

6. View results with cover art and metadata

### API Endpoint

```bash
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@unknown_song.mp3"
```

**Response:**
```json
{
  "message": "Song identified successfully",
  "song": {
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "album": "A Night at the Opera",
    "cover_art_url": "https://...",
    "release_date": "1975-10-31",
    "identification_score": 0.95,
    "spotify_id": "4u7EnebtmKWzUH433cf5Qv",
    "spotify_url": "https://open.spotify.com/track/4u7EnebtmKWzUH433cf5Qv",
    "preview_url": "https://...",
    "popularity": 72,
    "isrc": "GBUM71505106",
    "tags": ["rock", "classic rock", "progressive rock"],
    "musicbrainz_url": "https://musicbrainz.org/recording/..."
  },
  "identification_source": "acoustid"
}
```

### Python Code

```python
from song_identifier import SongIdentifier

# Initialize with API key
identifier = SongIdentifier(acoustid_api_key='your-key')

# Identify a song
metadata = identifier.identify_song('path/to/audio.mp3')

if metadata:
    print(f"Song: {metadata['title']} by {metadata['artist']}")
    print(f"Album: {metadata['album']}")
    print(f"Confidence: {metadata['identification_score']:.1%}")
```

### With Spotify Fallback

```python
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())

# Identify with Spotify enrichment
metadata = identifier.identify_with_spotify_fallback('audio.mp3', sp)

# Now includes Spotify preview URL, popularity, etc.
print(f"Spotify URL: {metadata.get('spotify_url')}")
```

## Confidence Scores

Each identification includes a confidence score from 0 to 1:

- **0.8 - 1.0**: Very high confidence (excellent match)
- **0.6 - 0.8**: High confidence (good match)
- **0.4 - 0.6**: Medium confidence (possible match)
- **0.0 - 0.4**: Low confidence (uncertain match)

The UI displays confidence with color coding:
- Green: High confidence
- Yellow: Medium confidence
- Red: Low confidence

## Limitations

1. **Database Coverage**: Can only identify songs in the AcoustID database
   - Most commercial releases are covered
   - Very new or obscure tracks may not be identified

2. **Audio Quality**: Better audio quality improves identification accuracy
   - Clean recordings work best
   - Heavy background noise may reduce accuracy

3. **File Size**: Maximum upload size is 16MB

4. **Processing Time**: Typically 2-5 seconds per identification

5. **Rate Limits**: Free API has reasonable rate limits
   - Sufficient for personal use
   - Contact AcoustID for commercial applications

## Troubleshooting

### "Could not identify the song"

- **Solution 1**: Try a longer audio clip (at least 10-15 seconds)
- **Solution 2**: Use a cleaner audio source without background noise
- **Solution 3**: The song may not be in the AcoustID database

### "fpcalc not found"

- **Solution**: Install chromaprint system package
  ```bash
  # Ubuntu/Debian
  sudo apt-get install libchromaprint-tools
  
  # macOS
  brew install chromaprint
  ```

### "No AcoustID API key"

- **Solution**: Set the environment variable
  ```bash
  export ACOUSTID_API_KEY='your-api-key-here'
  ```

### Low confidence scores

- **Solution 1**: Use longer audio clips
- **Solution 2**: Improve audio quality
- **Solution 3**: Remove background noise

## Privacy & Data

- Audio files are processed locally and sent only to AcoustID for fingerprinting
- No audio is stored permanently
- Only acoustic fingerprints (not actual audio) are sent to AcoustID
- Temporary files are deleted immediately after processing

## Testing

Run the integration tests to verify setup:

```bash
python test_identification_integration.py
```

Run the basic setup test:

```bash
python test_song_identifier.py
```

## API Documentation

See the full API documentation in the main README.md file.

## Credits

- **AcoustID**: https://acoustid.org - Free acoustic fingerprinting service
- **MusicBrainz**: https://musicbrainz.org - Open music encyclopedia
- **Chromaprint**: https://acoustid.org/chromaprint - Audio fingerprinting library
- **Spotify**: https://spotify.com - Additional metadata and cover art

## License

This feature uses open-source libraries and free APIs:
- AcoustID: Free for non-commercial use
- MusicBrainz: CC0 license (public domain)
- Chromaprint: LGPL v2.1+

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the AcoustID documentation: https://acoustid.org/webservice
3. Open an issue on GitHub

---

Happy identifying! 🎵
