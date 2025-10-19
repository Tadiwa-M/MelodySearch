# Security Best Practices

## Environment Variables

This application requires sensitive credentials to be configured via environment variables. **Never commit credentials directly to the codebase.**

### Required Environment Variables

1. **SECRET_KEY**: Flask session secret key
   - Must be a strong, random value
   - Generate using: `python -c "import secrets; print(secrets.token_hex(32))"`
   
2. **SPOTIFY_CLIENT_ID**: Your Spotify API client ID
   - Obtain from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)
   
3. **SPOTIFY_CLIENT_SECRET**: Your Spotify API client secret
   - Obtain from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)

### Setup Instructions

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your credentials:
   ```bash
   SECRET_KEY=<your-generated-secret-key>
   SPOTIFY_CLIENT_ID=<your-spotify-client-id>
   SPOTIFY_CLIENT_SECRET=<your-spotify-client-secret>
   ```

3. The `.env` file is already in `.gitignore` and will not be committed to version control.

## Security Measures Implemented

### 1. Credential Management
- All sensitive credentials are loaded from environment variables
- No hardcoded credentials in the codebase
- Application fails fast if required credentials are missing

### 2. HTTP Security Headers
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking attacks
- `X-XSS-Protection: 1; mode=block` - Enables XSS filter
- `Strict-Transport-Security` - Forces HTTPS in production
- `Content-Security-Policy` - Restricts resource loading

### 3. Input Validation
- Song name length validation (max 200 characters)
- Special character filtering to prevent injection attacks
- File upload validation (type, size, extension)

### 4. Dependency Security
- All dependencies are kept up to date
- Regular security audits using `pip-audit` or similar tools
- Known vulnerabilities are patched promptly

### 5. File Upload Security
- Filename sanitization using `secure_filename()`
- File size limits (16MB max)
- Allowed file extension whitelist
- Temporary file cleanup after processing

## Production Deployment

### Additional Security Recommendations

1. **Use HTTPS**: Always use HTTPS in production with valid SSL certificates
2. **Set FLASK_ENV=production**: Disable debug mode in production
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Firewall**: Use a firewall to restrict access to necessary ports only
5. **Monitoring**: Set up logging and monitoring for security events
6. **Regular Updates**: Keep all dependencies and the system up to date

### Example Production Configuration

```bash
# .env for production
SECRET_KEY=<strong-random-64-character-hex-string>
FLASK_ENV=production
SPOTIFY_CLIENT_ID=<your-client-id>
SPOTIFY_CLIENT_SECRET=<your-client-secret>
SPOTIFY_REDIRECT_URI=https://yourdomain.com/callback
PORT=5000
```

### Running with Gunicorn (Production)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 server:app
```

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please report it by:
1. **DO NOT** create a public GitHub issue
2. Email the repository maintainer privately
3. Include detailed information about the vulnerability
4. Allow reasonable time for a fix before public disclosure

## Security Audit Checklist

- [ ] All credentials are stored in environment variables
- [ ] `.env` file is in `.gitignore`
- [ ] Dependencies are up to date (run `pip list --outdated`)
- [ ] Security headers are configured
- [ ] Input validation is in place
- [ ] HTTPS is enabled in production
- [ ] Debug mode is disabled in production
- [ ] Rate limiting is configured
- [ ] Monitoring and logging are set up
