# What Tasks Can MelodySearch Do? 🎵

## Quick Answer
MelodySearch can identify unknown songs and find similar music using mathematical algorithms and audio fingerprinting. Here's what it can do:

## Main Tasks

### 1. 🔍 Identify Unknown Songs from Audio
- Upload any audio file to identify the song
- Get comprehensive metadata instantly
- Returns: title, artist, album, cover art, and more
- Uses audio fingerprinting technology (like Shazam)
- Free tier available (50 identifications/day)

**Example:** Upload a recording → Get "Blinding Lights by The Weeknd" with album art

### 2. 🔍 Search for Similar Songs by Name
- Search any song from Spotify's catalog
- Get 10 similar song recommendations
- See detailed similarity scores and explanations

**Example:** Search "Bohemian Rhapsody" → Get similar classic rock songs

### 3. 📤 Upload Your Own Audio Files for Similarity
- Upload MP3, WAV, FLAC, M4A, or OGG files
- Analyze the audio using real feature extraction
- Find similar songs in Spotify's catalog

**Example:** Upload your unreleased track → Find commercial songs with similar vibes

### 4. 🎼 Analyze Audio Features
Extract detailed musical characteristics:
- **Tempo** (BPM) - how fast the song is
- **Energy** - how intense/active it is
- **Mood/Valence** - how positive/happy it sounds
- **Danceability** - how easy to dance to
- **Key & Mode** - the musical key (C major, A minor, etc.)
- **Loudness** - volume level
- **Acousticness** - acoustic vs electronic
- **Instrumentalness** - has vocals or not
- **Speechiness** - how much talking/rapping
- **Liveness** - studio vs live recording

### 5. 🎭 Cross-Genre Discovery
- Find similar songs even across different genres
- Genre-aware matching (rock → alternative rock)
- Era-based discovery (classic, vintage, modern, current)

**Example:** Like "Lose Yourself" (hip-hop) → Also try "In The End" (rock) with high energy

### 6. 📊 Build a Music Database
- Save analyzed songs to local database
- Track your music collection
- Compare new songs against your library

### 7. 🧮 Mathematical Similarity Analysis
- Uses advanced algorithms for matching:
  - Cosine similarity for feature vectors
  - Genre semantic understanding
  - Weighted feature importance
  - Multi-dimensional comparison

### 8. 🌐 Web Interface + API
- **Web UI**: Easy-to-use browser interface
- **REST API**: Integrate into your own apps
- **Drag & Drop**: Upload files easily

## How to Use These Tasks

### Web Interface (Easiest)
```bash
python server.py
# Open http://127.0.0.1:5000
```

### Command Line
```bash
python main.py
# Follow the prompts
```

### API Calls
```bash
# Identify song
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@unknown_song.mp3"

# Search task
curl -X POST http://127.0.0.1:5000/search \
  -H "Content-Type: application/json" \
  -d '{"song_name": "Wonderwall"}'

# Upload task for similarity
curl -X POST http://127.0.0.1:5000/upload \
  -F "audio_file=@mysong.mp3"
```

## Real-World Use Cases

1. **Song Identification** (NEW!)
   - "What song is playing right now?"
   - Identify songs from recordings, videos, or live performances
   - Get complete information about unknown tracks

1. **Song Identification**
   - "What's this song playing on the radio?"
   - Identify background music in videos
   - Find song names from audio recordings
   
2. **Music Discovery** 
   - "I like this song, what else is similar?"
   - Find new artists with similar styles

3. **Playlist Creation**
   - Build cohesive playlists with similar vibes
   - Mix genres intelligently

4. **Music Production**
   - Upload your demo and find commercial references
   - Understand what your track sounds like

5. **DJ/Radio Programming**
   - Identify tracks you hear
   - Identify unknown tracks
   - Create smooth transitions between songs
   - Build themed sets

6. **Music Research**
   - Identify and catalog songs
   - Analyze musical trends over time
   - Study genre evolution
   - Catalog unknown recordings

7. **Personal Music Library**
   - Identify and organize your collection
   - Organize your collection by similarity
   - Identify and tag unknown files
   - Discover forgotten tracks in your library

## Task Limitations

- ⚠️ Requires Spotify API credentials (free registration, subject to rate limits)
- ⚠️ Song identification: Free tier limited to 50 requests/day (AudD API)
- ⚠️ Upload files limited to 16MB
- ⚠️ Analysis takes approximately 2-10 seconds depending on method
- ⚠️ Recommendations limited to songs in Spotify catalog
- ⚠️ Identification limited to songs in AudD database

## What MelodySearch CANNOT Do

- ❌ Play music (use Spotify for that)
- ❌ Download songs (copyright restrictions)
- ❌ Create playlists in your Spotify account
- ❌ Real-time streaming analysis
- ❌ Identify songs not in the AudD database (very obscure/unreleased tracks)

## Summary

**MelodySearch excels at:**
- Identifying unknown songs from audio (like Shazam)
- Finding similar songs mathematically
- Analyzing audio features in detail
- Cross-genre music discovery
- Working with both Spotify songs and your own files
- Providing detailed explanations of similarity
- Returning comprehensive metadata including album art

**Perfect for:** Music lovers, DJs, producers, researchers, playlist curators, radio programmers, and anyone who wants to identify songs or discover music in a smart way! 🎵✨
