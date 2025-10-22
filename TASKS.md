# What Tasks Can MelodySearch Do? 🎵

## Quick Answer
MelodySearch can analyze music and find similar songs using mathematical algorithms. Here's what it can do:

## Main Tasks

### 1. 🔍 Search for Similar Songs by Name
- Search any song from Spotify's catalog
- Get 10 similar song recommendations
- See detailed similarity scores and explanations

**Example:** Search "Bohemian Rhapsody" → Get similar classic rock songs

### 2. 📤 Upload Your Own Audio Files
- Upload MP3, WAV, FLAC, M4A, or OGG files
- Analyze the audio using real feature extraction
- Find similar songs in Spotify's catalog

**Example:** Upload your unreleased track → Find commercial songs with similar vibes

### 3. 🎼 Analyze Audio Features
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

### 4. 🎭 Cross-Genre Discovery
- Find similar songs even across different genres
- Genre-aware matching (rock → alternative rock)
- Era-based discovery (classic, vintage, modern, current)

**Example:** Like "Lose Yourself" (hip-hop) → Also try "In The End" (rock) with high energy

### 5. 📊 Build a Music Database
- Save analyzed songs to local database
- Track your music collection
- Compare new songs against your library

### 8. 💾 Personal Library Management
- Save favorite songs from search results
- Build your personal music library
- Quick access to your liked songs
- Track when songs were added

### 9. 📚 Create Custom Collections
- Organize songs into playlists/collections
- Name and describe your collections
- Add/remove songs from collections
- Manage multiple collections (Workout, Chill, Party, etc.)

### 6. 🧮 Mathematical Similarity Analysis
- Uses advanced algorithms for matching:
  - Cosine similarity for feature vectors
  - Genre semantic understanding
  - Weighted feature importance
  - Multi-dimensional comparison

### 7. 🌐 Web Interface + API
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
# Search task
curl -X POST http://127.0.0.1:5000/search \
  -H "Content-Type: application/json" \
  -d '{"song_name": "Wonderwall"}'

# Upload task
curl -X POST http://127.0.0.1:5000/upload \
  -F "audio_file=@mysong.mp3"
```

## Real-World Use Cases

1. **Music Discovery** 
   - "I like this song, what else is similar?"
   - Find new artists with similar styles
   - Save discoveries to your library for later

2. **Playlist Creation**
   - Build cohesive playlists with similar vibes
   - Create collections for different moods
   - Mix genres intelligently
   - Organize with custom collections

3. **Music Production**
   - Upload your demo and find commercial references
   - Understand what your track sounds like
   - Save reference tracks to collections

4. **DJ/Radio Programming**
   - Create smooth transitions between songs
   - Build themed sets using collections
   - Save successful combinations for future gigs

5. **Music Research**
   - Analyze musical trends over time
   - Study genre evolution
   - Build collections of examples by era/style

6. **Personal Music Library**
   - Organize your collection by similarity
   - Discover forgotten tracks in your library
   - Create collections for workouts, studying, parties, etc.
   - Keep track of songs you want to explore later

## Task Limitations

- ⚠️ Requires Spotify API credentials (free registration, subject to rate limits)
- ⚠️ Upload files limited to 16MB
- ⚠️ Analysis takes approximately 2-10 seconds depending on method
- ⚠️ Recommendations limited to songs in Spotify catalog

## What MelodySearch CANNOT Do

- ❌ Play music (use Spotify for that)
- ❌ Download songs (copyright restrictions)
- ❌ Identify unknown songs (use Shazam instead)
- ❌ Create playlists in your Spotify account
- ❌ Real-time streaming analysis

## Summary

**MelodySearch excels at:**
- Finding similar songs mathematically
- Analyzing audio features in detail
- Cross-genre music discovery
- Working with both Spotify songs and your own files
- Providing detailed explanations of similarity

**Perfect for:** Music lovers, DJs, producers, researchers, playlist curators, and anyone who wants to discover music in a smart way! 🎵✨
