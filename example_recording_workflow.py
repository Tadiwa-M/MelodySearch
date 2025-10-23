#!/usr/bin/env python3
"""
Example: Complete Audio Recording Workflow

This script demonstrates the complete workflow of:
1. Recording audio from the microphone
2. Analyzing the recorded audio
3. Finding similar songs

This is a simplified example showing integration with MelodySearch.
"""

import sys
import os
from audio_recorder import AudioRecorder


def main():
    """
    Demonstrate the complete recording and analysis workflow.
    """
    print("=" * 60)
    print("MelodySearch - Recording Workflow Example")
    print("=" * 60)
    
    # Step 1: Record audio
    print("\n[Step 1] Recording Audio")
    print("-" * 60)
    
    recorder = AudioRecorder()
    
    # Test audio device first
    print("Testing audio device...")
    if not recorder.test_audio_device():
        print("⚠️  Warning: Audio device test failed")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Workflow cancelled.")
            return 1
    
    # Record with countdown
    print("\nRecording 15 seconds of audio...")
    success, filepath = recorder.record_with_countdown(
        duration=15.0,
        countdown=3,
        output_file="example_recording.wav",
        output_dir="."
    )
    
    if not success or not filepath:
        print("\n✗ Recording failed!")
        return 1
    
    print(f"\n✓ Recording saved: {filepath}")
    
    # Step 2: Verify the recording
    print("\n[Step 2] Verifying Recording")
    print("-" * 60)
    
    try:
        import soundfile as sf
        data, samplerate = sf.read(filepath)
        duration = len(data) / samplerate
        
        print(f"✓ File format: WAV")
        print(f"  Sample rate: {samplerate} Hz")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Samples: {len(data)}")
        print(f"  File size: {os.path.getsize(filepath) / 1024:.1f} KB")
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return 1
    
    # Step 3: Show next steps
    print("\n[Step 3] Next Steps")
    print("-" * 60)
    print("\nYour recording is ready! You can now:")
    print("\n1. Use with the web interface:")
    print("   - Start server: python server.py")
    print("   - Open browser: http://127.0.0.1:5000")
    print(f"   - Upload file: {filepath}")
    
    print("\n2. Use with command line (if supported):")
    print("   - Run: python main.py")
    print(f"   - Enter path: {filepath}")
    
    print("\n3. Analyze with librosa (optional):")
    print("   >>> import librosa")
    print(f"   >>> y, sr = librosa.load('{filepath}')")
    print("   >>> tempo, beats = librosa.beat.beat_track(y=y, sr=sr)")
    print("   >>> print(f'Tempo: {tempo} BPM')")
    
    print("\n" + "=" * 60)
    print("✓ Workflow complete!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
