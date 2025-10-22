# MelodySearch 🎵

**MelodySearch** is an intelligent music similarity search engine that helps you discover songs similar to your favorites using advanced mathematical audio analysis and metadata comparison.

## What Can MelodySearch Do? 🎯

### Core Capabilities

1. **Song Identification**
   - Identify any song from user-provided audio (like Shazam)
   - Upload audio files and get song metadata instantly
   - Returns title, artist, album, and cover art
   - Free tier available (50 identifications per day)
   - Automatic Spotify metadata enrichment

2. **Song Similarity Search**
   - Find songs similar to any track on Spotify
   - Discover music across genres using mathematical similarity algorithms
   - Get recommendations based on audio features and metadata

2. **Multiple Analysis Methods**
   - **Song Identification**: Uses audio fingerprinting to identify unknown songs
   - **Metadata-Based Analysis**: Uses genre, artist popularity, release year, tempo, and other metadata
   - **Audio Feature Analysis**: Extracts tempo, energy, valence, danceability, and spectral features
   - **Real Audio File Upload**: Analyze your own audio files (MP3, WAV, FLAC, M4A, OGG)

3. **Spotify Integration**
   - Search for any song in Spotify's catalog
   - Extract comprehensive song metadata
   - Access artist genres and popularity data
   - Get album information and release dates

4. **Audio File Upload & Analysis**
   - Upload your own audio files for analysis
   - Extract real audio features using librosa
   - Find similar tracks based on actual audio characteristics
   - Compare uploaded audio with Spotify catalog

5. **Advanced Feature Extraction**
   - **Tempo & Rhythm**: BPM detection, beat stability, rhythm patterns
   - **Tonal Features**: Key detection, mode, chroma analysis
   - **Energy & Dynamics**: RMS energy, spectral characteristics
   - **Mood & Valence**: Musical positivity/negativity estimation
   - **Danceability**: Beat strength and rhythmic regularity
   - **Acousticness**: Acoustic vs electronic content detection
   - **Instrumentalness**: Vocal vs instrumental balance
   - **Speechiness**: Spoken word detection (rap/hip-hop identification)
   - **Liveness**: Live performance vs studio recording detection
   - **Loudness**: Dynamic range analysis

6. **Cross-Genre Discovery**
   - Mathematical similarity matching that works across different genres
   - Genre-aware recommendations with style mixing
   - Era-based matching (classic, vintage, modern, current)

7. **Web Interface**
   - Clean, modern UI for song search
   - Visual display of song features and similarity scores
   - Drag-and-drop file upload support
   - Real-time search results

8. **Personal Library & Collections**
   - Save favorite songs and search results to your personal library
   - Create custom collections/playlists from saved songs
   - Organize music by mood, genre, or any criteria
   - Persistent storage of your music preferences

## Project Structure 📁

```
MelodySearch/
├── server.py                          # Flask web server with REST API
├── song_identifier.py                 # Song identification using audio fingerprinting
├── main.py                           # Command-line interface
├── feature_extraction.py             # Audio feature extraction using librosa
├── matcher.py                        # Similarity matching algorithms
├── metadata_similarity_engine.py     # Metadata-based similarity engine
├── song_db.py                        # Song database management
├── spotify_integration.py            # Spotify API integration
├── mp3_to_wav.py                     # Audio format conversion utilities
├── library_manager.py                # User library and collections management
├── templates/
│   └── index.html                    # Web UI
└── Data/                             # Song database storage
    └── library/                      # User library storage (personal)
```

## Installation & Setup 🚀

### Prerequisites
- Python 3.8+
- Spotify API credentials (Client ID and Client Secret)
- AudD API key (optional, for song identification - free tier available)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Tadiwa-M/MelodySearch.git
   cd MelodySearch
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API credentials**
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   - **Spotify API** (required): Get from https://developer.spotify.com/dashboard
   - **AudD API** (optional): Get free key from https://audd.io/ (50 requests/day)
   
   ```bash
   SPOTIFY_CLIENT_ID='your_spotify_client_id'
   SPOTIFY_CLIENT_SECRET='your_spotify_client_secret'
   AUDD_API_KEY='your_audd_api_key'  # Optional for song identification
   SECRET_KEY='generate_a_random_secret_key'
   ```

4. **Run the application**
   
   **Web Interface:**
   ```bash
   python server.py
   ```
   Then open http://127.0.0.1:5000 in your browser
   
   **Command Line:**
   ```bash
   python main.py
   ```

## Usage Examples 💡

### 1. Song Identification - Identify Unknown Songs

**Use Case:** You have an audio recording and want to know what song it is.

1. Start the server: `python server.py`
2. Open http://127.0.0.1:5000
3. Upload an audio file (MP3, WAV, FLAC, M4A, or OGG)
4. Get instant results with:
   - Song title
   - Artist name
   - Album name
   - Cover art
   - Release date
   - Spotify link
   - Additional metadata

**API Usage:**
```bash
curl -X POST http://127.0.0.1:5000/identify \
  -F "audio_file=@unknown_song.mp3"
```

**Response:**
```json
{
  "message": "Song identified successfully",
  "identified": true,
  "song": {
    "title": "Blinding Lights",
    "artist": "The Weeknd",
    "album": "After Hours",
    "cover_art": "https://i.scdn.co/image/...",
    "release_date": "2019-11-29",
    "spotify_url": "https://open.spotify.com/track/...",
    "genres": ["canadian pop", "pop"],
    ...
  }
}
```

### 2. Web Interface - Search by Song Name

1. Start the server: `python server.py`
2. Open http://127.0.0.1:5000
3. Enter a song name (e.g., "Blinding Lights")
4. Click "Search"
5. View similar songs with similarity scores and explanations
6. Click "Save" on any recommendation to add it to your library

### 3. Web Interface - Upload Audio File for Similarity

1. Click the upload area or drag & drop an audio file
2. Supported formats: MP3, WAV, FLAC, M4A, OGG
3. Wait for analysis (uses real audio feature extraction)
4. View recommendations based on your uploaded audio

### 4. Command Line Interface

```bash
python main.py
```

Follow the prompts:
- Enter path to WAV file
- Enter song title
- View top 10 recommendations with similarity scores

### 4. Personal Library Management

1. **Save Songs**: Click the "Save" button on any search result or recommendation
2. **View Library**: Switch to the "My Library" tab to see all saved songs
3. **Create Collections**: 
   - Go to the "Collections" tab
   - Click "New Collection"
   - Give it a name and optional description
4. **Organize Songs**: Add saved songs to collections from your library
5. **Manage Collections**: View, edit, or delete collections as needed

### 5. API Endpoints

#### Identify a song from audio
```bash
POST /identify
Content-Type: multipart/form-data

audio_file: <your audio file>
```

#### Find similar songs (by title and artist) - RECOMMENDED
```bash
POST /similar-songs
Content-Type: application/json

{
  "title": "Blinding Lights",
  "artist": "The Weeknd"
}
```

**Response:**
```json
{
  "original_song": {
    "title": "Blinding Lights",
    "artist": "The Weeknd",
    "spotify_id": "0VjIjW4GlUZAMYd2vXMi3b",
    "popularity": 95,
    "genres": ["canadian pop", "pop"],
    "audio_features": {...}
  },
  "similar_songs": [
    {
      "title": "Save Your Tears",
      "artist": "The Weeknd",
      "similarity_score": 0.89,
      "similarity_explanation": "Similar musical genres (match: 95%)",
      "audio_features": {...}
    }
  ],
  "total_matches": 10
}
```

#### Search for a song and get recommendations (by name only)
```bash
POST /search
Content-Type: application/json

{
  "song_name": "Bohemian Rhapsody"
}
```

#### Upload and analyze audio file for similarity
```bash
POST /upload
Content-Type: multipart/form-data

audio_file: <your audio file>
```

#### Library Management
```bash
# Add song to library
POST /library/songs
Content-Type: application/json
{ "title": "Song Name", "artist": "Artist Name", ... }

# Get all library songs
GET /library/songs

# Remove song from library
DELETE /library/songs/{song_id}

# Create collection
POST /library/collections
Content-Type: application/json
{ "name": "My Playlist", "description": "Optional description" }

# Get all collections
GET /library/collections

# Get collection with songs
GET /library/collections/{collection_id}

# Add song to collection
POST /library/collections/{collection_id}/songs
Content-Type: application/json
{ "song_id": "song_id_from_library" }

# Remove song from collection
DELETE /library/collections/{collection_id}/songs/{song_id}

# Delete collection
DELETE /library/collections/{collection_id}

# Get library statistics
GET /library/stats
```

**For complete API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md)**

## Technical Details 🔧

### Similarity Algorithm

MelodySearch uses a hybrid similarity approach:

1. **Metadata Similarity** (Primary Method)
   - Genre matching with semantic understanding
   - Era and release year proximity
   - Artist popularity and mainstream level
   - Duration and song structure similarity
   - Explicit content matching

2. **Audio Feature Similarity** (Real Audio Analysis)
   - Multi-dimensional feature vector comparison
   - Weighted importance for different features:
     - Tempo (normalized to 0-1 range)
     - Energy, Valence, Danceability (0-1 scale)
     - Acousticness, Instrumentalness (0-1 scale)
     - Speechiness, Liveness (0-1 scale)
     - Loudness (normalized decibel scale)
   - Cosine similarity for vector comparison

3. **Mathematical Matching**
   - Euclidean distance for feature vectors
   - Weighted scoring based on feature importance
   - Cross-genre normalization

### Genre Understanding

The system includes comprehensive genre mappings for:
- Electronic genres (EDM, House, Techno, Dubstep, etc.)
- Hip-Hop/Rap (including Trap, Drill, Grime)
- Rock genres (Alternative, Indie, Punk, Metal)
- Pop variants (Dance Pop, K-Pop, Synthpop)
- Acoustic genres (Folk, Country, Acoustic)
- Jazz and Blues styles
- Classical and Orchestral
- R&B, Soul, and Funk
- And many more...

### Feature Extraction Pipeline

**For Spotify Songs:**
1. Extract comprehensive metadata (genres, popularity, release info)
2. Analyze artist characteristics
3. Estimate audio features from metadata patterns
4. Create similarity vectors

**For Uploaded Audio:**
1. Load audio file with librosa
2. Extract tempo using beat tracking
3. Analyze chroma for key detection
4. Calculate RMS energy for dynamics
5. Compute spectral features (centroid, contrast)
6. Estimate danceability, valence, and mood
7. Create feature vector for matching

## Dependencies 📦

- **Flask**: Web server framework
- **spotipy**: Spotify API client
- **librosa**: Audio analysis library
- **numpy**: Numerical computations
- **scikit-learn**: Machine learning utilities (similarity metrics)
- **soundfile**: Audio file I/O
- **scipy**: Scientific computing
- **requests**: HTTP library for API calls (also used for AudD API)

See `requirements.txt` for exact versions.

### External APIs

- **Spotify API**: For metadata, search, and recommendations (required)
- **AudD API**: For song identification (optional, free tier: 50 requests/day)

## Features in Detail 🎼

### Audio Features Explained

- **Tempo**: Speed of the song in BPM (beats per minute)
- **Key**: Musical key (0-11 representing C, C#, D, etc.)
- **Mode**: Major (1) or Minor (0)
- **Energy**: Intensity and activity level (0.0 to 1.0)
- **Valence**: Musical positivity/happiness (0.0 to 1.0)
- **Danceability**: How suitable for dancing (0.0 to 1.0)
- **Acousticness**: Amount of acoustic instruments (0.0 to 1.0)
- **Instrumentalness**: Likelihood of no vocals (0.0 to 1.0)
- **Speechiness**: Presence of spoken words (0.0 to 1.0)
- **Liveness**: Probability of live performance (0.0 to 1.0)
- **Loudness**: Overall loudness in decibels (typically -60 to 0 dB)

### Metadata Features

- **Artist Genres**: Up to multiple genres per artist
- **Release Year**: Album/single release date
- **Popularity**: Spotify popularity score (0-100)
- **Mainstream Level**: underground, mid_tier, or mainstream
- **Era Classification**: classic (<1980), vintage (1980-2000), modern (2000-2015), current (>2015)
- **Duration Category**: short (<3 min), medium, or long (>5 min)

## API Response Format 📊

### Search Response
```json
{
  "message": "Song analyzed successfully",
  "original_song": {
    "title": "Song Name",
    "artist": "Artist Name",
    "audio_features": { ... },
    "spotify_metadata": { ... }
  },
  "spotify_recommendations": [
    {
      "title": "Similar Song 1",
      "artist": "Artist Name",
      "similarity_score": 0.87,
      "explanation": "Strong genre match...",
      "feature_breakdown": { ... },
      "spotify_id": "...",
      "preview_url": "..."
    }
  ],
  "analysis_stats": {
    "analysis_method": "metadata_based",
    "candidates_found": 50,
    "metadata_matches": 10
  }
}
```

## Database 💾

Songs are stored in JSON format in the `Data/` directory:
- **Song Database** (`Data/song_db.json`): Each analyzed song is saved for future comparisons
- **Personal Library** (`Data/library/library_songs.json`): Your saved/liked songs
- **Collections** (`Data/library/collections.json`): Your custom playlists
- All data includes extracted features and metadata
- Enables building a local music library over time
- Library data is excluded from git (personal data)

## Performance Considerations ⚡

- **Search Time**: ~2-5 seconds for metadata-based search
- **Upload Analysis**: ~5-10 seconds for real audio analysis
- **Candidate Discovery**: Searches 50+ potential matches
- **Recommendation Generation**: Returns top 10 most similar songs
- **Rate Limiting**: Respects Spotify API rate limits

## Known Limitations ⚠️

1. **Audio Analysis**: Real audio analysis requires librosa and is CPU-intensive
2. **Spotify API**: Some features depend on Spotify's data availability
3. **Preview URLs**: Not all Spotify tracks have preview URLs
4. **Genre Coverage**: Genre mappings are comprehensive but not exhaustive
5. **File Size**: Upload limited to 16MB for performance

## Recent Features ✨

**Library & Collections System**
- Save favorite songs and search results
- Create custom collections/playlists
- Organize music by any criteria
- Persistent personal library storage
- Easy song and collection management

## Future Enhancements 🚀

Potential improvements and features:
- Multi-track playlist similarity analysis
- User preference learning and personalized recommendations
- Smart playlists based on mood/activity
- More audio file formats support
- Offline mode with pre-downloaded features
- Advanced filtering (by year, genre, mood)
- Collaborative filtering recommendations
- Integration with more music APIs (Last.fm, Apple Music)
- Export/import library and collections

## Contributing 🤝

Contributions are welcome! Areas for improvement:
- Additional genre classifications
- Enhanced audio feature extraction
- UI/UX improvements
- Performance optimizations
- Additional music service integrations

## License 📄

See the repository for license information.

## Credits 👏

Built with:
- Spotify Web API
- librosa audio analysis library
- Flask web framework
- scikit-learn for similarity metrics

---

**MelodySearch** - Discover music mathematically 🎵✨
