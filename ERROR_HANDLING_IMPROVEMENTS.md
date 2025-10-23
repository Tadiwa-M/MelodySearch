# Error Handling and Usability Improvements

## Overview

This document describes the comprehensive error handling and usability improvements implemented across the MelodySearch application to ensure it meets the three core usability principles: **Learnability**, **Robustness**, and **Flexibility**.

## Three Core Usability Principles

### 1. Learnability (Easy to Learn and Use)

The application has been enhanced to be intuitive and easy to understand, even for first-time users.

#### Improvements:
- **Clear Error Messages**: All errors include user-friendly explanations of what went wrong
- **Actionable Suggestions**: Error responses include specific steps users can take to fix issues
- **Visual Indicators**: Uses emoji indicators (✓, ❌, 💡, ⚠️, 🔥) for better scanning
- **Progress Feedback**: Shows what the application is doing during long operations
- **Confidence Scores**: Provides quality indicators for identification results
- **Self-Documenting**: Error messages guide users without requiring documentation

#### Examples:
```python
# Before
return jsonify({"error": "Song not found"}), 404

# After
return create_error_response(
    'not_found',
    f'Song "{song_name}" not found',
    details='No matching songs found in Spotify catalog',
    suggestions=[
        'Check the spelling of the song name',
        'Try including the artist name in the search',
        'Try a more popular song or different search terms'
    ],
    status_code=404
)
```

### 2. Robustness (Error Tolerance and Recovery)

The application handles errors gracefully and recovers from failures when possible.

#### Improvements:
- **Retry Logic**: Automatic retries for transient failures (3 attempts with exponential backoff)
- **Graceful Degradation**: Continues with partial results when full results unavailable
- **Error Recovery**: Catches and handles specific error types with appropriate responses
- **Resource Cleanup**: Always cleans up temporary files and handles, even on errors
- **Data Protection**: Atomic file writes with backups prevent corruption
- **Input Validation**: Validates all inputs before processing
- **Fallback Mechanisms**: Provides alternative approaches when primary methods fail

#### Examples:

**Retry Logic with Exponential Backoff:**
```python
max_retries = 3
retry_delay = 1

for attempt in range(max_retries):
    try:
        results = sp.search(q=song_name, type='track', limit=1)
        break
    except spotipy.SpotifyException as e:
        if attempt < max_retries - 1:
            logging.warning(f"Search attempt {attempt + 1} failed, retrying...")
            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        else:
            # Handle failure after all retries
```

**Atomic File Writes:**
```python
# Write to temporary file first
temp_path = f"{path}.tmp"
with open(temp_path, 'w', encoding='utf-8') as f:
    f.write(json_str)
    f.flush()
    os.fsync(f.fileno())  # Ensure data written to disk

# Then atomically rename
os.replace(temp_path, path)
```

**Graceful Degradation:**
```python
# Try to get metadata, but continue with basic data if it fails
try:
    metadata_features = similarity_engine.extract_comprehensive_metadata(track['id'])
except Exception as e:
    logging.error(f"Metadata extraction failed: {e}")
    # Continue with limited features
    metadata_features = {
        'popularity': track.get('popularity', 50),
        'duration_ms': track.get('duration_ms', 180000),
        'feature_completeness': 0.3
    }
```

### 3. Flexibility (Accommodates User Preferences)

The application adapts to different situations and user needs.

#### Improvements:
- **Configurable Parameters**: Timeouts, retry counts, and other settings can be adjusted
- **Multiple Input Formats**: Supports various audio formats with auto-detection
- **Optional Fields**: Sensible defaults for optional parameters
- **Partial Results**: Returns what's available even if full processing fails
- **Detailed Error Modes**: Different error detail levels for debugging vs. production
- **Multiple Retry Attempts**: Allows users to correct mistakes (e.g., file path entry)

## Files Modified

### 1. server.py
**Major Enhancements:**
- Added `create_error_response()` helper for standardized error responses
- Added `validate_string_input()` for input validation
- Enhanced all API endpoints (/search, /similar-songs, /upload, /identify)
- Implemented retry logic with exponential backoff
- Added comprehensive error handling for network, API, and file errors
- Added missing imports (re, datetime)

**Key Features:**
- Standardized error response format across all endpoints
- User-friendly error messages with suggestions
- Proper HTTP status codes (400, 401, 403, 404, 413, 500, 503, 504)
- XSS prevention through input sanitization
- File validation (size, type, existence)
- Graceful degradation when services fail

### 2. audio_recorder.py
**Major Enhancements:**
- Comprehensive error handling in record() method
- Enhanced main() with retry logic and validation
- Better error messages for common audio issues
- Detailed troubleshooting guide

**Key Features:**
- Validates duration and filename
- Handles PortAudio-specific errors
- Provides targeted suggestions for:
  - Microphone not found
  - Permission denied
  - Buffer overflow
  - Device in use
- Keyboard interrupt handling
- File size validation after recording

### 3. song_identifier.py
**Major Enhancements:**
- File validation before processing
- Retry logic for MusicBrainz API
- Specific exception handling for AcoustID errors
- Confidence score interpretation
- Enhanced Spotify enrichment

**Key Features:**
- Validates file exists, readable, and has content
- Handles specific exceptions:
  - FingerprintGenerationError
  - WebServiceError
  - NoBackendError
  - NetworkError
- Provides installation instructions when fpcalc missing
- Interprets confidence scores (low/medium/high)
- Safe field extraction with defaults

### 4. main.py
**Complete Rewrite:**
- Professional CLI with comprehensive error handling
- File path validation with retry logic
- Visual progress indicators
- Formatted output with similarity percentages

**Key Features:**
- Validates audio files before processing
- Multiple retry attempts for user input (max 3)
- Visual indicators for similarity (🔥 ✓ •)
- Detailed error messages with suggestions
- Graceful handling of keyboard interrupts
- Helpful guidance when database is empty

### 5. library_manager.py
**Major Enhancements:**
- Enhanced JSON loading with corruption detection
- Atomic file writes with backups
- Data validation before saving
- Comprehensive logging

**Key Features:**
- Detects and backs up corrupted JSON files
- Atomic writes prevent data loss
- Validates data can be serialized
- Input sanitization (length limits)
- Permission error handling
- Detailed error information in return values

## Error Response Format

All API endpoints now use a standardized error response format:

```json
{
  "error": "error_type",
  "message": "User-friendly error message",
  "success": false,
  "details": "Technical details (optional)",
  "suggestions": [
    "Actionable suggestion 1",
    "Actionable suggestion 2"
  ],
  "timestamp": "2025-10-23T10:27:57.831Z"
}
```

## HTTP Status Codes

The application now uses appropriate HTTP status codes:

- **200**: Success
- **400**: Bad Request (invalid input)
- **401**: Unauthorized (authentication required)
- **403**: Forbidden (API error)
- **404**: Not Found (song/resource not found)
- **413**: Payload Too Large (file too big)
- **500**: Internal Server Error (unexpected error)
- **503**: Service Unavailable (external service down)
- **504**: Gateway Timeout (request timeout)

## Error Categories

Errors are categorized for better handling:

1. **Validation Errors**: Invalid input data
2. **Authentication Errors**: Missing or invalid authentication
3. **Not Found Errors**: Requested resource doesn't exist
4. **Network Errors**: Connection issues
5. **API Errors**: External service failures
6. **File Errors**: File access or format issues
7. **Internal Errors**: Unexpected application errors

## Logging Strategy

- **INFO**: Normal operation events
- **WARNING**: Recoverable issues (fallbacks used)
- **ERROR**: Errors that prevent operation completion
- **DEBUG**: Detailed information for debugging

All errors are logged with appropriate detail while user-facing messages remain simple and actionable.

## Retry Strategy

Network operations use exponential backoff:
- 1st retry: 1 second delay
- 2nd retry: 2 seconds delay
- 3rd retry: 3 seconds delay
- Then fail with helpful error message

## Best Practices Implemented

1. **Fail Fast**: Validate inputs early before expensive operations
2. **Fail Gracefully**: Provide partial results when possible
3. **Informative Errors**: Tell users what went wrong and how to fix it
4. **Resource Cleanup**: Always clean up files, connections, etc.
5. **Atomic Operations**: Use temporary files and rename for safety
6. **Data Validation**: Validate before processing and before saving
7. **Defensive Programming**: Check assumptions and handle edge cases
8. **User-Centric**: Error messages focus on user actions, not implementation

## Testing Recommendations

Test the following error scenarios:

### API Endpoints
- [ ] Invalid JSON input
- [ ] Missing required fields
- [ ] Oversized requests
- [ ] Network timeouts
- [ ] Spotify API failures
- [ ] Invalid audio files

### File Operations
- [ ] Missing files
- [ ] Corrupted files
- [ ] Permission denied
- [ ] Disk full
- [ ] Large files (>16MB)

### Audio Recording
- [ ] No microphone
- [ ] Permission denied
- [ ] Device in use
- [ ] Buffer overflow

### Song Identification
- [ ] Missing fpcalc
- [ ] Poor quality audio
- [ ] Network issues
- [ ] Unknown songs

## Subprinciples Addressed

The implementation addresses these usability subprinciples:

**Learnability:**
- Predictability: Consistent error format
- Synthesizability: Clear feedback on actions
- Familiarity: Standard HTTP codes and patterns
- Generalizability: Similar errors handled similarly
- Consistency: Uniform response structure

**Robustness:**
- Observability: Detailed logging
- Recoverability: Retry logic and fallbacks
- Responsiveness: Quick feedback on errors
- Task Conformance: Handles edge cases

**Flexibility:**
- Task Migratability: Partial results available
- Substitutivity: Multiple ways to achieve goals
- Customizability: Configurable parameters

## Conclusion

These improvements ensure that MelodySearch is:
- **Easy to use** with clear guidance when things go wrong
- **Resilient** to failures and errors
- **Flexible** in handling different scenarios

Users will have a much better experience with informative errors, helpful suggestions, and graceful handling of edge cases.
