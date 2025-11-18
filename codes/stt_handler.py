import os
from pathlib import Path
import torch
import sounddevice as sd
import numpy as np
import time
import asyncio
import webrtcvad
from faster_whisper import WhisperModel
import queue
import threading
from typing import Optional

# --- Configuration ---
SAMPLERATE = 16000
FRAME_MS = 20
BYTES_PER_SAMPLE = 2
FRAME_SIZE = int(SAMPLERATE * FRAME_MS / 1000)
SILENCE_THRESHOLD_MS = 800  # How long to wait in silence before stopping
VAD_AGGRESSIVENESS = 2  # 0-3, 3 is most aggressive at filtering non-speech

_DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
_DEFAULT_MODEL_PATH = _DEFAULT_MODEL_DIR / "faster-whisper-large-v3-turbo-ct2"
MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", str(_DEFAULT_MODEL_PATH))

device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

print(f"Loading Faster-Whisper model from: {MODEL_PATH}")
try:
    STT_MODEL = WhisperModel(
        MODEL_PATH,
        device=device,
        compute_type=compute_type,
    )
    print("Faster-Whisper model loaded successfully.")
except Exception as e:
    print(f"Error loading Faster-Whisper model from {MODEL_PATH}: {e}")
    STT_MODEL = None


async def listen_and_transcribe(
    audio_queue: queue.Queue, stop_event: Optional[threading.Event] = None
) -> str:
    """
    Listens for speech, sends amplitude data to a queue for visualization,
    and returns the transcribed text.
    """
    if not STT_MODEL:
        print("STT Model not available. Cannot transcribe.")
        await asyncio.sleep(1)
        return "Error: STT model not loaded."

    audio_data_queue: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        """This function is called by sounddevice for each audio chunk."""
        amplitude = np.sqrt(np.mean(indata**2))
        audio_queue.put(amplitude)

        pcm = (indata * 32767).astype(np.int16)
        audio_data_queue.put(pcm.tobytes())

    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    stream = sd.InputStream(
        samplerate=SAMPLERATE,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SIZE,
        callback=callback,
    )

    buffer = bytearray()
    speech_frames = []
    silent_count = 0
    max_silent_frames = int(SILENCE_THRESHOLD_MS / FRAME_MS)
    speech_started = False

    print("🎤 Listening...")
    with stream:
        start_time = time.time()
        while time.time() - start_time < 30:
            if stop_event and stop_event.is_set():
                if speech_started and len(speech_frames) >= 10:
                    print("Stop pressed - processing captured speech...")
                    break
                else:
                    print("Recording stopped by user.")
                    speech_frames = []
                    break
            
            while not audio_data_queue.empty():
                try:
                    buffer.extend(audio_data_queue.get_nowait())
                except queue.Empty:
                    break

            while len(buffer) >= FRAME_SIZE * BYTES_PER_SAMPLE:
                frame = buffer[: FRAME_SIZE * BYTES_PER_SAMPLE]
                buffer = buffer[FRAME_SIZE * BYTES_PER_SAMPLE :]

                if vad.is_speech(frame, SAMPLERATE):
                    if not speech_started:
                        print("🗣️ Speech detected...")
                        speech_started = True
                    silent_count = 0
                    speech_frames.append(np.frombuffer(frame, dtype=np.int16))
                else:
                    if speech_started:
                        speech_frames.append(np.frombuffer(frame, dtype=np.int16))
                    silent_count += 1

                if speech_started and silent_count > max_silent_frames:
                    print("Silence detected - stopping recording...")
                    break

            if speech_started and silent_count > max_silent_frames:
                break

            await asyncio.sleep(0.01)

    # Clear the queue of any remaining amplitude data
    while not audio_queue.empty():
        audio_queue.get_nowait()

    if len(speech_frames) < 10:
        print("⚠️ No valid speech detected.")
        return ""

    print(f"✨ Transcribing {len(speech_frames)} audio frames...")
    audio_np = np.concatenate(speech_frames, axis=0).astype(np.float32) / 32768.0
    segments, _ = STT_MODEL.transcribe(audio_np, beam_size=5)

    transcription = " ".join([seg.text for seg in segments]).strip()
    print(f"Transcription: {transcription}")
    return transcription
