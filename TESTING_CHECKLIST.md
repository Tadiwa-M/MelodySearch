# Testing Checklist for Song Identification Feature

## Automated Tests ✅

- [x] Module initialization tests (SongIdentifier class)
- [x] Method availability tests
- [x] Python syntax validation
- [x] Import verification

## Manual Testing Required 🧪

### Setup Testing

1. **Environment Configuration**
   - [ ] Create `.env` file from `.env.example`
   - [ ] Add `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
   - [ ] Optionally add `AUDD_API_KEY` for testing
   - [ ] Add `SECRET_KEY` for Flask session

2. **Server Startup**
   - [ ] Run `python server.py`
   - [ ] Verify server starts without errors
   - [ ] Check port 5000 is accessible
   - [ ] Open http://127.0.0.1:5000 in browser

### Frontend UI Testing

3. **Identify Section UI**
   - [ ] Verify "🔍 Identify Unknown Song" section appears
   - [ ] Check purple button styling
   - [ ] Test drag-and-drop area highlighting
   - [ ] Verify file type validation messages

4. **File Upload Testing**
   - [ ] Click to browse and select file
   - [ ] Drag and drop audio file
   - [ ] Verify file size validation (16MB max)
   - [ ] Check file format validation (MP3, WAV, FLAC, M4A, OGG)

### API Endpoint Testing

5. **Identification Endpoint (/identify)**

   **Test with curl:**
   ```bash
   # Get a sample audio file (use a popular song for best results)
   curl -X POST http://127.0.0.1:5000/identify \
     -F "audio_file=@test_song.mp3"
   ```

   Expected results:
   - [ ] Returns 200 status code for known songs
   - [ ] Returns JSON with song metadata
   - [ ] Includes title, artist, album
   - [ ] Includes album art URL
   - [ ] Includes Spotify link (if enriched)
   - [ ] Returns 404 for unknown songs with helpful message

6. **Response Validation**
   - [ ] Album art URL is valid and loads
   - [ ] Spotify link opens correctly
   - [ ] Genre information is accurate
   - [ ] Release date format is correct
   - [ ] Confidence score is present (if available)

### Integration Testing

7. **Spotify Enrichment**
   - [ ] Identified song gets enriched with Spotify data
   - [ ] Additional metadata appears (genres, popularity, etc.)
   - [ ] Album details are complete
   - [ ] Artist information is included

8. **Database Storage**
   - [ ] Check `Data/song_db.json` for saved songs
   - [ ] Verify identified songs are stored correctly
   - [ ] Confirm metadata structure is correct

### Error Handling Testing

9. **Error Scenarios**
   - [ ] Upload file larger than 16MB → shows error
   - [ ] Upload invalid file type → shows error
   - [ ] Identify very obscure song → returns 404 with suggestions
   - [ ] No file selected → shows error message
   - [ ] Network error → shows appropriate error

10. **Rate Limiting (if using free tier)**
    - [ ] Exceeding 50 requests/day returns rate limit message
    - [ ] Error message provides guidance

### Performance Testing

11. **Speed Testing**
    - [ ] Identification completes within 5-10 seconds
    - [ ] Loading indicator appears during processing
    - [ ] Button states update correctly (disabled during processing)

12. **File Size Testing**
    - [ ] Test with small file (~1MB)
    - [ ] Test with medium file (~5MB)
    - [ ] Test with large file (~15MB)
    - [ ] Verify processing time scales reasonably

### Compatibility Testing

13. **Audio Format Testing**
    - [ ] MP3 file identification works
    - [ ] WAV file identification works
    - [ ] FLAC file identification works
    - [ ] M4A file identification works
    - [ ] OGG file identification works

14. **Browser Compatibility**
    - [ ] Works in Chrome/Chromium
    - [ ] Works in Firefox
    - [ ] Works in Safari
    - [ ] Works in Edge
    - [ ] Mobile browser testing (optional)

### User Experience Testing

15. **Results Display**
    - [ ] Album art displays properly
    - [ ] Text is readable
    - [ ] Links are clickable
    - [ ] Layout looks good on different screen sizes
    - [ ] Smooth scrolling to results

16. **Multiple Identifications**
    - [ ] Can identify multiple songs in sequence
    - [ ] Previous results are replaced correctly
    - [ ] Upload area resets between identifications

## Test Audio Files Suggestions 🎵

Use popular songs for best results:

1. **Recent Pop Hits**
   - Blinding Lights by The Weeknd
   - Shape of You by Ed Sheeran
   - Levitating by Dua Lipa

2. **Classic Songs**
   - Bohemian Rhapsody by Queen
   - Hotel California by Eagles
   - Imagine by John Lennon

3. **Various Genres**
   - Hip-Hop: Lose Yourself by Eminem
   - Electronic: Strobe by deadmau5
   - Rock: Smells Like Teen Spirit by Nirvana

4. **Edge Cases**
   - Very short clip (5 seconds)
   - Low quality audio
   - Live recording
   - Cover version

## Success Criteria ✓

The feature is considered fully functional if:

1. ✓ Can identify popular songs with >90% success rate
2. ✓ Returns complete metadata including album art
3. ✓ Spotify enrichment works correctly
4. ✓ Error messages are helpful and actionable
5. ✓ UI is intuitive and responsive
6. ✓ Processing completes within reasonable time
7. ✓ No Python errors in server logs
8. ✓ No JavaScript errors in browser console

## Known Limitations ⚠️

Document any issues found during testing:

1. **AudD Free Tier**: Limited to 50 requests/day
2. **Database Coverage**: Very obscure songs may not be identified
3. **Audio Quality**: Poor quality audio may fail identification
4. **Processing Time**: Can take 5-10 seconds for full analysis

## Next Steps

After testing is complete:

- [ ] Document any bugs found
- [ ] Update documentation with testing findings
- [ ] Consider adding more example audio in documentation
- [ ] Possibly add demo mode with pre-identified songs
- [ ] Consider caching identification results

## Notes

Add any observations or issues here:

```
[Testing notes go here]
```

---

**Date Tested:** ___________  
**Tested By:** ___________  
**Environment:** ___________  
**Status:** ⬜ Pass / ⬜ Fail / ⬜ Partial
