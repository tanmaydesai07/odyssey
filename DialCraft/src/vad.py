"""
Voice Activity Detection for DialCraft.
Uses webrtcvad to detect when the caller starts and stops speaking.
This replaces the old fixed-size buffer approach with an intelligent
silence-based trigger.
"""
import webrtcvad
import audioop
from enum import Enum


class VADState(Enum):
    IDLE = "idle"               # Waiting for speech to begin
    SPEAKING = "speaking"       # User is actively speaking
    TRAILING = "trailing"       # Speech ended, counting silence frames


class VoiceActivityDetector:
    """Detects speech boundaries in a stream of 8kHz mu-law audio chunks.
    
    Twilio sends 20ms frames of 8kHz mu-law (160 bytes each).
    We convert to PCM for webrtcvad, track speech onset/offset,
    and signal when the user has finished a utterance.
    
    Args:
        aggressiveness: VAD sensitivity 0-3 (3 = most aggressive at filtering non-speech).
        silence_threshold_ms: How many ms of silence after speech before we trigger processing.
        speech_threshold_ms: How many ms of speech required before we consider it real speech
                             (avoids triggering on brief noises).
    """

    FRAME_MS = 20           # Twilio sends 20ms frames
    SAMPLE_RATE = 8000      # Twilio uses 8kHz
    FRAME_BYTES_MULAW = 160 # 8000 * 0.020 = 160 samples = 160 bytes (mu-law is 1 byte/sample)
    FRAME_BYTES_PCM = 320   # 160 samples * 2 bytes/sample (16-bit PCM)

    def __init__(
        self,
        aggressiveness: int = 2,
        silence_threshold_ms: int = 1000,
        speech_threshold_ms: int = 200,
    ):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.silence_frames_needed = silence_threshold_ms // self.FRAME_MS  # e.g., 50 frames
        self.speech_frames_needed = speech_threshold_ms // self.FRAME_MS    # e.g., 10 frames

        self.state = VADState.IDLE
        self.silence_count = 0
        self.speech_count = 0
        self.audio_buffer = bytearray()  # Accumulated mu-law audio during speech

    def reset(self):
        """Reset the detector for the next utterance."""
        self.state = VADState.IDLE
        self.silence_count = 0
        self.speech_count = 0
        self.audio_buffer.clear()

    def process_frame(self, mulaw_frame: bytes) -> bool:
        """Process a single 20ms frame of 8kHz mu-law audio.
        
        Args:
            mulaw_frame: 160 bytes of mu-law encoded audio (one 20ms frame).
            
        Returns:
            True if the user has finished speaking (time to process).
            False if still listening.
        """
        # Convert mu-law → 16-bit PCM for webrtcvad
        pcm_frame = audioop.ulaw2lin(mulaw_frame, 2)
        is_speech = self.vad.is_speech(pcm_frame, self.SAMPLE_RATE)

        if self.state == VADState.IDLE:
            if is_speech:
                self.speech_count += 1
                self.audio_buffer.extend(mulaw_frame)
                # Only transition to SPEAKING after enough speech frames
                # to avoid triggering on random noise
                if self.speech_count >= self.speech_frames_needed:
                    self.state = VADState.SPEAKING
                    print("[VAD] 🎙️ Speech detected — listening...")
            else:
                # Reset speech count if we get silence during the onset check
                self.speech_count = 0
                self.audio_buffer.clear()

        elif self.state == VADState.SPEAKING:
            self.audio_buffer.extend(mulaw_frame)
            if not is_speech:
                self.silence_count = 1
                self.state = VADState.TRAILING
            # else: keep accumulating

        elif self.state == VADState.TRAILING:
            self.audio_buffer.extend(mulaw_frame)
            if is_speech:
                # Speaker resumed — go back to SPEAKING
                self.silence_count = 0
                self.state = VADState.SPEAKING
            else:
                self.silence_count += 1
                if self.silence_count >= self.silence_frames_needed:
                    # Enough silence — the user has finished their utterance
                    print(f"[VAD] ⏸️  Silence detected ({self.silence_count * self.FRAME_MS}ms) — processing...")
                    return True

        return False

    def get_audio(self) -> bytes:
        """Return the accumulated mu-law audio buffer.
        
        Call this after process_frame() returns True.
        The buffer contains the full utterance including the trailing silence.
        """
        return bytes(self.audio_buffer)

    def get_audio_duration_ms(self) -> int:
        """Return the duration of audio in the buffer in milliseconds."""
        return (len(self.audio_buffer) * 1000) // self.SAMPLE_RATE
