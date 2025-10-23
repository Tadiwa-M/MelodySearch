# Security Fixes Applied to server.py

## Overview
This document summarizes the security vulnerabilities fixed in `server.py` to protect the application from common web security threats.

## Critical Security Issues Fixed

### 1. Hardcoded API Credentials (CRITICAL)
**Issue**: Spotify API credentials were hardcoded in the source code (lines 33-34).
- Client ID: `9818b6e351d84e1ab29bf345fa7ee898`
- Client Secret: `3dc0f649da4b4bd1bf30966ea4f3f49e`

**Fix**: 
- Removed hardcoded credentials
- Now requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` environment variables
- Application logs an error if credentials are not set
- Prevents credential exposure in version control

**Action Required**: Set these environment variables before running the application:
```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
```

### 2. Weak Secret Key (CRITICAL)
**Issue**: Flask secret key had a weak default value (`dev-secret-key-12345`).

**Fix**:
- Requires `SECRET_KEY` environment variable to be set in production
- In development mode, generates a random secret key if none provided
- Application refuses to start in production without a proper secret key

**Action Required**: Set a strong secret key:
```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

### 3. Authentication Bypass (CRITICAL)
**Issue**: Line 233 had `session['is_authenticated'] = True`, bypassing authentication.

**Fix**:
- Removed authentication bypass
- Search endpoint now properly checks authentication status
- Returns 401 Unauthorized if user is not authenticated

### 4. Debug Mode in Production (HIGH)
**Issue**: Debug mode logic could enable debug in production (`!= 'production'`).

**Fix**:
- Debug mode now defaults to `production` (disabled)
- Only enables debug when `FLASK_ENV=development`
- Added warning when running in debug mode

### 5. Missing Security Headers (HIGH)
**Issue**: No security headers were set on HTTP responses.

**Fix**: Added security headers to all responses:
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Strict-Transport-Security` - Forces HTTPS

### 6. Insufficient File Upload Validation (MEDIUM)
**Issue**: Weak file upload validation could allow malicious uploads.

**Fix**:
- Added path traversal protection (checks for `..`, `/`, `\`)
- Validates file extension more strictly
- Added file size validation (checks both at app config and upload time)
- Validates file is not empty
- Uses `secure_filename()` for all uploaded files

### 7. URL Validation for External Requests (MEDIUM)
**Issue**: No validation of URLs before making external requests.

**Fix**:
- Added domain validation for Spotify preview URLs
- Only allows URLs from `*.spotify.com` and `*.scdn.co` domains
- Rejects potentially malicious URLs

### 8. Information Disclosure in Error Messages (MEDIUM)
**Issue**: Error messages exposed internal details to users.

**Fix**:
- Generic error messages for users
- Detailed errors only logged server-side
- Prevents information leakage about internal structure

### 9. Missing Input Validation (MEDIUM)
**Issue**: No validation of JSON input and song name.

**Fix**:
- Validates Content-Type is JSON
- Validates JSON structure
- Limits song name length to 200 characters
- Sanitizes input by stripping whitespace

### 10. Missing Authentication Function (BUG FIX)
**Issue**: `get_auth_manager()` function was used but not defined.

**Fix**:
- Added `get_auth_manager()` function
- Imported `SpotifyOAuth` for user authentication
- Properly configures OAuth with scope and cache

## Security Best Practices Applied

1. **Defense in Depth**: Multiple layers of validation and security checks
2. **Fail Secure**: Application refuses to start with insecure configuration
3. **Least Privilege**: Minimal permissions and exposure
4. **Input Validation**: All user inputs are validated and sanitized
5. **Secure Defaults**: Production mode is the default, not development
6. **Error Handling**: No sensitive information in user-facing errors

## Configuration Required

### Required Environment Variables
```bash
# Production (REQUIRED)
export SECRET_KEY="<strong-random-key>"
export SPOTIFY_CLIENT_ID="<your-client-id>"
export SPOTIFY_CLIENT_SECRET="<your-client-secret>"

# Optional
export SPOTIFY_REDIRECT_URI="http://127.0.0.1:5000/callback"
export FLASK_ENV="production"  # default
export PORT="5000"  # default
```

### Development Setup
```bash
export FLASK_ENV="development"
export SECRET_KEY="<any-key-for-testing>"
export SPOTIFY_CLIENT_ID="<your-dev-client-id>"
export SPOTIFY_CLIENT_SECRET="<your-dev-client-secret>"
```

## Testing the Security Fixes

1. **Test authentication requirement**:
   ```bash
   curl -X POST http://localhost:5000/search \
     -H "Content-Type: application/json" \
     -d '{"song_name": "test"}'
   # Should return 401 Unauthorized
   ```

2. **Test file upload validation**:
   ```bash
   curl -X POST http://localhost:5000/upload \
     -F "audio_file=@malicious_file.exe"
   # Should reject invalid file types
   ```

3. **Test without credentials**:
   ```bash
   unset SPOTIFY_CLIENT_ID SPOTIFY_CLIENT_SECRET
   python3 server.py
   # Should log error about missing credentials
   ```

## Known Limitations

1. **CSRF Protection**: Not implemented. Consider adding Flask-WTF for CSRF tokens.
2. **Rate Limiting**: Not implemented. Consider adding Flask-Limiter to prevent abuse.
3. **SQL Injection**: Not applicable (no SQL database used).
4. **Session Security**: Using filesystem sessions. Consider Redis for production.

## Future Security Enhancements

1. Add CSRF protection for state-changing operations
2. Implement rate limiting on API endpoints
3. Add request logging and monitoring
4. Implement API key rotation mechanism
5. Add Content Security Policy (CSP) headers
6. Consider adding Web Application Firewall (WAF)
7. Implement proper session management with Redis

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Spotify API Security](https://developer.spotify.com/documentation/web-api/)
