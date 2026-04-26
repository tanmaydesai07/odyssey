from kokoro import KPipeline
import torch

class TextToSpeech:
    def __init__(self, lang_code='a', voice_name='af_heart'):
        # 'a' is for American English. We force it to CPU so your GPU stays dedicated to the LLM.
        self.device = 'cpu'
        self.pipeline = KPipeline(lang_code=lang_code)
        self.voice_name = voice_name
        print("[⚙️ Kokoro TTS Initialized on CPU]")

    def generate_speech(self, text):
        """Converts text to audio data."""
        # The pipeline acts as a generator. We will grab the first chunk.
        generator = self.pipeline(text, voice=self.voice_name, speed=1.0)
        
        # We combine chunks if the sentence is long
        full_audio = []
        for i, (graphemes, phonemes, audio) in enumerate(generator):
            full_audio.append(audio)
            
        import numpy as np
        if full_audio:
            return np.concatenate(full_audio)
        return None