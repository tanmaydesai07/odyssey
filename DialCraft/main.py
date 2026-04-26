"""
DialCraft — AI Voice Agent with Intelligent Voice Activity Detection.

Architecture:
  1. Twilio calls in → opens a WebSocket media stream
  2. Audio frames (8kHz mu-law, 20ms each) arrive continuously
  3. VAD detects when the user starts and stops speaking
  4. On speech end: STT → LLM → TTS → stream audio back to caller
  5. The AI greets the caller on connect, then listens for their turn
"""
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response
import uvicorn
import json
import base64
import audioop
import wave
import os
import asyncio
import numpy as np

# Import AI modules
from src.stt import SpeechToText
from src.llm import LLM
from src.tts import TextToSpeech
from src.vad import VoiceActivityDetector

# Fix for Intel OpenMP conflict
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

app = FastAPI()

# ── Initialize AI Brains (loaded once at startup) ──────────────────────
print("Loading AI Models into memory...")
stt = SpeechToText()
llm = LLM()
tts = TextToSpeech()
print("─── 🟢 DialCraft AI Ready! ───")


# ── Greeting message ───────────────────────────────────────────────────
GREETING = "Hello! This is DialCraft. How can I help you today?"


@app.post("/twiml")
async def twilio_webhook(request: Request):
    """Instructs Twilio to open the WebSocket (inbound call handler)."""
    host = request.headers.get("host", "your-ngrok-url.ngrok-free.app")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/media-stream" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="text/xml")


async def send_audio_to_twilio(websocket: WebSocket, stream_sid: str, audio_data: np.ndarray):
    """Convert TTS audio (24kHz float32) → 8kHz mu-law and stream to Twilio.
    
    Args:
        websocket: The active Twilio WebSocket.
        stream_sid: The Twilio stream session ID.
        audio_data: numpy array of float32 audio samples at 24kHz.
    """
    if audio_data is None:
        return

    # Convert Kokoro float32 → int16 PCM
    audio_int16 = (audio_data * 32767).astype(np.int16).tobytes()
    # Downsample 24kHz → 8kHz for phone lines
    audio_8k, _ = audioop.ratecv(audio_int16, 2, 1, 24000, 8000, None)
    # Convert PCM → telecom mu-law
    audio_ulaw = audioop.lin2ulaw(audio_8k, 2)

    # Stream in 20ms chunks (160 bytes at 8kHz mu-law)
    chunk_size = 160
    for i in range(0, len(audio_ulaw), chunk_size):
        chunk = audio_ulaw[i : i + chunk_size]
        payload = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": base64.b64encode(chunk).decode("utf-8")},
        }
        await websocket.send_text(json.dumps(payload))


async def send_tts_response(websocket: WebSocket, stream_sid: str, text: str):
    """Synthesize text and stream the audio back to the caller.
    
    Args:
        websocket: The active Twilio WebSocket.
        stream_sid: The Twilio stream session ID.
        text: Text to speak.
    """
    audio_data = tts.generate_speech(text)
    await send_audio_to_twilio(websocket, stream_sid, audio_data)


def mulaw_to_wav_16k(mulaw_bytes: bytes, output_path: str):
    """Convert accumulated 8kHz mu-law bytes → 16kHz PCM WAV file for Whisper.
    
    Args:
        mulaw_bytes: Raw mu-law audio bytes at 8kHz.
        output_path: Path to write the WAV file.
    """
    # mu-law → 16-bit PCM
    pcm_data = audioop.ulaw2lin(mulaw_bytes, 2)
    # Upsample 8kHz → 16kHz (Whisper expects 16kHz)
    pcm_16k, _ = audioop.ratecv(pcm_data, 2, 1, 8000, 16000, None)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm_16k)


@app.websocket("/media-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n[🟢 Call Connected!]")

    stream_sid = None
    vad = VoiceActivityDetector(
        aggressiveness=2,
        silence_threshold_ms=1200,  # 1.2s of silence → process
        speech_threshold_ms=200,    # 200ms of speech needed to trigger
    )
    conversation_history = []
    is_ai_speaking = False  # Prevent processing audio while AI is responding

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data["event"] == "start":
                stream_sid = data["start"]["streamSid"]
                print(f"[Stream Started] SID: {stream_sid}")

                # ── Send greeting ──────────────────────────────────
                print(f"🤖 AI: {GREETING}")
                is_ai_speaking = True
                await send_tts_response(websocket, stream_sid, GREETING)
                is_ai_speaking = False
                vad.reset()
                print("[🎧 Listening...]")

            elif data["event"] == "media":
                # Skip processing audio while the AI is speaking
                if is_ai_speaking:
                    continue

                payload = base64.b64decode(data["media"]["payload"])

                # ── Feed audio frames to VAD ──────────────────────
                # Twilio may send variable-length payloads, process in 160-byte frames
                for offset in range(0, len(payload), 160):
                    frame = payload[offset : offset + 160]
                    if len(frame) < 160:
                        # Pad short final frame with silence (mu-law silence = 0xFF)
                        frame = frame + b"\xff" * (160 - len(frame))

                    utterance_complete = vad.process_frame(frame)

                    if utterance_complete:
                        # ── User finished speaking — process! ─────
                        duration_ms = vad.get_audio_duration_ms()
                        print(f"\n[⚙️ Processing {duration_ms}ms of audio...]")

                        # 1. Convert accumulated mu-law → WAV
                        mulaw_audio = vad.get_audio()
                        wav_path = "temp/twilio_in.wav"
                        mulaw_to_wav_16k(mulaw_audio, wav_path)

                        # 2. Transcribe (Ears)
                        user_text = stt.transcribe(wav_path)
                        print(f"🗣️ You said: {user_text}")

                        # Reset VAD for the next utterance
                        vad.reset()

                        # Skip empty/noise transcriptions
                        if not user_text or len(user_text.strip()) < 2:
                            print("[⏭️ Skipping empty/noise transcription]")
                            print("[🎧 Listening...]")
                            continue

                        # 3. Think + Speak (streamed sentence by sentence)
                        is_ai_speaking = True
                        print("🤖 AI: ", end="", flush=True)

                        full_response = ""
                        for sentence in llm.generate_stream(user_text, history=conversation_history):
                            print(sentence + " ", end="", flush=True)
                            full_response += sentence + " "

                            # Generate TTS and stream back
                            audio_data = tts.generate_speech(sentence)
                            await send_audio_to_twilio(websocket, stream_sid, audio_data)

                        print()  # Newline after full response

                        # 4. Update conversation history
                        conversation_history.append({"role": "user", "content": user_text})
                        conversation_history.append({"role": "assistant", "content": full_response.strip()})

                        # Keep history manageable (last 10 turns = 20 messages)
                        if len(conversation_history) > 20:
                            conversation_history = conversation_history[-20:]

                        is_ai_speaking = False
                        print("[🎧 Listening...]")

            elif data["event"] == "stop" or data["event"] == "closed":
                print("\n[🔴 Call Disconnected]")
                break

    except Exception as e:
        print(f"Error during call: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)