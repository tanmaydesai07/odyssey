from faster_whisper import WhisperModel

class SpeechToText:
    def __init__(self, model_size="small.en"):
        # Force to CPU with int8 for speed
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path):
        """Converts saved audio file to text."""
        print("[⚙️ Transcribing...]")
        segments, _ = self.model.transcribe(audio_path, beam_size=5)
        text = "".join([segment.text for segment in segments])
        return text.strip()