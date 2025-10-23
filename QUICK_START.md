# Quick Start Guide - Song Identification Feature

## 🚀 Get Started in 3 Minutes

### 1. Setup (First Time Only)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your credentials
nano .env  # or use your favorite editor
```

Add these to `.env`:
```bash
SECRET_KEY=your-random-secret-key-here
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
AUDD_API_KEY=your-audd-api-key  # Optional, free tier works without it
```

**Get Credentials:**
- Spotify: https://developer.spotify.com/dashboard
- AudD (optional): https://audd.io/

### 2. Install & Run

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start the server
python server.py
```

### 3. Identify a Song

**Option A: Web Interface**

1. Open http://127.0.0.1:5000
2. Scroll to "🔍 Identify Unknown Song"
3. Upload an audio file (MP3, WAV, etc.)
4. Click "🔍 Identify This Song"
5. View results!

**Option B: Command Line**

```bash
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@path/to/your/song.mp3"
```

**Option C: Python Code**

```python
from song_identifier import SongIdentifier

identifier = SongIdentifier()
result = identifier.identify_song("mysong.mp3")

if result and result.get('identified'):
    print(f"Song: {result['title']}")
    print(f"Artist: {result['artist']}")
    print(f"Album: {result['album']}")
    print(f"Cover: {result['cover_art']}")
```

## 📋 What You Get

Each identification returns:
- ✓ Song title
- ✓ Artist name
- ✓ Album name
- ✓ Album cover art (URL)
- ✓ Release date
- ✓ Genres
- ✓ Spotify link
- ✓ Record label
- ✓ Duration
- ✓ Popularity score

## 💡 Tips for Best Results

1. **Use Popular Songs First**: Test with well-known tracks
2. **Good Audio Quality**: Clear recordings work best
3. **15-30 Second Clips**: Optimal length for identification
4. **Include the Chorus**: Most recognizable part of the song
5. **Minimize Background Noise**: Clearer audio = better results

## ⚠️ Limitations

- **Free Tier**: 50 identifications per day (without API key)
- **Database**: Very obscure songs might not be identified
- **File Size**: Maximum 16MB
- **Formats**: MP3, WAV, FLAC, M4A, OGG only

## 🐛 Common Issues

### "Could not identify song"
- Try a different 15-30 second clip from the song
- Use better quality audio
- Check if it's a very obscure or unreleased track

### "Rate limit exceeded"
- Free tier: Wait 24 hours or get an API key
- With key: Upgrade to paid plan at https://audd.io/

### "Invalid file type"
- Convert to supported format: MP3, WAV, FLAC, M4A, or OGG

## 📚 More Documentation

- **User Guide**: See `SONG_IDENTIFICATION_GUIDE.md`
- **Testing**: See `TESTING_CHECKLIST.md`
- **Full Details**: See `FEATURE_SUMMARY.md`
- **Main Docs**: See `README.md`

## 🎯 Example Usage

```bash
# Example: Identify a song
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@blinding_lights.mp3"

# Response:
{
  "message": "Song identified successfully",
  "identified": true,
  "song": {
    "title": "Blinding Lights",
    "artist": "The Weeknd",
    "album": "After Hours",
    "cover_art": "https://i.scdn.co/image/...",
    "spotify_url": "https://open.spotify.com/track/...",
    ...
  }
}
```

## ✅ Verification

Test your setup:
```bash
# Run the test suite
python test_identification.py

# Should see: ✓ All module tests passed!
```

## 🔗 Quick Links

- Web Interface: http://127.0.0.1:5000
- API Endpoint: http://127.0.0.1:5000/identify
- Spotify Dashboard: https://developer.spotify.com/dashboard
- AudD Dashboard: https://audd.io/

---

**Ready to identify songs? Upload an audio file and discover what's playing! 🎵**
