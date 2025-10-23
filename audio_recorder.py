"""
Audio Recording Module for MelodySearch

This module provides functionality to record audio from the user's microphone.
It captures clear audio input (default 15 seconds), handles errors gracefully,
and produces WAV format output suitable for song recognition and feature extraction.

Features:
- Records audio from system microphone
- Configurable duration (default 15 seconds)
- High-quality audio capture (44.1 kHz sample rate, 16-bit)
- Comprehensive error handling
- Progress indication during recording
- WAV format output (compatible with librosa and existing feature extraction)

Usage:
    # Basic usage
    recorder = AudioRecorder()
    success, filepath = recorder.record()
    
    # Custom duration
    success, filepath = recorder.record(duration=30)
    
    # Custom output file
    success, filepath = recorder.record(output_file="my_recording.wav")
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import logging
import os
import sys
from datetime import datetime
from typing import Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class AudioRecorder:
    """
    Audio recorder class for capturing microphone input.
    
    This class handles all aspects of audio recording including:
    - Device selection and validation
    - Audio capture with proper parameters
    - Error handling and recovery
    - File output in WAV format
    """
    
    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 1,
        dtype: str = 'int16'
    ):
        """
        Initialize the AudioRecorder.
        
        Args:
            sample_rate: Sample rate in Hz (default 44100 for CD quality)
            channels: Number of audio channels (1=mono, 2=stereo, default 1)
            dtype: Data type for audio samples (default 'int16' for compatibility)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        
        # Validate audio device availability
        try:
            devices = sd.query_devices()
            self.default_input_device = sd.default.device[0]
            logging.info(f"Audio system initialized. Default input device: {self.default_input_device}")
        except Exception as e:
            logging.warning(f"Could not query audio devices: {e}")
            self.default_input_device = None
    
    def list_input_devices(self) -> list:
        """
        List all available input audio devices.
        
        Returns:
            List of tuples (device_id, device_name, channels)
        """
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for idx, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append((
                        idx,
                        device['name'],
                        device['max_input_channels']
                    ))
            
            return input_devices
        except Exception as e:
            logging.error(f"Error listing audio devices: {e}")
            return []
    
    def test_audio_device(self, duration: float = 1.0) -> bool:
        """
        Test if the audio device is working by recording a short sample.
        
        Args:
            duration: Test duration in seconds (default 1.0)
        
        Returns:
            True if device is working, False otherwise
        """
        try:
            logging.info("Testing audio device...")
            test_recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype
            )
            sd.wait()
            
            # Check if we got any audio data
            if np.max(np.abs(test_recording)) > 0:
                logging.info("Audio device test successful")
                return True
            else:
                logging.warning("Audio device test returned silent audio")
                return False
                
        except Exception as e:
            logging.error(f"Audio device test failed: {e}")
            return False
    
    def record(
        self,
        duration: float = 15.0,
        output_file: Optional[str] = None,
        output_dir: str = ".",
        show_progress: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Record audio from the microphone with comprehensive error handling.
        
        Args:
            duration: Recording duration in seconds (default 15.0)
            output_file: Optional custom output filename
            output_dir: Directory to save the recording (default current dir)
            show_progress: Whether to show recording progress (default True)
        
        Returns:
            Tuple of (success: bool, filepath: str or None)
            - success: True if recording succeeded, False otherwise
            - filepath: Path to the recorded file, or None if failed
        """
        # Validate duration
        if duration <= 0:
            logging.error("Duration must be positive")
            if show_progress:
                print("❌ Error: Duration must be greater than 0 seconds")
            return False, None
        
        if duration > 300:  # 5 minutes max
            logging.warning(f"Duration {duration}s exceeds recommended maximum (300s)")
            if show_progress:
                print(f"⚠️  Warning: Duration {duration}s is very long. Recommended max is 300s")
        
        try:
            # Generate output filename if not provided
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"recording_{timestamp}.wav"
            
            # Validate filename
            if not output_file.endswith('.wav'):
                logging.warning("Adding .wav extension to filename")
                output_file = output_file + '.wav'
            
            # Ensure output directory exists
            try:
                os.makedirs(output_dir, exist_ok=True)
            except PermissionError:
                logging.error(f"Permission denied to create directory: {output_dir}")
                if show_progress:
                    print(f"❌ Error: No permission to create directory {output_dir}")
                    print("💡 Try saving to your home directory or current directory")
                return False, None
            except Exception as e:
                logging.error(f"Failed to create output directory: {e}")
                if show_progress:
                    print(f"❌ Error: Could not create output directory: {e}")
                return False, None
            
            output_path = os.path.join(output_dir, output_file)
            
            # Check if file already exists
            if os.path.exists(output_path):
                logging.warning(f"File {output_path} already exists, will overwrite")
                if show_progress:
                    print(f"⚠️  File {output_path} already exists and will be overwritten")
            
            # Calculate number of frames
            frames = int(duration * self.sample_rate)
            
            logging.info(f"Starting recording: {duration} seconds at {self.sample_rate} Hz")
            if show_progress:
                print(f"\n🎤 Recording for {duration} seconds...")
                print("Please speak or play music now.")
                print("-" * 50)
            
            # Record audio with error handling
            try:
                recording = sd.rec(
                    frames,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype
                )
            except sd.PortAudioError as e:
                logging.error(f"PortAudio recording error: {e}")
                if show_progress:
                    if "Input overflowed" in str(e):
                        print("❌ Error: Audio input buffer overflow")
                        print("💡 Try:")
                        print("   - Close other audio applications")
                        print("   - Reduce input volume")
                        print("   - Use a lower sample rate")
                    elif "No such device" in str(e) or "device" in str(e).lower():
                        print("❌ Error: Microphone not found")
                        print("💡 Try:")
                        print("   - Check microphone connection")
                        print("   - Grant microphone permissions")
                        print("   - Restart the application")
                    elif "permission" in str(e).lower():
                        print("❌ Error: Microphone permission denied")
                        print("💡 Grant microphone access in your system settings")
                    else:
                        print(f"❌ Error: {e}")
                        print("💡 Check your audio device configuration")
                return False, None
            except Exception as e:
                logging.error(f"Unexpected recording error: {e}")
                if show_progress:
                    print(f"❌ Error: Recording failed - {e}")
                return False, None
            
            # Show progress during recording
            if show_progress:
                try:
                    self._show_recording_progress(duration)
                except KeyboardInterrupt:
                    logging.info("Recording cancelled by user")
                    print("\n\n⚠️  Recording cancelled by user")
                    sd.stop()
                    return False, None
            
            # Wait for recording to complete
            try:
                sd.wait()
            except KeyboardInterrupt:
                logging.info("Recording cancelled during wait")
                print("\n\n⚠️  Recording cancelled")
                sd.stop()
                return False, None
            
            # Validate recording
            if not self._validate_recording(recording):
                logging.error("Recording validation failed")
                if show_progress:
                    print("❌ Error: Recording validation failed")
                    print("💡 Try:")
                    print("   - Check that your microphone is working")
                    print("   - Ensure audio is being captured")
                    print("   - Increase input volume")
                return False, None
            
            # Save to file with error handling
            try:
                sf.write(output_path, recording, self.sample_rate)
            except PermissionError:
                logging.error(f"Permission denied writing to {output_path}")
                if show_progress:
                    print(f"❌ Error: No permission to write to {output_path}")
                    print("💡 Try saving to a different location")
                return False, None
            except Exception as e:
                logging.error(f"Failed to save recording: {e}")
                if show_progress:
                    print(f"❌ Error: Could not save recording - {e}")
                return False, None
            
            # Verify file was created successfully
            if not os.path.exists(output_path):
                logging.error(f"Failed to create output file: {output_path}")
                if show_progress:
                    print(f"❌ Error: File was not created at {output_path}")
                return False, None
            
            file_size = os.path.getsize(output_path)
            
            # Verify file size is reasonable
            expected_size = frames * self.channels * 2  # 2 bytes per sample for int16
            if file_size < expected_size * 0.5:  # File is less than 50% of expected size
                logging.warning(f"File size ({file_size} bytes) is smaller than expected")
                if show_progress:
                    print(f"⚠️  Warning: Recording may be incomplete (file size: {file_size} bytes)")
            
            logging.info(f"Recording saved successfully: {output_path} ({file_size} bytes)")
            
            if show_progress:
                print(f"\n✓ Recording complete!")
                print(f"  Saved to: {output_path}")
                print(f"  Duration: {duration} seconds")
                print(f"  Sample rate: {self.sample_rate} Hz")
                print(f"  File size: {file_size / 1024:.1f} KB")
            
            return True, output_path
            
        except KeyboardInterrupt:
            logging.info("Recording cancelled by user (Ctrl+C)")
            if show_progress:
                print("\n\n⚠️  Recording cancelled by user")
            return False, None
            
        except sd.PortAudioError as e:
            logging.error(f"PortAudio error during recording: {e}")
            if show_progress:
                if "Input overflowed" in str(e):
                    print("❌ Error: Audio input buffer overflow")
                    print("💡 Try closing other audio applications")
                elif "No such device" in str(e):
                    print("❌ Error: Audio device not found")
                    print("💡 Check your microphone connection")
                elif "permission" in str(e).lower():
                    print("❌ Error: Microphone access denied")
                    print("💡 Grant microphone permissions in system settings")
                else:
                    print(f"❌ Error: {e}")
            return False, None
            
        except Exception as e:
            logging.error(f"Unexpected error during recording: {e}", exc_info=True)
            if show_progress:
                print(f"❌ Error: An unexpected error occurred")
                print(f"Details: {e}")
                print("💡 Try:")
                print("   - Restarting the application")
                print("   - Checking microphone permissions")
                print("   - Using a different output directory")
            return False, None
    
    def _show_recording_progress(self, duration: float):
        """
        Show a progress indicator during recording.
        
        Args:
            duration: Total recording duration in seconds
        """
        try:
            import time
            
            # Show progress bar
            steps = min(int(duration), 50)  # Max 50 steps
            step_duration = duration / steps
            
            for i in range(steps):
                time.sleep(step_duration)
                progress = (i + 1) / steps
                bar_length = 40
                filled = int(bar_length * progress)
                bar = "█" * filled + "░" * (bar_length - filled)
                elapsed = (i + 1) * step_duration
                print(f"\r[{bar}] {progress*100:.0f}% ({elapsed:.1f}s/{duration:.1f}s)", end="", flush=True)
            
            print()  # New line after progress bar
            
        except Exception as e:
            # Progress display is non-critical, just log and continue
            logging.debug(f"Progress display error: {e}")
    
    def _validate_recording(self, recording: np.ndarray) -> bool:
        """
        Validate that the recording contains actual audio data.
        
        Args:
            recording: The recorded audio data
        
        Returns:
            True if recording is valid, False otherwise
        """
        try:
            # Check if recording is not empty
            if recording is None or len(recording) == 0:
                logging.error("Recording is empty")
                return False
            
            # Check if recording contains non-zero data
            max_amplitude = np.max(np.abs(recording))
            if max_amplitude == 0:
                logging.warning("Recording contains only silence")
                # Still return True as silence might be intentional
                return True
            
            # Check for clipping (values at maximum)
            if self.dtype == 'int16':
                max_value = 32767
                clipping_threshold = max_value * 0.99
                clipped_samples = np.sum(np.abs(recording) > clipping_threshold)
                clipping_percentage = (clipped_samples / len(recording)) * 100
                
                if clipping_percentage > 5:
                    logging.warning(f"Recording has {clipping_percentage:.1f}% clipped samples. "
                                  f"Consider reducing input volume.")
            
            # Log audio level information
            rms_level = np.sqrt(np.mean(recording**2))
            logging.info(f"Recording levels - Max: {max_amplitude}, RMS: {rms_level:.2f}")
            
            return True
            
        except Exception as e:
            logging.error(f"Recording validation error: {e}")
            return False
    
    def record_with_countdown(
        self,
        duration: float = 15.0,
        countdown: int = 3,
        output_file: Optional[str] = None,
        output_dir: str = "."
    ) -> Tuple[bool, Optional[str]]:
        """
        Record audio with a countdown before starting.
        
        Args:
            duration: Recording duration in seconds (default 15.0)
            countdown: Countdown duration in seconds (default 3)
            output_file: Optional custom output filename
            output_dir: Directory to save the recording
        
        Returns:
            Tuple of (success: bool, filepath: str or None)
        """
        try:
            import time
            
            print(f"\n🎤 Preparing to record for {duration} seconds...")
            print("Get ready!")
            
            for i in range(countdown, 0, -1):
                print(f"  Starting in {i}...", end="", flush=True)
                time.sleep(1)
                print("\r" + " " * 30, end="\r", flush=True)
            
            print("  Recording NOW!")
            
            return self.record(
                duration=duration,
                output_file=output_file,
                output_dir=output_dir,
                show_progress=True
            )
            
        except Exception as e:
            logging.error(f"Error in countdown recording: {e}")
            return False, None


def main():
    """
    Main function for command-line usage of the audio recorder.
    Enhanced with comprehensive error handling and user guidance.
    """
    print("=" * 60)
    print("MelodySearch - Audio Recorder")
    print("=" * 60)
    
    # Create recorder instance with error handling
    try:
        recorder = AudioRecorder()
    except Exception as e:
        print(f"\n❌ Error: Failed to initialize audio recorder")
        print(f"Details: {e}")
        print("\n💡 Try:")
        print("   - Installing PortAudio: sudo apt-get install portaudio19-dev")
        print("   - Checking that sounddevice is installed: pip install sounddevice")
        print("   - Restarting your system")
        return 1
    
    # List available input devices
    print("\nAvailable input devices:")
    devices = recorder.list_input_devices()
    if devices:
        for idx, name, channels in devices:
            print(f"  [{idx}] {name} ({channels} channels)")
    else:
        print("  ❌ No input devices found!")
        print("\n💡 Troubleshooting:")
        print("   - Check that a microphone is connected")
        print("   - Grant microphone permissions to this application")
        print("   - On Linux: Check if your user is in the 'audio' group")
        print("   - Restart your computer and try again")
        return 1
    
    # Test audio device
    print("\nTesting audio device...")
    try:
        if not recorder.test_audio_device():
            print("⚠️  Warning: Audio device test failed")
            print("\n💡 This could mean:")
            print("   - Microphone is not capturing audio")
            print("   - Input volume is too low")
            print("   - Wrong device is selected as default")
            
            response = input("\nContinue anyway? (y/n): ").strip().lower()
            if response != 'y':
                print("Recording cancelled.")
                return 1
        else:
            print("✓ Audio device is working")
    except Exception as e:
        print(f"⚠️  Warning: Could not test audio device: {e}")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Recording cancelled.")
            return 1
    
    # Get recording parameters with validation
    print("\nRecording Configuration:")
    
    # Get duration
    max_retries = 3
    duration = None
    for attempt in range(max_retries):
        try:
            duration_input = input(f"  Duration in seconds (default 15, max 300): ").strip()
            
            if not duration_input:
                duration = 15.0
                break
            
            duration = float(duration_input)
            
            if duration <= 0:
                print("  ❌ Error: Duration must be positive")
                if attempt < max_retries - 1:
                    print("  Please try again")
                continue
            
            if duration > 300:  # 5 minutes max
                print("  ❌ Error: Duration too long (max 300 seconds)")
                if attempt < max_retries - 1:
                    print("  Please try again")
                continue
            
            # Valid duration
            break
            
        except ValueError:
            print("  ❌ Error: Please enter a valid number")
            if attempt < max_retries - 1:
                print("  Please try again")
        except KeyboardInterrupt:
            print("\n\n⚠️  Cancelled by user")
            return 1
    
    if duration is None:
        print("❌ Too many invalid attempts. Exiting.")
        return 1
    
    # Get output filename
    try:
        output_file = input(f"  Output filename (default: auto-generated): ").strip()
        
        if not output_file:
            output_file = None
        else:
            # Validate filename
            if not output_file:
                output_file = None
            elif not output_file.endswith('.wav'):
                output_file += '.wav'
            
            # Check for invalid characters
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            if any(char in output_file for char in invalid_chars):
                print(f"  ⚠️  Warning: Filename contains invalid characters")
                print("  Using auto-generated filename instead")
                output_file = None
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        return 1
    
    # Record audio
    print("\n" + "=" * 60)
    try:
        success, filepath = recorder.record_with_countdown(
            duration=duration,
            countdown=3,
            output_file=output_file,
            output_dir="."
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Recording cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: Recording failed unexpectedly")
        print(f"Details: {e}")
        print("\n💡 Try:")
        print("   - Checking microphone permissions")
        print("   - Using a different microphone")
        print("   - Restarting the application")
        return 1
    
    if success and filepath:
        print("\n" + "=" * 60)
        print("✓ Recording completed successfully!")
        print("=" * 60)
        print(f"\n📁 Saved to: {filepath}")
        print("\nYou can now use this recording with MelodySearch:")
        print(f"  python main.py")
        print(f"  Enter path: {filepath}")
        print("\nOr identify the song:")
        print(f"  Use the /identify endpoint to identify this recording")
        return 0
    else:
        print("\n" + "=" * 60)
        print("✗ Recording failed!")
        print("=" * 60)
        print("\n💡 Common issues and solutions:")
        print("\n  1. Microphone not connected:")
        print("     - Check physical connection")
        print("     - Try a different USB port")
        print("\n  2. Permission denied:")
        print("     - Grant microphone access in system settings")
        print("     - On Linux: Add your user to 'audio' group")
        print("\n  3. Device already in use:")
        print("     - Close other applications using the microphone")
        print("     - Restart audio services")
        print("\n  4. Driver issues:")
        print("     - Update audio drivers")
        print("     - Try a different microphone")
        print("\n  5. System issues:")
        print("     - Restart your computer")
        print("     - Reinstall PortAudio")
        return 1


if __name__ == "__main__":
    sys.exit(main())
