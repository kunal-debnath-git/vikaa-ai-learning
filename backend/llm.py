import asyncio
from google import genai
from google.genai import types
import anthropic
from backend.config import settings


async def call_llm(provider: str, prompt: str, system_prompt: str = "") -> str:
    provider_cfg = settings.LLM_PROVIDERS.get(provider, {})

    if provider == "gemini":
        model = provider_cfg.get("model", "gemini-2.0-flash")
        max_tokens = provider_cfg.get("max_tokens", 8000)
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Gemini SDK is synchronous — run in thread to avoid blocking the event loop
        def _sync_call():
            return client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                ),
            )

        response = await asyncio.to_thread(_sync_call)
        return response.text

    elif provider == "claude":
        model = provider_cfg.get("model", "claude-sonnet-4-6")
        max_tokens = provider_cfg.get("max_tokens", 8000)
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
