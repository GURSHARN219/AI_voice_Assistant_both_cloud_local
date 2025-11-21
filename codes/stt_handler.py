import os
from pathlib import Path
import asyncio
import numpy as np
import torch
import sounddevice as sd
import webrtcvad
import noisereduce as nr
import queue
import time
import threading
from typing import Optional

# --- Configuration ---
SAMPLERATE = 16000
FRAME_MS = 20
BYTES_PER_SAMPLE = 2
FRAME_SIZE = int(SAMPLERATE * FRAME_MS / 1000)
VAD_AGGRESSIVENESS = 1
SILENCE_THRESHOLD_MS = 1000
MAX_BUFFER_SECONDS = 15
MIN_STREAM_SECONDS = 0.4
MAX_LISTEN_SECONDS = 30

_DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
_DEFAULT_MODEL_PATH = _DEFAULT_MODEL_DIR / "faster-whisper-large-v3-turbo-ct2"
MODEL_PATH = os.getenv("WHISPER_MODEL_PATH", str(_DEFAULT_MODEL_PATH))

device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

# Model loaded in background thread
STT_MODEL = None
_loading_lock = threading.Lock()
_STT_MODEL_LOCK = threading.Lock()
_loading_thread = None
_status_callback = None


def set_status_callback(callback):
    """Set callback function to update GUI status."""
    global _status_callback
    _status_callback = callback


def _load_stt_model():
    """Load STT model synchronously (runs in background thread)."""
    global STT_MODEL
    if STT_MODEL is not None:
        return
    try:
        # Import here to avoid blocking GUI startup
        from faster_whisper import WhisperModel
        
        model_arg = str(MODEL_PATH)
        if not os.path.exists(model_arg):
            print(f"[STT] Model path {model_arg} not found, using default 'deepdml/faster-whisper-large-v3-turbo-ct2'")
            model_arg = "deepdml/faster-whisper-large-v3-turbo-ct2"

        STT_MODEL = WhisperModel(
            model_arg,
            device=device,
            compute_type=compute_type,
            cpu_threads=8,
            num_workers=1
        )
        print("Whisper large-v3-turbo loaded successfully!")
        if _status_callback:
            _status_callback("Whisper loaded successfully")
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        STT_MODEL = None


# Start loading immediately on import
print("Loading models")
_loading_thread = threading.Thread(target=_load_stt_model, daemon=True)
_loading_thread.start()


async def ensure_stt_model_loaded():
    """Ensure STT model is loaded (lazy load in background thread)."""
    global STT_MODEL
    if STT_MODEL is not None:
        return
    loop = asyncio.get_running_loop()
    with _loading_lock:
        if STT_MODEL is not None:
            return
        await loop.run_in_executor(None, _load_stt_model)


async def whisper_streaming_advanced(
    amplitude_queue: queue.Queue,
    stop_event: Optional[threading.Event] = None,
    partial_callback=None,
    final_callback=None,
) -> str:
    """
    VAD-based Auto-Recording Engine:
    1. Listens for speech (VAD).
    2. Records until silence.
    3. Transcribes final audio.
    No partial streaming to prevent hallucinations/lag.
    """
    # Ensure model is loaded before use
    await ensure_stt_model_loaded()
    if not STT_MODEL:
        print("[STT] Model not available. Cannot transcribe.")
        await asyncio.sleep(1)
        return "Error: STT model not loaded."

    vad = webrtcvad.Vad(2) # Increased aggressiveness (2)
    audio_data_queue = queue.Queue()

    # ------------- Sounddevice Callback ---------------
    def sd_callback(indata, frames, time_info, status):
        # indata is int16
        amp = float(np.sqrt(np.mean(indata.astype(np.float32)**2))) / 32768.0
        amplitude_queue.put(amp)
        audio_data_queue.put(indata.copy())

    # ----------------------------------------------------
    # RECORDING LOOP
    # ----------------------------------------------------
    buffer = []
    speech_started = False
    silent_frames = 0
    # 1000ms silence to stop
    max_silent = int(1000 / FRAME_MS) 
    
    stream = sd.InputStream(
        samplerate=SAMPLERATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME_SIZE,
        callback=sd_callback,
    )

    print("[STT] Listening (VAD Mode)...")

    with stream:
        while True:
            if stop_event and stop_event.is_set():
                break

            while not audio_data_queue.empty():
                frame = audio_data_queue.get()
                if frame.ndim == 2:
                    frame_mono = frame[:, 0]
                else:
                    frame_mono = frame
                
                is_speech = vad.is_speech(frame_mono.tobytes(), SAMPLERATE)

                if not speech_started:
                    # WAITING FOR SPEECH
                    if is_speech:
                        print("[STT] Speech detected - Recording...")
                        speech_started = True
                        buffer.append(frame_mono)
                        silent_frames = 0
                    else:
                        # Keep a small rolling buffer of pre-speech audio (0.5s)
                        buffer.append(frame_mono)
                        if len(buffer) > int(500 / FRAME_MS):
                            buffer.pop(0)
                else:
                    # RECORDING
                    buffer.append(frame_mono)
                    if is_speech:
                        silent_frames = 0
                    else:
                        silent_frames += 1
                    
                    # Stop on silence
                    if silent_frames > max_silent:
                        print("[STT] Silence detected - Processing...")
                        stop_event.set() # Break outer loop
                        break
                    
                    # Stop on max duration (30s)
                    if len(buffer) * FRAME_MS > 30000:
                        print("[STT] Max duration - Processing...")
                        stop_event.set()
                        break
            
            if stop_event.is_set():
                break
            
            await asyncio.sleep(0.005)

    # ----------------------------------------------------
    # TRANSCRIPTION
    # ----------------------------------------------------
    final_text = ""
    if len(buffer) > int(1000 / FRAME_MS): # Only transcribe if > 1s audio
        try:
            audio_np = np.concatenate(buffer)
            audio_float = audio_np.astype(np.float32) / 32768.0
            
            # Noise reduction
            audio_float = nr.reduce_noise(y=audio_float, sr=SAMPLERATE, prop_decrease=0.6)
            
            # Normalize
            max_amp = np.max(np.abs(audio_float))
            if max_amp > 0.01: # Amplitude threshold
                audio_float = audio_float / (max_amp + 1e-6)
                
                loop = asyncio.get_running_loop()
                segments, _ = await loop.run_in_executor(
                    None,
                    lambda: STT_MODEL.transcribe(
                        audio_float,
                        language="en",
                        beam_size=5,
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=500),
                        condition_on_previous_text=False,
                        temperature=0.0
                    )
                )
                
                final_text = " ".join([s.text for s in segments]).strip()
                
                # Hallucination filters
                filters = ["Thank you.", "Thanks for watching!", "You", "Bye.", ".", "MBC"]
                if final_text in filters or len(final_text) < 2:
                    final_text = ""
            else:
                print("[STT] Audio too quiet, ignoring.")

        except Exception as e:
            print(f"[STT] Error: {e}")

    if final_callback and final_text:
        final_callback(final_text)
    
    # Clear queues
    with amplitude_queue.mutex:
        amplitude_queue.queue.clear()
    
    return final_text


# Legacy alias for backward compatibility
async def listen_and_transcribe(
    audio_queue: queue.Queue, stop_event: Optional[threading.Event] = None
) -> str:
    """Legacy wrapper for backward compatibility."""
    return await whisper_streaming_advanced(
        amplitude_queue=audio_queue,
        stop_event=stop_event,
        partial_callback=None,
        final_callback=None
    )
