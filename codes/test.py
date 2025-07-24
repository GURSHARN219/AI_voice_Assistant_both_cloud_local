import os
import time
import queue
import asyncio
import warnings
import numpy as np
import torch
import sounddevice as sd
import webrtcvad
import simpleaudio as sa
from faster_whisper import WhisperModel
from langdetect import detect_langs
from kokoro import KPipeline
from openai import OpenAI
import dotenv

# Load environment variables
dotenv.load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Suppress PyTorch warnings
warnings.filterwarnings(
    "ignore",
    message="torch.nn.utils.weight_norm is deprecated in favor of torch.nn.utils.parametrizations.weight_norm.",
)

# Configurations
LLM_MODEL = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
BASE_URL = "https://openrouter.ai/api/v1"
STT_MODEL_PATH = "A:/AI/AI_Models/local_models/ARS/faster-whisper-large-v3-turbo-ct2"
SAMPLING_RATE = 16000
FRAME_DURATION_MS = 20
FRAME_SIZE = int(SAMPLING_RATE * FRAME_DURATION_MS / 1000)
BYTES_PER_SAMPLE = 2

# AI Personality Prompt
CHARACTER_PERSONALITY = """
You are Sophia, a confident 20-year-old girl with a playful, cheeky personality. 
You're an AI assistant named Sophia. Remember: Respond naturally, keep it short, 
keep it real, keep it varied. Don't use overly formal language or complex words and emojis.
"""

# Audio queue used by stream callback
audio_queue = queue.Queue()

# Device setup
if torch.cuda.is_available():
    device = "cuda"
    compute_type = "float16"
    print("[+] CUDA is available. Using GPU.")
else:
    device = "cpu"
    compute_type = "int8"
    print("[-] CUDA not available. Using CPU.")

# Load Whisper STT model
print("[+] Loading Whisper STT model...")
try:
    stt_model = WhisperModel(STT_MODEL_PATH, device=device, compute_type=compute_type)
    print("[+] STT model loaded.")
except Exception as e:
    print(f"[!] Failed to load STT model: {e}")
    stt_model = None

# Load Kokoro TTS model
print("[+] Loading Kokoro TTS model...")
try:
    tts_pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    print("[+] TTS model loaded.")
except Exception as e:
    print(f"[!] Failed to load TTS model: {e}")
    tts_pipeline = None

# Initialize LLM client
print("[+] Initializing LLM client...")
llm_client = OpenAI(base_url=BASE_URL, api_key=OPENROUTER_API_KEY)
print("[+] LLM client ready.")


def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[!] Audio stream warning: {status}")
    pcm16 = (indata * 32767).astype(np.int16)
    audio_queue.put(pcm16.tobytes())


async def record_with_vad(max_duration=15, silence_duration=0.5):
    vad = webrtcvad.Vad(2)
    pcm_buffer = bytearray()
    speech_frames = []
    silent_frames = 0
    max_silent_frames = int(silence_duration * 1000 / FRAME_DURATION_MS)
    start_time = time.time()

    print("[*] Listening...")

    with sd.InputStream(
        samplerate=SAMPLING_RATE, channels=1, dtype="float32", callback=audio_callback
    ):
        while time.time() - start_time < max_duration:
            while not audio_queue.empty():
                pcm_buffer.extend(audio_queue.get())

                while len(pcm_buffer) >= FRAME_SIZE * BYTES_PER_SAMPLE:
                    frame_bytes = pcm_buffer[: FRAME_SIZE * BYTES_PER_SAMPLE]
                    pcm_buffer = pcm_buffer[FRAME_SIZE * BYTES_PER_SAMPLE :]

                    try:
                        is_speech = vad.is_speech(frame_bytes, SAMPLING_RATE)
                    except Exception as e:
                        print(f"[!] VAD error: {e}")
                        is_speech = False

                    if is_speech:
                        silent_frames = 0
                        speech_frames.append(np.frombuffer(frame_bytes, dtype=np.int16))
                    else:
                        silent_frames += 1
                        if speech_frames and silent_frames > max_silent_frames:
                            break

            if speech_frames and silent_frames > max_silent_frames:
                break

            await asyncio.sleep(0.01)

    if not speech_frames:
        print("[!] No speech detected.")
        return None

    return np.concatenate(speech_frames, axis=0)


def transcribe_and_detect_lang(audio_data: np.ndarray):
    if stt_model is None:
        return "STT model not loaded.", "en"

    print("[*] Transcribing...")
    segments, _ = stt_model.transcribe(audio_data, beam_size=5)
    text = " ".join(segment.text for segment in segments).strip()

    lang = "unknown"
    if text:
        try:
            langs = detect_langs(text)
            if langs:
                lang = langs[0].lang
        except Exception:
            pass

    return text, lang


async def query_llm(prompt: str):
    if not prompt:
        return "I didn't catch that. Could you say it again?"

    print("[*] Querying LLM...")
    try:
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": CHARACTER_PERSONALITY.strip()},
                {"role": "user", "content": prompt.strip()},
            ],
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        print(f"[Sophia]: {reply}")
        return reply
    except Exception as e:
        print(f"[!] LLM error: {e}")
        return "Oops, my brain just fizzled."


async def speak(text: str):
    if tts_pipeline is None or not text:
        return

    print("[*] Speaking...")
    generator = tts_pipeline(text, voice="af_heart")

    for _, _, audio in generator:
        audio_np = audio.cpu().numpy() if torch.is_tensor(audio) else np.array(audio)
        audio_bytes = (audio_np * 32767).astype(np.int16).tobytes()

        wave_obj = sa.WaveObject(
            audio_bytes, num_channels=1, bytes_per_sample=2, sample_rate=24000
        )
        play_obj = wave_obj.play()
        await asyncio.get_event_loop().run_in_executor(None, play_obj.wait_done)


async def main():
    if stt_model is None or tts_pipeline is None:
        print("[!] Exiting: Model(s) failed to load.")
        return

    print("🎤 Sophia is ready. Speak to begin.")
    print("   Say 'exit' or 'quit' to stop.")

    while True:
        try:
            audio_data = await record_with_vad()
            if audio_data is None:
                continue

            user_input, lang = transcribe_and_detect_lang(audio_data)
            if not user_input:
                print("[!] Nothing was transcribed.")
                continue

            print(f"[User ({lang})]: {user_input}")

            if user_input.strip().lower() in ["exit", "quit", "bye", "goodbye"]:
                print("Sophia: Bye! 👋")
                await speak("Bye!")
                break

            bot_reply = await query_llm(user_input)
            await speak(bot_reply)

        except KeyboardInterrupt:
            print("\n[!] Interrupted. Shutting down.")
            break
        except Exception as e:
            print(f"[!] Error in main loop: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[!] Fatal error: {e}")
