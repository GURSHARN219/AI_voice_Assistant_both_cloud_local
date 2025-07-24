import torch
import numpy as np
import asyncio
import simpleaudio as sa
from kokoro import KPipeline

try:
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    print("Kokoro TTS model loaded successfully.")
except Exception as e:
    print(f"Error loading Kokoro TTS model: {e}")
    pipeline = None


async def speak_text(text: str):
    """
    Converts text to speech and plays it asynchronously.
    """
    if not pipeline:
        print("[TTS ERROR] TTS pipeline not available.")
        return

    try:
        for _, _, audio in pipeline(text, voice="af_heart"):
            audio_np = (
                audio.cpu().numpy() if torch.is_tensor(audio) else np.array(audio)
            )
            audio_int16 = (audio_np * 32767).astype(np.int16)

            wave_obj = sa.WaveObject(
                audio_int16, num_channels=1, bytes_per_sample=2, sample_rate=24000
            )
            play_obj = wave_obj.play()

            await asyncio.get_event_loop().run_in_executor(None, play_obj.wait_done)

    except Exception as e:
        print(f"[TTS ERROR] Could not speak text: {e}")
