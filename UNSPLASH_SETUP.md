# Unsplash Mood Board Integration Guide

## Overview

MelodySearch now features a beautiful Pinterest-style mood board powered by Unsplash's aesthetic photography. The mood board displays creatively shot images based on your Spotify listening history, with automatic fallback to Spotify album art if Unsplash is unavailable.

## Features

✨ **Pinterest-Style Masonry Layout**
- Responsive column-based grid (4 columns on desktop, 2-3 on tablet, 2 on mobile)
- Varying image heights for authentic Pinterest feel
- Smooth hover animations and transitions
- Beautiful overlays with image information

🎨 **Aesthetic Image Search**
- Searches Unsplash based on:
  - Artist names + "aesthetic"
  - Music genres + "vibes"
  - Track names + "mood"
  - General music aesthetics
- High-quality, professionally shot photography
- Attribution to photographers (required by Unsplash API guidelines)

💾 **Save to Collections**
- Pin button on each image (hover to reveal)
- Save images to mood board collections
- Visual feedback when saving

🔄 **Automatic Fallback**
- If Unsplash API is unavailable, automatically falls back to Spotify album art
- Graceful error handling
- Source indicator ("✨ Powered by Unsplash" or "🎵 From Spotify")

---

## Setup Instructions

### 1. Create Unsplash Developer Account

1. Go to [https://unsplash.com/developers](https://unsplash.com/developers)
2. Click "Register as a developer"
3. Sign up or log in with your Unsplash account
4. Accept the API Guidelines and Terms

### 2. Create a New Application

1. Go to [https://unsplash.com/oauth/applications](https://unsplash.com/oauth/applications)
2. Click "New Application"
3. Fill in the application details:
   - **Application name**: `MelodySearch` (or your preferred name)
   - **Description**: "Music mood board generator for Spotify"
   - Check all the guidelines checkboxes
4. Click "Create application"

### 3. Get Your Access Key

1. Once created, you'll see your application page
2. Find the **"Access Key"** (this is different from the Secret Key)
3. Copy the Access Key - it should look like: `abc123xyz...`

### 4. Add to Your .env File

1. Open or create your `.env` file in the project root
2. Add the following line:
   ```
   UNSPLASH_ACCESS_KEY=your-access-key-here
   ```
3. Replace `your-access-key-here` with the actual Access Key you copied

Example `.env` file:
```env
SECRET_KEY=your-secret-key
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
UNSPLASH_ACCESS_KEY=abc123xyz456...
FLASK_ENV=development
PORT=5000
```

### 5. Restart Your Server

```bash
python server.py
```

---

## Rate Limits

**Demo/Development:**
- 50 requests per hour

**Production (after applying):**
- 5,000 requests per hour
- To upgrade, go to your app settings on Unsplash and apply for production access
- You'll need to show them your app in action

---

## How It Works

### Backend (`image_service.py`)

The `ImageService` class handles:
1. **Search** - Queries Unsplash API with music-related keywords
2. **Keyword Generation** - Creates aesthetic search terms from track metadata
3. **Download Tracking** - Triggers Unsplash download endpoint (required for compliance)
4. **Fallback Logic** - Returns empty array if API fails, triggering Spotify fallback

### Frontend (`templates/index.html`)

The mood board displays with:
1. **Masonry Grid** - CSS column-based layout for Pinterest effect
2. **Lazy Loading** - Images load as you scroll
3. **Hover Interactions** - Reveal photographer credits and save button
4. **Responsive Design** - Adapts to all screen sizes

### API Endpoint (`/mood-board`)

1. Fetches recently played tracks from Spotify
2. Extracts artist names and genres
3. Attempts to fetch Unsplash images
4. Falls back to Spotify album art if Unsplash fails
5. Returns images with source indicator

---

## Testing Without Unsplash

The mood board works without Unsplash! If you don't set up the API key:
- It will automatically use Spotify album artwork
- All features still work
- The source indicator will show "🎵 From Spotify"

This makes it easy to develop and test before setting up Unsplash.

---

## Upgrading to Pinterest API

If you later get Pinterest API access, the architecture supports easy switching:

1. The `image_service.py` module is provider-agnostic
2. Add a `PinterestService` class similar to the Unsplash implementation
3. Modify the `/mood-board` endpoint to try Pinterest first, then Unsplash, then Spotify
4. Update environment variables in `.env.example`

---

## Troubleshooting

### Images not loading?
- Check that `UNSPLASH_ACCESS_KEY` is set in your `.env` file
- Verify the key is correct (copy-paste from Unsplash dashboard)
- Check server logs for API errors
- Ensure you haven't exceeded rate limits (50/hour for demo)

### Only seeing Spotify images?
- This means Unsplash API isn't working (check key)
- Or you've hit rate limits
- Check browser console and server logs for errors

### Rate limit exceeded?
- Demo accounts: 50 requests/hour
- Wait an hour or apply for production access (5000/hour)
- Server automatically falls back to Spotify

---

## API Compliance

Unsplash requires:
- ✅ Photographer attribution (we display this on hover)
- ✅ Triggering download endpoint when images are shown (automated)
- ✅ Linking to photographer's Unsplash profile (clickable credit)
- ✅ UTM parameters in links (added automatically)

Our implementation handles all of this automatically!

---

## Next Steps

Want to enhance the mood board further?

1. **Save Collections** - Implement backend persistence for saved images
2. **Share Boards** - Generate shareable links to mood boards
3. **Custom Searches** - Let users manually search for specific aesthetics
4. **AI Mood Detection** - Analyze audio features to determine mood keywords
5. **Mix Sources** - Combine Unsplash, Pexels, and Pixabay for more variety

---

## Resources

- [Unsplash API Documentation](https://unsplash.com/documentation)
- [Unsplash Developer Guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines)
- [Pinterest API (for future upgrade)](https://developers.pinterest.com/docs/api/v5/)

---

Happy mood boarding! 🎨✨
