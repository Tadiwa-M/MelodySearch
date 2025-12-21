# Spotify OAuth Setup Guide

MelodySearch requires Spotify API credentials to access your listening history and provide personalized music recommendations. Follow these steps to set up Spotify authentication.

## 🚀 Quick Setup

### Step 1: Create a Spotify Developer Account

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account (or create one if you don't have it)
3. Accept the Terms of Service

### Step 2: Create a New App

1. Click **"Create app"** button
2. Fill in the app details:
   - **App name**: `MelodySearch` (or any name you prefer)
   - **App description**: `Personal music discovery and mood board app`
   - **Redirect URI**: `http://127.0.0.1:5000/callback`
     - **IMPORTANT**: This must match exactly, including the port number
     - If your app runs on a different port, update this accordingly
   - **APIs used**: Select **Web API**
3. Click **"Save"**

### Step 3: Get Your Credentials

1. After creating the app, you'll see your app's dashboard
2. Click **"Settings"** button (top right)
3. You'll see:
   - **Client ID**: A long string like `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
   - **Client Secret**: Click **"View client secret"** to reveal it
4. Copy both of these values

### Step 4: Configure Your .env File

1. Open the `.env` file in the MelodySearch root directory
2. Replace the placeholder values with your actual credentials:

```env
# Spotify API Credentials
SPOTIFY_CLIENT_ID=your-actual-client-id-here
SPOTIFY_CLIENT_SECRET=your-actual-client-secret-here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback

# Generate a random secret key for Flask sessions
SECRET_KEY=your-random-secret-key-here
```

3. To generate a secure `SECRET_KEY`, run:
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Step 5: Test the Connection

1. Start your MelodySearch server:
```bash
python3 server.py
```

2. Open your browser and go to: `http://127.0.0.1:5000`

3. Click the **"Connect Spotify"** button in the top right

4. You'll be redirected to Spotify's login page:
   - Log in with your Spotify account
   - Grant permissions to MelodySearch
   - You'll be redirected back to MelodySearch

5. If successful, you'll see **"Logged in as [Your Name]"** in the header

## 🔧 Troubleshooting

### "Redirect URI mismatch" Error

**Problem**: After clicking "Connect Spotify", you see an error about redirect URI mismatch.

**Solution**:
1. Go back to your [Spotify App Settings](https://developer.spotify.com/dashboard)
2. Click on your app → Settings
3. Under "Redirect URIs", ensure you have **exactly**: `http://127.0.0.1:5000/callback`
4. If you're running on a different port, update both:
   - Spotify Dashboard redirect URI
   - `.env` file `SPOTIFY_REDIRECT_URI`

### Login Button Does Nothing / Page Just Refreshes

**Problem**: Clicking "Connect Spotify" refreshes the page but doesn't redirect to Spotify.

**Causes**:
1. **Missing credentials in .env**: Make sure you replaced `your-spotify-client-id` and `your-spotify-client-secret` with actual values
2. **Server not running**: Ensure `python3 server.py` is running in the terminal
3. **Invalid credentials**: Double-check you copied the Client ID and Secret correctly from Spotify Dashboard

**Solution**:
1. Stop the server (Ctrl+C)
2. Verify your `.env` file has real credentials (not placeholders)
3. Restart the server: `python3 server.py`
4. Try clicking "Connect Spotify" again

### Friend Can't Connect on Their Device

**Problem**: The app works for you but your friend can't connect Spotify on their device.

**Causes**:
1. **Different URL**: They're accessing the app from a different URL (e.g., your local IP address instead of 127.0.0.1)
2. **Redirect URI doesn't match**: Spotify redirect only works for the exact URI you configured

**Solutions**:

**Option A: Add Multiple Redirect URIs** (Recommended if sharing with others)
1. Go to Spotify App Settings
2. Add additional redirect URIs for different access methods:
   ```
   http://127.0.0.1:5000/callback
   http://localhost:5000/callback
   http://YOUR_LOCAL_IP:5000/callback
   ```
3. Update your `.env` to use the appropriate URI

**Option B: Use a Public Domain** (For production deployment)
1. Deploy your app to a server with a public domain
2. Update redirect URI to: `https://your-domain.com/callback`
3. Update `.env` accordingly
4. Remember to use HTTPS in production!

### "Invalid Client" Error

**Problem**: Error message says "Invalid client" or "Invalid client secret"

**Solution**:
1. Go to your [Spotify Dashboard](https://developer.spotify.com/dashboard)
2. Click on your app
3. Regenerate your Client Secret if needed
4. Copy the new credentials to your `.env` file
5. Restart the server

## 📝 Important Notes

1. **Keep Credentials Secret**: Never commit your `.env` file to Git or share your Client Secret publicly
2. **Rate Limits**: Spotify has API rate limits. The free tier should be sufficient for personal use
3. **User Authorization**: Each user must authorize the app through Spotify OAuth
4. **Session Management**: Users stay logged in until they click "Logout" or clear browser data

## 🔐 Security Best Practices

1. **SECRET_KEY**: Always use a strong, random secret key for Flask sessions
2. **HTTPS**: Use HTTPS in production (Spotify requires it for public apps)
3. **Environment Variables**: Never hardcode credentials in your source code
4. **Git**: Ensure `.env` is in your `.gitignore` file

## 🌐 Deploying to Production

If you're deploying MelodySearch to a server (not just localhost):

1. **Update Redirect URI** in both:
   - Spotify Dashboard: `https://your-domain.com/callback`
   - `.env`: `SPOTIFY_REDIRECT_URI=https://your-domain.com/callback`

2. **Enable Quota Extension** (optional):
   - By default, Spotify apps are in "Development Mode" (25 users max)
   - For more users, submit your app for Extended Quota Mode in the Spotify Dashboard

3. **Use Environment Variables**: On your server, set environment variables instead of using `.env` file

## ✅ Verification Checklist

- [ ] Created Spotify Developer account
- [ ] Created app in Spotify Dashboard
- [ ] Added redirect URI: `http://127.0.0.1:5000/callback`
- [ ] Copied Client ID to `.env`
- [ ] Copied Client Secret to `.env`
- [ ] Generated and set SECRET_KEY in `.env`
- [ ] Started server: `python3 server.py`
- [ ] Clicked "Connect Spotify" button
- [ ] Authorized app on Spotify
- [ ] Redirected back to MelodySearch successfully
- [ ] See "Logged in as [Name]" in header

## 💡 Need Help?

If you're still having issues:
1. Check the server console for error messages
2. Open browser DevTools (F12) → Console tab to see JavaScript errors
3. Verify all environment variables are set correctly
4. Make sure you're using the exact redirect URI in both places

---

**Ready to go!** Once authenticated, you can:
- View your mood board based on listening history
- Create custom boards with aesthetic searches
- Save and share your favorite boards
- Discover new music recommendations
