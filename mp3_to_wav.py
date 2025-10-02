# Python
from pydub import AudioSegment

def convert_mp3_to_wav(mp3_path, wav_path):
    sound = AudioSegment.from_mp3(mp3_path)
    sound.export(wav_path, format="wav")

# Example usage:
if __name__ == "__main__":
    mp3_path = input("Enter the path to the MP3 file: ")
    wav_path = input("Enter the path to save the WAV file: ")
    convert_mp3_to_wav(mp3_path, wav_path)
    print(f"Converted {mp3_path} to {wav_path}.")
