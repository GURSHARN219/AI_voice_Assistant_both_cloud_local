import os
import asyncio
import dotenv
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIError

# Load environment variables
dotenv.load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PRIMARY_PROVIDER_URL = "https://openrouter.ai/api/v1"
PRIMARY_MODEL = "tngtech/deepseek-r1t2-chimera:free"

FALLBACK_PROVIDER_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
FALLBACK_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

CHARACTER_PERSONALITY = """
You are Sophia, a confident 20-year-old girl with a playful, cheeky personality. 
You're an AI assistant named Sophia. Remember: Respond naturally, keep it short, 
keep it real, keep it varied. Don't use overly formal language or complex words and emojis.
"""

# Initialize Clients (Conditional initialization to prevent startup crashes)
primary_client = None
if OPENROUTER_API_KEY:
    primary_client = AsyncOpenAI(
        base_url=PRIMARY_PROVIDER_URL, 
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "http://localhost:3000", 
            "X-Title": "Sophia AI"
        }
    )

# Ollama usually accepts any string as a key, but 'ollama' is standard
fallback_client = AsyncOpenAI(
    base_url=FALLBACK_PROVIDER_URL, 
    api_key=os.getenv("OLLAMA_API_KEY", "ollama")
)

async def query_llm(prompt: str, stream_callback=None) -> tuple[str, str]:
    """
    Queries the LLM providers with a fallback mechanism using native AsyncOpenAI.
    
    Args:
        prompt: User's question
        stream_callback: Optional callback(text_chunk) for streaming responses
        
    Returns tuple: (response_text, provider_name)
    """
    
    # --- Attempt 1: OpenRouter ---
    if primary_client:
        try:
            print(f"[LLM] 🔵 Trying OpenRouter ({PRIMARY_MODEL})...")
            
            if stream_callback:
                # Streaming mode
                full_response = ""
                stream = await primary_client.chat.completions.create(
                    model=PRIMARY_MODEL,
                    messages=[
                        {"role": "system", "content": CHARACTER_PERSONALITY},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    stream=True,
                )
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        stream_callback(content)
                
                if full_response:
                    print("[LLM] OpenRouter successful (streamed).")
                    return full_response.strip(), "OpenRouter"
            else:
                # Non-streaming mode
                response = await primary_client.chat.completions.create(
                    model=PRIMARY_MODEL,
                    messages=[
                        {"role": "system", "content": CHARACTER_PERSONALITY},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                )
                content = response.choices[0].message.content
                if content:
                    print("[LLM] OpenRouter successful.")
                    return content.strip(), "OpenRouter"
                
        except APIConnectionError as e:
            print(f"[LLM] OpenRouter Connection Error: {e}")
        except RateLimitError:
            print(f"[LLM] OpenRouter Rate Limit Reached (Free Tier).")
        except APIError as e:
            print(f"[LLM] OpenRouter API Error: {e}")
        except Exception as e:
            print(f"[LLM] Unexpected OpenRouter error: {e}")
    else:
        print("[LLM] OpenRouter skipped (No API Key found).")

    # --- Attempt 2: Ollama (Fallback) ---
    try:
        print(f"[LLM] Trying Ollama Fallback ({FALLBACK_MODEL})...")
        
        if stream_callback:
            # Streaming mode
            full_response = ""
            stream = await fallback_client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": CHARACTER_PERSONALITY},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    stream_callback(content)
            
            if full_response:
                print("[LLM] Ollama successful (streamed).")
                return full_response.strip(), "Ollama"
        else:
            # Non-streaming mode
            response = await fallback_client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": CHARACTER_PERSONALITY},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            if content:
                print("[LLM] Ollama successful.")
                return content.strip(), "Ollama"

    except APIConnectionError as e:
        print(f"[LLM] Ollama Connection Error: {e}")
        print(f"       Ensure Ollama is running at {FALLBACK_PROVIDER_URL}")
    except Exception as e:
        print(f"[LLM] Unexpected Ollama error: {e}")

    # --- All Failed ---
    print("[LLM] All LLM providers failed.")
    return "Oops! My thinking cap is offline right now.", "None"

# Example Usage Block
if __name__ == "__main__":
    async def main():
        response, provider = await query_llm("Tell me a joke about coding.")
        print(f"\n--- Final Output ({provider}) ---\n{response}")

    asyncio.run(main())