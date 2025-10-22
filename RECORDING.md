# Audio Recording Guide for MelodySearch

This guide explains how to use the audio recording feature to capture audio for song recognition in MelodySearch.

## Overview

MelodySearch now includes an audio recording system that allows you to:
- Record audio directly from your microphone
- Capture up to 15 seconds (or custom duration) of audio
- Produce WAV format output compatible with the song recognition system
- Handle errors gracefully with helpful feedback

## Quick Start

### Basic Recording (Interactive)

The easiest way to record audio is using the interactive script:

```bash
python record_audio.py
```

This will:
1. List available audio input devices
2. Test your audio device
3. Guide you through the recording process
4. Save the recording with an auto-generated filename

### Quick Recording (Non-Interactive)

For a quick recording without prompts:

```bash
python record_audio.py --quick --duration 15
```

### Recording with Custom Options

```bash
# Record for 30 seconds
python record_audio.py --duration 30

# Record with custom filename
python record_audio.py --output mysong.wav

# Record in stereo
python record_audio.py --stereo

# Skip countdown
python record_audio.py --countdown 0
```

## Command-Line Options

```
Usage: python record_audio.py [options]

Options:
  -d, --duration SECONDS    Recording duration (default: 15)
  -o, --output FILE         Output filename (default: auto-generated)
  -c, --countdown SECONDS   Countdown before recording (default: 3)
  -q, --quick              Quick mode: skip device checks
  --no-progress            Hide progress bar during recording
  --list-devices           List audio devices and exit
  --test-device            Test audio device and exit
  --sample-rate HZ         Sample rate (default: 44100)
  --stereo                 Record in stereo instead of mono
```

## Using in Python Code

You can also use the AudioRecorder class directly in your Python scripts:

```python
from audio_recorder import AudioRecorder

# Create recorder instance
recorder = AudioRecorder(
    sample_rate=44100,  # CD quality
    channels=1,         # Mono
    dtype='int16'       # 16-bit audio
)

# Record audio
success, filepath = recorder.record(
    duration=15.0,
    output_file="my_recording.wav",
    output_dir="./recordings",
    show_progress=True
)

if success:
    print(f"Recording saved to: {filepath}")
else:
    print("Recording failed!")
```

### Advanced Usage

```python
from audio_recorder import AudioRecorder

recorder = AudioRecorder()

# List available input devices
devices = recorder.list_input_devices()
for idx, name, channels in devices:
    print(f"Device {idx}: {name} ({channels} channels)")

# Test audio device
if recorder.test_audio_device(duration=1.0):
    print("Audio device is working!")

# Record with countdown
success, filepath = recorder.record_with_countdown(
    duration=15.0,
    countdown=3,
    output_file="song.wav"
)
```

## Integration with MelodySearch

After recording audio, you can use it with MelodySearch in two ways:

### 1. Command-Line Interface

```bash
# Record audio
python record_audio.py --output mysong.wav

# Use with MelodySearch
python main.py
# When prompted, enter: mysong.wav
```

### 2. Web Interface

```bash
# Record audio
python record_audio.py --output mysong.wav

# Start web server
python server.py

# Open browser to http://127.0.0.1:5000
# Click upload and select mysong.wav
```

## Audio Quality Settings

### Sample Rates

- **44100 Hz (default)**: CD quality, recommended for music
- **48000 Hz**: Professional audio, slightly higher quality
- **22050 Hz**: Lower quality, smaller file size

### Channels

- **Mono (1 channel, default)**: Sufficient for song recognition, smaller files
- **Stereo (2 channels)**: Full stereo recording, larger files

### Format

All recordings are saved in WAV format with 16-bit samples, which is:
- Uncompressed (high quality)
- Compatible with librosa and existing feature extraction
- Suitable for song recognition algorithms

## Troubleshooting

### "No audio devices found"

**Solution:**
1. Check that your microphone is connected
2. Verify microphone is enabled in system settings
3. Grant microphone permissions to your terminal/Python

### "Audio device test failed"

**Solution:**
1. Close other applications using the microphone
2. Try a different microphone
3. Check system audio settings
4. Update audio drivers

### "PortAudio library not found"

**Solution:**
On Linux:
```bash
sudo apt-get install portaudio19-dev libportaudio2
```

On macOS:
```bash
brew install portaudio
```

On Windows:
```bash
# PortAudio is included with sounddevice, no action needed
```

### "Recording contains only silence"

**Solution:**
1. Check microphone volume level in system settings
2. Speak louder or move closer to microphone
3. Test microphone with other applications
4. Check microphone is not muted

### "Input overflowed"

**Solution:**
1. Close other audio applications
2. Reduce system audio processing load
3. Try a lower sample rate (22050 Hz)

### Permission Issues

**On macOS:**
Grant microphone permissions:
- System Preferences → Security & Privacy → Microphone
- Enable for Terminal or your IDE

**On Linux:**
Ensure user is in audio group:
```bash
sudo usermod -a -G audio $USER
# Then log out and back in
```

## Technical Details

### Output Format

- **Container:** WAV (RIFF WAVE)
- **Sample Rate:** 44100 Hz (default, configurable)
- **Bit Depth:** 16-bit signed integer
- **Channels:** 1 (mono, default) or 2 (stereo)
- **Byte Order:** Little-endian

### Validation

The recorder automatically validates recordings for:
- Non-empty data
- Reasonable audio levels
- Clipping detection (warns if > 5% of samples are clipped)

### File Naming

Auto-generated filenames use the format:
```
recording_YYYYMMDD_HHMMSS.wav
```

Example: `recording_20251022_143055.wav`

## Examples

### Example 1: Quick Song Recognition

```bash
# Record a 15-second clip
python record_audio.py --quick

# The script will show the filename, e.g., recording_20251022_143055.wav

# Use with MelodySearch
python main.py
# Enter path: recording_20251022_143055.wav
```

### Example 2: Record and Compare Multiple Songs

```bash
# Record first song
python record_audio.py --output song1.wav --duration 20

# Record second song
python record_audio.py --output song2.wav --duration 20

# Use both with MelodySearch to compare
```

### Example 3: Batch Recording

```python
from audio_recorder import AudioRecorder
import time

recorder = AudioRecorder()

for i in range(5):
    print(f"\nRecording {i+1}/5...")
    success, filepath = recorder.record_with_countdown(
        duration=10.0,
        countdown=3,
        output_file=f"song_{i+1}.wav"
    )
    
    if success:
        print(f"Saved: {filepath}")
    
    # Wait before next recording
    if i < 4:
        print("\nPrepare next song...")
        time.sleep(5)
```

## Best Practices

1. **Environment:**
   - Record in a quiet environment
   - Minimize background noise
   - Position microphone appropriately

2. **Duration:**
   - 15 seconds is usually sufficient for song recognition
   - For full songs, use 30-60 seconds
   - Keep files under 5 minutes to avoid large file sizes

3. **Quality:**
   - Use default settings (44100 Hz, mono) for best compatibility
   - Only use stereo if specifically needed
   - Check recording levels (not too quiet, no clipping)

4. **Testing:**
   - Always test your audio device first
   - Do a short test recording before important captures
   - Verify the recording played back correctly

## Dependencies

The audio recording feature requires:
- **sounddevice**: Python interface to PortAudio
- **soundfile**: Reading/writing audio files
- **numpy**: Numerical operations
- **PortAudio**: System audio library

These are automatically installed with:
```bash
pip install -r requirements.txt
```

## Additional Resources

- [MelodySearch README](README.md) - Main documentation
- [MelodySearch Tasks](TASKS.md) - Feature overview
- [sounddevice Documentation](https://python-sounddevice.readthedocs.io/)
- [PortAudio Documentation](http://www.portaudio.com/docs.html)

---

**Happy Recording!** 🎤🎵
