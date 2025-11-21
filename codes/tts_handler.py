import torch
import numpy as np
import asyncio
import simpleaudio as sa
import threading
import queue

# Pipeline loaded in background thread
pipeline = None
_PIPELINE_LOCK = threading.Lock()
_loading_thread = None
_status_callback = None


def set_status_callback(callback):
    """Set callback function to update GUI status."""
    global _status_callback
    _status_callback = callback


def _load_tts_pipeline():
    """Load TTS pipeline synchronously (runs in background thread)."""
    global pipeline
    if pipeline is not None:
        return
    try:
        # Import here to avoid blocking GUI startup
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
        print("KokoroTTS loaded successfully")
        if _status_callback:
            _status_callback("KokoroTTS loaded successfully")
    except Exception as e:
        print(f"Error loading Kokoro TTS model: {e}")
        pipeline = None


# Start loading immediately on import
_loading_thread = threading.Thread(target=_load_tts_pipeline, daemon=True)
_loading_thread.start()

# TTS Queues for pipelined processing
_text_queue = queue.Queue()
_audio_queue = queue.Queue()

def _generation_worker():
    """Worker thread to generate audio from text (Producer)."""
    while True:
        try:
            item = _text_queue.get()
            if item is None:
                break
            
            text, callback, on_complete = item
            
            # Handle empty text (just trigger callback)
            if not text or not text.strip():
                if on_complete:
                    _audio_queue.put((None, None, on_complete))
                _text_queue.task_done()
                continue

            # Ensure pipeline is loaded
            if pipeline is None:
                _load_tts_pipeline()
            
            if pipeline:
                print(f"[TTS] Generating: {text[:30]}...")
                try:
                    # Generate audio (this blocks until generation is done)
                    for _, _, audio in pipeline(text, voice="af_heart"):
                        audio_np = (
                            audio.cpu().numpy() if torch.is_tensor(audio) else np.array(audio)
                        )
                        audio_int16 = (audio_np * 32767).astype(np.int16)
                        
                        # Push to audio queue for playback
                        _audio_queue.put((audio_int16, callback, None))
                    
                    # Signal completion for this text block
                    if on_complete:
                        _audio_queue.put((None, None, on_complete))

                except Exception as e:
                    print(f"[TTS GEN ERROR] {e}")
                    # Even on error, we should probably trigger callback to avoid hanging
                    if on_complete:
                        _audio_queue.put((None, None, on_complete))
            else:
                print("[TTS ERROR] Pipeline failed to load.")
                if on_complete:
                    _audio_queue.put((None, None, on_complete))
                
            _text_queue.task_done()
        except Exception as e:
            print(f"[TTS WORKER ERROR] {e}")

def _playback_worker():
    """Worker thread to play audio (Consumer)."""
    while True:
        try:
            item = _audio_queue.get()
            if item is None:
                break
                
            audio_int16, callback, on_complete = item
            
            # Handle Audio Playback
            if audio_int16 is not None:
                # Calculate amplitude for visualization
                if callback:
                    # Convert back to float for amplitude calc
                    amplitude = float(np.abs(audio_int16).mean()) / 32768.0
                    callback(amplitude)

                try:
                    wave_obj = sa.WaveObject(
                        audio_int16, num_channels=1, bytes_per_sample=2, sample_rate=24000
                    )
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
                except Exception as e:
                    print(f"[TTS PLAY ERROR] {e}")
            
            # Handle Completion Callback
            if on_complete:
                try:
                    on_complete()
                except Exception as e:
                    print(f"[TTS CALLBACK ERROR] {e}")
                
            _audio_queue.task_done()
        except Exception as e:
            print(f"[TTS PLAY WORKER ERROR] {e}")

# Start workers
threading.Thread(target=_generation_worker, daemon=True).start()
threading.Thread(target=_playback_worker, daemon=True).start()


async def ensure_pipeline_loaded():
    """Ensure TTS pipeline is loaded (lazy load in background thread)."""
    global pipeline
    if pipeline is not None:
        return
    loop = asyncio.get_running_loop()
    with _PIPELINE_LOCK:
        if pipeline is not None:
            return
        await loop.run_in_executor(None, _load_tts_pipeline)


async def speak_text(text: str, amplitude_callback=None, on_complete=None):
    """
    Queues text for speech. Returns immediately.
    """
    _text_queue.put((text, amplitude_callback, on_complete))


async def speak_text_streaming(text: str, amplitude_callback=None, on_complete=None):
    """
    Converts text to speech immediately for streaming (sentence-by-sentence).
    
    Args:
        text: The text chunk to speak immediately
        amplitude_callback: Optional callback(amplitude: float) for visual feedback
        on_complete: Optional callback() when this chunk finishes playing
    """
    await speak_text(text, amplitude_callback, on_complete)
