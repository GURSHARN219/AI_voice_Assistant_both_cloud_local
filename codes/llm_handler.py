import os
from openai import OpenAI, APIConnectionError, RateLimitError
import asyncio
import dotenv

dotenv.load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

PRIMARY_PROVIDER_URL = "https://openrouter.ai/api/v1"
PRIMARY_MODEL = "moonshotai/kimi-k2:free"

FALLBACK_PROVIDER_URL = "http://localhost:1234/v1"
FALLBACK_MODEL = "google/gemma-3-4b"

CHARACTER_PERSONALITY = """
You are Sophia, a confident 20-year-old girl with a playful, cheeky personality. 
You're an AI assistant named Sophia. Remember: Respond naturally, keep it short, 
keep it real, keep it varied. Don't use overly formal language or complex words and emojis.
"""

primary_client = OpenAI(base_url=PRIMARY_PROVIDER_URL, api_key=OPENROUTER_API_KEY)
fallback_client = OpenAI(base_url=FALLBACK_PROVIDER_URL, api_key="lm-studio")


async def query_llm(prompt: str) -> tuple[str, str]:
    """
    Queries the LLM providers with a fallback mechanism and improved error handling.
    Returns the response text and the name of the provider used.
    """
    try:
        print("[LLM] 🔵 Trying OpenRouter...")
        response = await asyncio.to_thread(
            primary_client.chat.completions.create,
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": CHARACTER_PERSONALITY},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        print("[LLM] ✅ OpenRouter successful.")
        return response.choices[0].message.content.strip(), "OpenRouter"
    except APIConnectionError as e:
        print(
            f"[LLM] ❌ OpenRouter Connection Error: Could not connect to {PRIMARY_PROVIDER_URL}. Make sure the URL is correct and you have internet access."
        )
    except RateLimitError as e:
        print(
            f"[LLM] ⚠️ OpenRouter Rate Limit Error: You have exceeded your daily free usage limit."
        )
    except Exception as e:
        print(f"[LLM] ❌ An unexpected error occurred with OpenRouter: {e}")

    try:
        print("[LLM] 🟠 Trying LM Studio as fallback...")
        response = await asyncio.to_thread(
            fallback_client.chat.completions.create,
            model=FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": CHARACTER_PERSONALITY},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            stream=False,
        )
        print("[LLM] ✅ LM Studio successful.")
        return response.choices[0].message.content.strip(), "LM Studio"
    except APIConnectionError as e:
        print(
            f"[LLM] ❌ LM Studio Connection Error: Could not connect to {FALLBACK_PROVIDER_URL}. Make sure LM Studio is running and the server is enabled."
        )
    except Exception as e:
        print(f"[LLM] ❌ An unexpected error occurred with LM Studio: {e}")

    print("[LLM] 🔴 All LLM providers failed.")
    return "Oops! My thinking cap is offline right now.", "None"
