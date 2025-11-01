# Melody Search 🎵

A full-stack music discovery web application with Spotify integration that helps users find and explore music based on their preferences.

🔗 **[Live Demo](https://melodysearch.onrender.com)**

## Features

- 🔍 Real-time music search powered by Spotify API
- 📚 Personal music library management
- 🎨 Collection organization
- 🎵 Playlist generation
- 🔐 Secure Spotify authentication

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **API:** Spotify Web API
- **Deployment:** Render
- **Authentication:** OAuth 2.0

## Screenshots

<img width="1562" height="968" alt="image" src="https://github.com/user-attachments/assets/97f2617a-acb5-423a-977f-217245152cd3" />

<img width="1867" height="877" alt="image" src="https://github.com/user-attachments/assets/97264dcb-ab0b-42cb-83ef-465fbfe47b2f" />



## Setup

1. Clone the repository
```bash
git clone https://github.com/Tadiwa-M/MelodySearch.git
cd MelodySearch
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up Spotify API credentials
- Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Create a new app
- Copy Client ID and Client Secret
- Create `.env` file:
```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
```

5. Run the application
```bash
python app.py
```

6. Open browser to `http://localhost:5000`

## Future Enhancements

- Social features (see friends' playlists)
- Shazam-like song identification
- Enhanced recommendation algorithm
- Mobile app version

## Author

**Tadiwanashe Matara**
- Computer Science Student at Maastricht University
- [GitHub](https://github.com/Tadiwa-M)

## License

MIT License
