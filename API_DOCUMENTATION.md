# MelodySearch API Documentation

## Overview

MelodySearch provides REST API endpoints for finding similar songs based on audio features and metadata analysis.

## Base URL

```
http://127.0.0.1:5000
```

## Authentication

Currently, the API uses session-based authentication. For production use, ensure proper authentication is configured via environment variables.

---

## Endpoints

### 1. Find Similar Songs (by Title and Artist)

**Endpoint:** `POST /similar-songs`

**Description:** Generate a list of songs similar to a given song (specified by title and artist). Returns comprehensive metadata for each similar song.

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "title": "Blinding Lights",
  "artist": "The Weeknd"
}
```

**Parameters:**
- `title` (string, required): The song title. Max 200 characters.
- `artist` (string, required): The artist name. Max 200 characters.

#### Response

**Success Response (200 OK):**
```json
{
  "original_song": {
    "title": "Blinding Lights",
    "artist": "The Weeknd",
    "spotify_id": "0VjIjW4GlUZAMYd2vXMi3b",
    "popularity": 95,
    "duration_ms": 200040,
    "explicit": false,
    "preview_url": "https://p.scdn.co/mp3-preview/...",
    "album": "After Hours",
    "release_date": "2020-03-20",
    "genres": ["canadian pop", "pop"],
    "audio_features": {
      "tempo": 171,
      "energy": 0.73,
      "valence": 0.33,
      "danceability": 0.51,
      "acousticness": 0.00,
      "instrumentalness": 0.00,
      "speechiness": 0.06,
      "liveness": 0.09,
      "loudness": -5.9,
      "key": 1,
      "mode": 1
    }
  },
  "similar_songs": [
    {
      "title": "Save Your Tears",
      "artist": "The Weeknd",
      "spotify_id": "5QO79kh1waicV47BqGRL3g",
      "popularity": 93,
      "duration_ms": 215627,
      "explicit": false,
      "preview_url": "https://p.scdn.co/mp3-preview/...",
      "album": "After Hours",
      "release_date": "2020-03-20",
      "genres": ["canadian pop", "pop"],
      "similarity_score": 0.89,
      "similarity_explanation": "Similar musical genres (match: 95%) • From similar time period (match: 100%)",
      "audio_features": {
        "tempo": 118,
        "energy": 0.83,
        "valence": 0.55,
        "danceability": 0.68,
        "acousticness": 0.02,
        "instrumentalness": 0.00,
        "speechiness": 0.03,
        "liveness": 0.13,
        "loudness": -4.8,
        "key": 8,
        "mode": 1
      }
    }
  ],
  "total_matches": 10,
  "analysis_method": "metadata_based"
}
```

**Error Responses:**

- `400 Bad Request`: Missing or invalid parameters
  ```json
  {
    "error": "Song title is required"
  }
  ```
  
- `404 Not Found`: Song not found on Spotify
  ```json
  {
    "error": "Song not found"
  }
  ```
  
- `403 Forbidden`: Spotify API error
  ```json
  {
    "error": "Spotify API error: <error message>"
  }
  ```

#### Example Usage

**cURL:**
```bash
curl -X POST http://127.0.0.1:5000/similar-songs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Blinding Lights",
    "artist": "The Weeknd"
  }'
```

**Python:**
```python
import requests

url = "http://127.0.0.1:5000/similar-songs"
data = {
    "title": "Blinding Lights",
    "artist": "The Weeknd"
}

response = requests.post(url, json=data)
result = response.json()

print(f"Original song: {result['original_song']['title']}")
print(f"Found {result['total_matches']} similar songs:")
for song in result['similar_songs']:
    print(f"  - {song['title']} by {song['artist']} (similarity: {song['similarity_score']:.2%})")
```

**JavaScript:**
```javascript
fetch('http://127.0.0.1:5000/similar-songs', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    title: 'Blinding Lights',
    artist: 'The Weeknd'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Original song:', data.original_song.title);
  console.log('Similar songs:', data.similar_songs);
});
```

---

### 2. Search Song (by Name Only)

**Endpoint:** `POST /search`

**Description:** Search for a song by name and get similar song recommendations. This endpoint is less precise than `/similar-songs` as it doesn't use the artist name.

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "song_name": "Bohemian Rhapsody"
}
```

**Parameters:**
- `song_name` (string, required): The song name to search for. Max 200 characters.

#### Response

Similar to `/similar-songs` but may return less accurate results since artist information is not provided.

---

### 3. Upload Audio File

**Endpoint:** `POST /upload`

**Description:** Upload an audio file for analysis and get similar song recommendations based on real audio feature extraction.

#### Request

**Headers:**
```
Content-Type: multipart/form-data
```

**Body:**
- `audio_file`: Audio file (MP3, WAV, FLAC, M4A, or OGG). Max 16MB.

#### Response

Returns similar songs based on real audio analysis of the uploaded file.

---

## Metadata Fields

### Song Metadata

All song objects include the following metadata fields:

- **title** (string): The song title
- **artist** (string): The primary artist name
- **spotify_id** (string): Spotify track ID
- **popularity** (integer, 0-100): Spotify popularity score
- **duration_ms** (integer): Song duration in milliseconds
- **explicit** (boolean): Whether the song contains explicit content
- **preview_url** (string|null): URL to 30-second preview audio (if available)
- **album** (string): Album name
- **release_date** (string): Release date (ISO format)
- **genres** (array): List of associated genres

### Audio Features

Each song includes estimated or extracted audio features:

- **tempo** (integer): Beats per minute (BPM)
- **key** (integer, 0-11): Musical key (0=C, 1=C#, 2=D, etc.)
- **mode** (integer, 0-1): Major (1) or Minor (0)
- **energy** (float, 0-1): Intensity and activity level
- **valence** (float, 0-1): Musical positivity/happiness
- **danceability** (float, 0-1): How suitable for dancing
- **acousticness** (float, 0-1): Amount of acoustic instruments
- **instrumentalness** (float, 0-1): Likelihood of no vocals
- **speechiness** (float, 0-1): Presence of spoken words
- **liveness** (float, 0-1): Probability of live performance
- **loudness** (float, -60 to 0): Overall loudness in decibels

### Similarity Scores

- **similarity_score** (float, 0-1): Overall similarity score (higher is more similar)
- **similarity_explanation** (string): Human-readable explanation of why songs are similar

---

## Input Validation

All endpoints validate input to prevent common security issues:

- Maximum length: 200 characters for text fields
- Prohibited characters: `<`, `>`, `"`, `\` (to prevent XSS attacks)
- Allowed characters: Letters, numbers, spaces, apostrophes, and most punctuation

---

## Rate Limiting

The API respects Spotify's rate limits. If you encounter rate limit errors, please wait a few seconds before retrying.

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Request successful
- **400 Bad Request**: Invalid input parameters
- **403 Forbidden**: Spotify API access denied
- **404 Not Found**: Song not found
- **500 Internal Server Error**: Server error

Error responses include a descriptive message:
```json
{
  "error": "Description of the error"
}
```

---

## Best Practices

1. **Use `/similar-songs` for best results**: When you know both the song title and artist, use the `/similar-songs` endpoint for more accurate results.

2. **Handle missing preview URLs**: Not all songs on Spotify have preview URLs. Check for null values.

3. **Cache results**: Similar song recommendations don't change frequently. Consider caching results to reduce API calls.

4. **Error handling**: Always implement proper error handling for network issues and API errors.

5. **Respect rate limits**: Don't make excessive requests in a short time period.

---

## Examples

### Find similar songs to "Bohemian Rhapsody" by Queen

```bash
curl -X POST http://127.0.0.1:5000/similar-songs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bohemian Rhapsody",
    "artist": "Queen"
  }'
```

### Find similar songs to "Shape of You" by Ed Sheeran

```bash
curl -X POST http://127.0.0.1:5000/similar-songs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Shape of You",
    "artist": "Ed Sheeran"
  }'
```

### Handle songs with apostrophes

```bash
curl -X POST http://127.0.0.1:5000/similar-songs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Don'\''t Stop Believin'\''",
    "artist": "Journey"
  }'
```

---

## Support

For issues or questions, please open an issue on the GitHub repository.
