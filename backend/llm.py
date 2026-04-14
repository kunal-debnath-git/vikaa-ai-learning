import google.generativeai as genai
import anthropic
from backend.config import settings

async def call_llm(provider: str, prompt: str, system_prompt: str = "") -> str:
    if provider == "gemini":
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=system_prompt)
        response = model.generate_content(prompt)
        return response.text
    
    elif provider == "claude":
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
