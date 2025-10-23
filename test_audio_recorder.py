#!/usr/bin/env python3
"""
Tests for Audio Recording Module

These tests validate the audio recording functionality including:
- Module imports and initialization
- Audio device detection
- Recording parameter validation
- File output and format validation
- Error handling
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


class TestAudioRecorderImport(unittest.TestCase):
    """Test that the audio recorder module can be imported."""
    
    def test_import_audio_recorder(self):
        """Test importing the audio_recorder module."""
        try:
            import audio_recorder
            self.assertIsNotNone(audio_recorder)
        except ImportError as e:
            self.fail(f"Failed to import audio_recorder: {e}")
    
    def test_import_audio_recorder_class(self):
        """Test importing the AudioRecorder class."""
        try:
            from audio_recorder import AudioRecorder
            self.assertIsNotNone(AudioRecorder)
        except ImportError as e:
            self.fail(f"Failed to import AudioRecorder class: {e}")


class TestAudioRecorderInitialization(unittest.TestCase):
    """Test AudioRecorder initialization."""
    
    def test_default_initialization(self):
        """Test initializing AudioRecorder with default parameters."""
        try:
            from audio_recorder import AudioRecorder
            recorder = AudioRecorder()
            self.assertEqual(recorder.sample_rate, 44100)
            self.assertEqual(recorder.channels, 1)
            self.assertEqual(recorder.dtype, 'int16')
        except Exception as e:
            self.fail(f"AudioRecorder initialization failed: {e}")
    
    def test_custom_initialization(self):
        """Test initializing AudioRecorder with custom parameters."""
        try:
            from audio_recorder import AudioRecorder
            recorder = AudioRecorder(
                sample_rate=48000,
                channels=2,
                dtype='float32'
            )
            self.assertEqual(recorder.sample_rate, 48000)
            self.assertEqual(recorder.channels, 2)
            self.assertEqual(recorder.dtype, 'float32')
        except Exception as e:
            self.fail(f"Custom AudioRecorder initialization failed: {e}")


class TestAudioRecorderMethods(unittest.TestCase):
    """Test AudioRecorder methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        from audio_recorder import AudioRecorder
        self.recorder = AudioRecorder()
    
    def test_list_input_devices_returns_list(self):
        """Test that list_input_devices returns a list."""
        result = self.recorder.list_input_devices()
        self.assertIsInstance(result, list)
    
    def test_validate_recording_empty(self):
        """Test validation of empty recording."""
        empty_recording = np.array([])
        result = self.recorder._validate_recording(empty_recording)
        self.assertFalse(result)
    
    def test_validate_recording_silent(self):
        """Test validation of silent recording."""
        silent_recording = np.zeros(1000)
        result = self.recorder._validate_recording(silent_recording)
        self.assertTrue(result)  # Silent is valid but warned
    
    def test_validate_recording_valid(self):
        """Test validation of valid recording."""
        # Create a simple sine wave
        duration = 1.0
        sample_rate = 44100
        frequency = 440  # A4 note
        t = np.linspace(0, duration, int(sample_rate * duration))
        valid_recording = (np.sin(2 * np.pi * frequency * t) * 16000).astype(np.int16)
        
        result = self.recorder._validate_recording(valid_recording)
        self.assertTrue(result)


class TestAudioRecorderFileOutput(unittest.TestCase):
    """Test audio recording file output."""
    
    def setUp(self):
        """Set up test fixtures."""
        from audio_recorder import AudioRecorder
        self.recorder = AudioRecorder()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('sounddevice.rec')
    @patch('sounddevice.wait')
    def test_record_creates_file(self, mock_wait, mock_rec):
        """Test that recording creates an output file."""
        # Mock the recording
        duration = 1.0
        sample_rate = 44100
        frames = int(duration * sample_rate)
        
        # Create mock audio data
        mock_audio = np.random.randint(-1000, 1000, frames).astype(np.int16).reshape(-1, 1)
        mock_rec.return_value = mock_audio
        
        # Record
        success, filepath = self.recorder.record(
            duration=duration,
            output_dir=self.temp_dir,
            show_progress=False
        )
        
        # Verify
        self.assertTrue(success)
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 0)
    
    @patch('sounddevice.rec')
    @patch('sounddevice.wait')
    def test_record_with_custom_filename(self, mock_wait, mock_rec):
        """Test recording with custom output filename."""
        # Mock the recording
        duration = 1.0
        sample_rate = 44100
        frames = int(duration * sample_rate)
        mock_audio = np.random.randint(-1000, 1000, frames).astype(np.int16).reshape(-1, 1)
        mock_rec.return_value = mock_audio
        
        custom_filename = "test_recording.wav"
        
        # Record
        success, filepath = self.recorder.record(
            duration=duration,
            output_file=custom_filename,
            output_dir=self.temp_dir,
            show_progress=False
        )
        
        # Verify
        self.assertTrue(success)
        self.assertIsNotNone(filepath)
        self.assertTrue(filepath.endswith(custom_filename))
        self.assertTrue(os.path.exists(filepath))


class TestAudioRecorderErrorHandling(unittest.TestCase):
    """Test error handling in AudioRecorder."""
    
    def setUp(self):
        """Set up test fixtures."""
        from audio_recorder import AudioRecorder
        self.recorder = AudioRecorder()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('sounddevice.rec')
    def test_record_handles_recording_error(self, mock_rec):
        """Test that recording handles errors gracefully."""
        # Mock an error during recording
        mock_rec.side_effect = Exception("Test error")
        
        # Record (should handle error gracefully)
        success, filepath = self.recorder.record(
            duration=1.0,
            output_dir=self.temp_dir,
            show_progress=False
        )
        
        # Verify error was handled
        self.assertFalse(success)
        self.assertIsNone(filepath)
    
    @patch('sounddevice.rec')
    @patch('sounddevice.wait')
    def test_record_validates_output(self, mock_wait, mock_rec):
        """Test that recording validates its output."""
        # Mock recording with invalid (empty) data
        mock_rec.return_value = np.array([])
        
        # Record
        success, filepath = self.recorder.record(
            duration=1.0,
            output_dir=self.temp_dir,
            show_progress=False
        )
        
        # Verify validation caught the issue
        self.assertFalse(success)


class TestAudioRecorderIntegration(unittest.TestCase):
    """Integration tests for AudioRecorder."""
    
    def test_full_recording_workflow(self):
        """Test the complete recording workflow (mocked)."""
        from audio_recorder import AudioRecorder
        import tempfile
        
        # Create recorder
        recorder = AudioRecorder(sample_rate=44100, channels=1)
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the actual recording
            with patch('sounddevice.rec') as mock_rec, \
                 patch('sounddevice.wait') as mock_wait:
                
                # Create realistic audio data
                duration = 2.0
                sample_rate = 44100
                frames = int(duration * sample_rate)
                
                # Generate a sine wave
                t = np.linspace(0, duration, frames)
                frequency = 440  # A4 note
                audio_data = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16)
                audio_data = audio_data.reshape(-1, 1)  # Make it mono
                
                mock_rec.return_value = audio_data
                
                # Record
                success, filepath = recorder.record(
                    duration=duration,
                    output_file="test.wav",
                    output_dir=temp_dir,
                    show_progress=False
                )
                
                # Verify success
                self.assertTrue(success)
                self.assertIsNotNone(filepath)
                self.assertTrue(os.path.exists(filepath))
                
                # Verify file can be read
                import soundfile as sf
                data, samplerate = sf.read(filepath)
                self.assertEqual(samplerate, recorder.sample_rate)
                self.assertGreater(len(data), 0)


class TestAudioRecorderCompatibility(unittest.TestCase):
    """Test compatibility with other MelodySearch components."""
    
    @patch('sounddevice.rec')
    @patch('sounddevice.wait')
    def test_output_compatible_with_librosa(self, mock_wait, mock_rec):
        """Test that recorded files are compatible with librosa."""
        from audio_recorder import AudioRecorder
        import tempfile
        
        recorder = AudioRecorder()
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock recording
            duration = 1.0
            frames = int(duration * recorder.sample_rate)
            mock_audio = np.random.randint(-1000, 1000, frames).astype(np.int16).reshape(-1, 1)
            mock_rec.return_value = mock_audio
            
            # Record
            success, filepath = recorder.record(
                duration=duration,
                output_dir=temp_dir,
                show_progress=False
            )
            
            self.assertTrue(success)
            
            # Try to load with librosa (if available)
            try:
                import librosa
                y, sr = librosa.load(filepath, sr=None)
                self.assertEqual(sr, recorder.sample_rate)
                self.assertGreater(len(y), 0)
            except ImportError:
                # librosa not available in test environment
                self.skipTest("librosa not available for compatibility test")


def run_tests():
    """Run all tests."""
    print("=" * 60)
    print("Audio Recorder Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorderImport))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorderInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorderMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorderFileOutput))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorderErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorderIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorderCompatibility))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
