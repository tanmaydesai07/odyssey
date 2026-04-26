import sounddevice as sd
import scipy.io.wavfile as wav
import os
import numpy as np

def record_audio(duration=5, sample_rate=16000, output_path="temp/user_input.wav"):
    """Records audio from the microphone."""
    os.makedirs("temp", exist_ok=True)
    
    print(f"\n[🎤 Listening for {duration} seconds... Speak now!]")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    wav.write(output_path, sample_rate, recording)
    return output_path

def play_audio(audio_data, sample_rate=24000):
    """Plays raw audio data through the speakers."""
    print("[🔊 Speaking...]")
    # Kokoro generates audio as float32 numpy arrays
    sd.play(audio_data, samplerate=sample_rate)
    sd.wait()