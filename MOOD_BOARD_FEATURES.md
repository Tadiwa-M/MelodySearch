# 🎨 Advanced Mood Board Features

Complete guide to all the powerful features added to the MelodySearch mood board system.

---

## ✨ Feature Overview

### 1. **Multi-Source Image Integration**
Mix images from three different providers for maximum variety and quality.

**Supported Sources:**
- **Unsplash** - Professional photography, high quality
- **Pexels** - Free stock photos, diverse subjects
- **Pixabay** - Large library, commercial-free images

**How it works:**
- Automatically mixes images from all configured sources
- Falls back gracefully if a source is unavailable
- Shuffles results for natural variety
- Proper attribution for all sources

---

### 2. **Custom Search**
Search for any aesthetic or vibe you want, independent of your listening history.

**Endpoint:** `POST /mood-board/custom-search`

**Request:**
```json
{
  "query": "dark moody aesthetic",
  "count": 15,
  "sources": ["unsplash", "pexels", "pixabay"]
}
```

**Response:**
```json
{
  "success": true,
  "images": [...],
  "query": "dark moody aesthetic",
  "count": 15,
  "sources_used": ["unsplash", "pexels", "pixabay"]
}
```

**Use Cases:**
- "cyberpunk aesthetic"
- "cottagecore vibes"
- "vintage 80s"
- "minimalist modern"
- "neon lights city"

---

### 3. **Save Mood Boards**
Persist your favorite mood boards to the database.

**Endpoint:** `POST /mood-board/save`

**Request:**
```json
{
  "name": "My Summer Vibes 2024",
  "images": [...],
  "tracks": [...]
}
```

**Response:**
```json
{
  "success": true,
  "board_id": "a3f8d9e2c1b0",
  "share_url": "http://localhost:5000/shared/mood-board/a3f8d9e2c1b0",
  "message": "Mood board saved successfully"
}
```

**Features:**
- Automatic ID generation
- Timestamp tracking (created_at, updated_at)
- Custom board names
- Links to original tracks

---

### 4. **Share Mood Boards**
Generate shareable links for your mood boards.

**Share URL Format:**
```
http://your-domain.com/shared/mood-board/{board_id}
```

**Public Access:**
- Anyone with the link can view
- No authentication required
- Beautiful read-only view
- Shows images in Pinterest masonry layout

---

### 5. **My Boards Collection**
View all your saved mood boards in one place.

**Endpoint:** `GET /mood-board/my-boards`

**Response:**
```json
{
  "success": true,
  "boards": [
    {
      "id": "a3f8d9e2c1b0",
      "name": "My Summer Vibes 2024",
      "image_count": 15,
      "created_at": "2024-12-19T10:30:00",
      "preview_image": {...}
    }
  ],
  "count": 1
}
```

---

## 🛠️ Setup Instructions

### API Keys Required

#### Unsplash (Required)
1. Visit: https://unsplash.com/developers
2. Create account and new application
3. Copy "Access Key"
4. Add to `.env`: `UNSPLASH_ACCESS_KEY=your-key`

#### Pexels (Optional)
1. Visit: https://www.pexels.com/api/
2. Create account
3. Copy API key
4. Add to `.env`: `PEXELS_API_KEY=your-key`

#### Pixabay (Optional)
1. Visit: https://pixabay.com/api/docs/
2. Create account
3. Copy API key
4. Add to `.env`: `PIXABAY_API_KEY=your-key`

**Note:** The more sources you configure, the more diverse your mood boards will be!

---

## 📊 API Reference

### Get Mood Board (Automatic)
```
GET /mood-board
```
Generates mood board from your recent Spotify listening history.

### Custom Search
```
POST /mood-board/custom-search
Body: { query, count, sources }
```
Search by any custom keyword.

### Save Board
```
POST /mood-board/save
Body: { name, images, tracks }
Auth: Required
```
Save current mood board to database.

### Get My Boards
```
GET /mood-board/my-boards
Auth: Required
```
Get all your saved boards.

### Load Specific Board
```
GET /mood-board/{board_id}
Auth: Optional (public if shared)
```
Load a specific saved board.

### Delete Board
```
DELETE /mood-board/{board_id}
Auth: Required (must be owner)
```
Delete a saved board.

### View Shared Board
```
GET /shared/mood-board/{board_id}
Public access
```
Public view of shared mood board.

---

## 🎯 Usage Examples

### Frontend Implementation

#### Custom Search
```javascript
async function searchCustomMoodBoard(query) {
    const response = await fetch('/mood-board/custom-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query,
            count: 15,
            sources: ['unsplash', 'pexels']
        })
    });
    const data = await response.json();
    displayImages(data.images);
}
```

#### Save Board
```javascript
async function saveMoodBoard(images, tracks, name) {
    const response = await fetch('/mood-board/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            images: images,
            tracks: tracks
        })
    });
    const data = await response.json();
    copyToClipboard(data.share_url);
}
```

#### Load My Boards
```javascript
async function loadMyBoards() {
    const response = await fetch('/mood-board/my-boards');
    const data = await response.json();
    displayBoardGallery(data.boards);
}
```

---

## 📁 File Structure

```
MelodySearch/
├── image_service.py          # Multi-source image fetching
├── mood_board_manager.py     # Database persistence & sharing
├── server.py                 # API endpoints
├── Data/
│   └── mood_boards/          # Saved boards (JSON files)
│       ├── a3f8d9e2c1b0.json
│       └── b4e9f1a3d2c8.json
└── templates/
    ├── index.html            # Main app (with masonry layout)
    └── shared_mood_board.html # Shared board view
```

---

## 🎨 Source Attribution

All image sources require proper attribution:

**Unsplash:**
```html
Photo by <a href="{url}?utm_source=MelodySearch&utm_medium=referral">
    {photographer}
</a>
```

**Pexels:**
```html
Photo by <a href="{url}?utm_source=MelodySearch&utm_medium=referral">
    {photographer}
</a>
```

**Pixabay:**
```html
Photo by <a href="{url}?utm_source=MelodySearch&utm_medium=referral">
    {photographer}
</a>
```

Our implementation handles this automatically!

---

## 🔒 Security & Privacy

- **Authentication:** Required for saving/deleting boards
- **Authorization:** Users can only delete their own boards
- **Public Sharing:** Shared boards are publicly accessible via unique ID
- **Data Storage:** Boards saved as JSON files in `Data/mood_boards/`
- **User Privacy:** User IDs from Spotify are never exposed in shares

---

## 🚀 Performance

- **Caching:** Consider adding Redis for frequently accessed boards
- **Rate Limits:**
  - Unsplash: 50/hour (demo), 5000/hour (production)
  - Pexels: 200/hour (free)
  - Pixabay: 5000/day (free)
- **Optimization:** Images are lazy-loaded in the UI
- **Fallback:** Always falls back to Spotify images if APIs fail

---

## 🔮 Future Enhancements

### Planned Features:
1. **Pinterest API Integration** - When approved, add as 4th source
2. **AI Mood Detection** - Analyze audio features to determine aesthetic keywords
3. **Collaborative Boards** - Share editing access with friends
4. **Export Options** - Download boards as PDF or image collage
5. **Board Templates** - Pre-made aesthetic themes
6. **Social Features** - Like, comment, remix other users' boards
7. **Spotify Integration** - Create playlists from board's related tracks

### Technical Improvements:
- Add Redis caching for better performance
- Implement pagination for large collections
- Add image CDN support
- Create admin dashboard for board moderation
- Add analytics (most popular aesthetics, top boards, etc.)

---

## 📞 Support

### Troubleshooting

**No images loading?**
- Check API keys in `.env` file
- Verify you haven't exceeded rate limits
- Check server logs for errors

**Save button not working?**
- Ensure you're logged in with Spotify
- Check browser console for errors
- Verify `Data/mood_boards/` directory exists

**Shared link not working?**
- Check that board ID is correct
- Ensure board file exists in database
- Verify server is running

---

## 📄 License

Images are sourced from:
- **Unsplash:** Free to use under Unsplash License
- **Pexels:** Free to use under Pexels License
- **Pixabay:** Free to use under Pixabay License

Always provide proper attribution as required by each service!

---

**Happy Mood Boarding!** 🎨✨
