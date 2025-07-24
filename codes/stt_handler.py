import torch
import sounddevice as sd
import numpy as np
import time
import asyncio
import webrtcvad
from faster_whisper import WhisperModel
import queue

# --- Configuration ---
SAMPLERATE = 16000
FRAME_MS = 20
BYTES_PER_SAMPLE = 2
FRAME_SIZE = int(SAMPLERATE * FRAME_MS / 1000)
SILENCE_THRESHOLD_MS = 600  # How long to wait in silence before stopping
VAD_AGGRESSIVENESS = 2  # 0-3, 3 is most aggressive at filtering non-speech


MODEL_PATH = "A:/AI/AI_Models/local_models/ARS/faster-whisper-large-v3-turbo-ct2"
try:
    STT_MODEL = WhisperModel(
        MODEL_PATH,
        device="cuda" if torch.cuda.is_available() else "cpu",
        compute_type="float16",
    )
    print("Faster-Whisper model loaded successfully.")
except Exception as e:
    print(f"Error loading Faster-Whisper model from {MODEL_PATH}: {e}")
    STT_MODEL = None


async def listen_and_transcribe(audio_queue: queue.Queue) -> str:
    """
    Listens for speech, sends amplitude data to a queue for visualization,
    and returns the transcribed text.
    """
    if not STT_MODEL:
        print("STT Model not available. Cannot transcribe.")
        return ""

    local_audio_data = []

    def callback(indata, frames, time_info, status):
        """This function is called by sounddevice for each audio chunk."""
        amplitude = np.sqrt(np.mean(indata**2))
        audio_queue.put(amplitude)

        pcm = (indata * 32767).astype(np.int16)
        local_audio_data.append(pcm.tobytes())

    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    stream = sd.InputStream(
        samplerate=SAMPLERATE, channels=1, dtype="float32", callback=callback
    )

    buffer = bytearray()
    speech_frames = []
    silent_count = 0
    max_silent_frames = int(SILENCE_THRESHOLD_MS / FRAME_MS)

    with stream:
        start_time = time.time()
        while time.time() - start_time < 20:
            if local_audio_data:
                buffer.extend(local_audio_data.pop(0))

            while len(buffer) >= FRAME_SIZE * BYTES_PER_SAMPLE:
                frame = buffer[: FRAME_SIZE * BYTES_PER_SAMPLE]
                buffer = buffer[FRAME_SIZE * BYTES_PER_SAMPLE :]

                if vad.is_speech(frame, SAMPLERATE):
                    silent_count = 0
                    speech_frames.append(np.frombuffer(frame, dtype=np.int16))
                else:
                    silent_count += 1

                if speech_frames and silent_count > max_silent_frames:
                    break

            if speech_frames and silent_count > max_silent_frames:
                break

            await asyncio.sleep(0.01)

    # Clear the queue of any remaining amplitude data
    while not audio_queue.empty():
        audio_queue.get_nowait()

    if not speech_frames:
        print("No speech detected.")
        return ""

    print("Transcribing audio...")
    audio_np = np.concatenate(speech_frames, axis=0).astype(np.float32) / 32768.0
    segments, _ = STT_MODEL.transcribe(audio_np, beam_size=5)

    transcription = " ".join([seg.text for seg in segments]).strip()
    print(f"Transcription: {transcription}")
    return transcription
