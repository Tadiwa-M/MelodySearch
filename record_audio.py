#!/usr/bin/env python3
"""
Quick Audio Recording Script

Simple command-line script to record audio for use with MelodySearch.
This is a convenience wrapper around the AudioRecorder class.

Usage:
    # Record with default settings (15 seconds)
    python record_audio.py
    
    # Record with custom duration
    python record_audio.py --duration 30
    
    # Record with custom output file
    python record_audio.py --output my_song.wav
    
    # Quick recording (no countdown, no prompts)
    python record_audio.py --quick --duration 10
"""

import sys
import argparse
from audio_recorder import AudioRecorder


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Record audio for MelodySearch song recognition",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-d', '--duration',
        type=float,
        default=15.0,
        help='Recording duration in seconds (default: 15)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output filename (default: auto-generated with timestamp)'
    )
    
    parser.add_argument(
        '-c', '--countdown',
        type=int,
        default=3,
        help='Countdown before recording starts (default: 3 seconds)'
    )
    
    parser.add_argument(
        '-q', '--quick',
        action='store_true',
        help='Quick mode: skip device listing and testing'
    )
    
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Hide progress bar during recording'
    )
    
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List available audio input devices and exit'
    )
    
    parser.add_argument(
        '--test-device',
        action='store_true',
        help='Test audio device and exit'
    )
    
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=44100,
        help='Sample rate in Hz (default: 44100)'
    )
    
    parser.add_argument(
        '--stereo',
        action='store_true',
        help='Record in stereo (2 channels) instead of mono'
    )
    
    return parser.parse_args()


def list_devices_and_exit(recorder):
    """List available devices and exit."""
    print("Available audio input devices:")
    print("-" * 60)
    devices = recorder.list_input_devices()
    
    if devices:
        for idx, name, channels in devices:
            marker = "(*)" if idx == recorder.default_input_device else "   "
            print(f"{marker} [{idx}] {name}")
            print(f"       Max input channels: {channels}")
    else:
        print("No input devices found!")
        print("\nPlease check:")
        print("  - Microphone is connected")
        print("  - System audio settings")
        print("  - Driver installation")
        return 1
    
    print("-" * 60)
    print(f"Default input device: {recorder.default_input_device}")
    return 0


def test_device_and_exit(recorder):
    """Test audio device and exit."""
    print("Testing audio device...")
    print("-" * 60)
    
    if recorder.test_audio_device(duration=2.0):
        print("✓ Audio device is working correctly!")
        print("\nYou can proceed with recording.")
        return 0
    else:
        print("✗ Audio device test failed!")
        print("\nPlease check:")
        print("  - Microphone is connected and powered")
        print("  - Correct device is selected as default")
        print("  - Microphone permissions are granted")
        print("  - No other application is blocking the device")
        return 1


def quick_record(recorder, args):
    """Perform a quick recording without prompts."""
    print(f"🎤 Quick Recording: {args.duration} seconds")
    
    if args.countdown > 0:
        success, filepath = recorder.record_with_countdown(
            duration=args.duration,
            countdown=args.countdown,
            output_file=args.output,
            output_dir="."
        )
    else:
        success, filepath = recorder.record(
            duration=args.duration,
            output_file=args.output,
            output_dir=".",
            show_progress=not args.no_progress
        )
    
    return 0 if success else 1


def interactive_record(recorder, args):
    """Perform an interactive recording with device checks."""
    print("=" * 60)
    print("MelodySearch - Audio Recorder")
    print("=" * 60)
    
    # List devices
    print("\n1. Available input devices:")
    devices = recorder.list_input_devices()
    if devices:
        for idx, name, channels in devices:
            marker = "(*)" if idx == recorder.default_input_device else "   "
            print(f"{marker} [{idx}] {name} ({channels} channels)")
        print("\n   (*) = currently selected device")
    else:
        print("   No input devices found!")
        return 1
    
    # Test device
    print("\n2. Testing audio device...")
    if not recorder.test_audio_device(duration=1.5):
        print("   ⚠️  Warning: Audio device test failed")
        response = input("   Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("   Recording cancelled.")
            return 1
    else:
        print("   ✓ Audio device is working")
    
    # Recording info
    print("\n3. Recording Configuration:")
    print(f"   Duration: {args.duration} seconds")
    print(f"   Sample rate: {args.sample_rate} Hz")
    print(f"   Channels: {'Stereo (2)' if args.stereo else 'Mono (1)'}")
    if args.output:
        print(f"   Output file: {args.output}")
    else:
        print(f"   Output file: auto-generated")
    
    # Confirm
    print("\n4. Ready to record")
    response = input("   Press Enter to start recording, or 'q' to quit: ").strip().lower()
    if response == 'q':
        print("   Recording cancelled.")
        return 1
    
    # Record
    if args.countdown > 0:
        success, filepath = recorder.record_with_countdown(
            duration=args.duration,
            countdown=args.countdown,
            output_file=args.output,
            output_dir="."
        )
    else:
        success, filepath = recorder.record(
            duration=args.duration,
            output_file=args.output,
            output_dir=".",
            show_progress=not args.no_progress
        )
    
    if success and filepath:
        print("\n" + "=" * 60)
        print("✓ Recording completed successfully!")
        print("=" * 60)
        print(f"\nRecorded file: {filepath}")
        print("\nNext steps:")
        print("  1. Use with main.py:")
        print(f"     python main.py")
        print(f"     Enter path: {filepath}")
        print("\n  2. Or upload via web interface:")
        print("     python server.py")
        print("     Then upload the file in your browser")
        return 0
    else:
        print("\n" + "=" * 60)
        print("✗ Recording failed!")
        print("=" * 60)
        return 1


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Validate arguments
    if args.duration <= 0:
        print("Error: Duration must be positive")
        return 1
    
    if args.duration > 300:
        print("Error: Duration too long (max 300 seconds / 5 minutes)")
        return 1
    
    if args.countdown < 0:
        print("Error: Countdown cannot be negative")
        return 1
    
    # Create recorder
    try:
        channels = 2 if args.stereo else 1
        recorder = AudioRecorder(
            sample_rate=args.sample_rate,
            channels=channels,
            dtype='int16'
        )
    except Exception as e:
        print(f"Error initializing audio recorder: {e}")
        return 1
    
    # Handle special modes
    if args.list_devices:
        return list_devices_and_exit(recorder)
    
    if args.test_device:
        return test_device_and_exit(recorder)
    
    # Recording modes
    if args.quick:
        return quick_record(recorder, args)
    else:
        return interactive_record(recorder, args)


if __name__ == "__main__":
    sys.exit(main())
