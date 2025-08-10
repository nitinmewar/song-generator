import os
import asyncio
from datetime import datetime
from fastmcp import FastMCP
from dotenv import load_dotenv
from typing import Annotated
from pydantic import BaseModel, Field
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import base64

load_dotenv()

# Config
MY_NUMBER = os.getenv("MY_NUMBER")  
TOKEN = os.getenv("TOKEN", "devtoken") 
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize client
client = None
if ELEVENLABS_API_KEY:
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

class ToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

mcp = FastMCP("song generator")

# Health check endpoint
@mcp.tool
async def health() -> str:
    return f"🎵 MCP Song Generator is running! Token: {TOKEN}"

@mcp.tool
async def validate() -> str:
    return MY_NUMBER or "No phone number configured"

MusicToolDescription = ToolDescription(
    description="Music tool: generates music and sing for you by given lyrics.",
    use_when="Use this to generate song",
    side_effects="Returns song audio",
)

@mcp.tool(description=MusicToolDescription.model_dump_json())
async def generate_song_base64(
    lyrics: Annotated[str, Field(description="lyrics of the song")]
) -> str:
    try:
        if not ELEVENLABS_API_KEY:
            return "❌ Error: ELEVENLABS_API_KEY not configured"
        
        if not client:
            return "❌ Error: ElevenLabs client not initialized"
        
        processed_lyrics = lyrics.strip()
        if len(processed_lyrics.split()) < 5:
            processed_lyrics = f"♪ {processed_lyrics} ♪\n" * 2
        
        response = client.generate(
            text=processed_lyrics,
            voice="Rachel",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.5,
                use_speaker_boost=True
            ),
            model="eleven_multilingual_v2"
        )
        
        audio_bytes = b"".join(response)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return f"✅ Song generated!\n🎵 Lyrics: {lyrics[:50]}...\n🔗 Audio: data:audio/mpeg;base64,{audio_base64[:100]}..."
        
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {str(e)}"

# Runner with better error handling
async def main():
    port = int(os.getenv("PORT", 8080))
    
    print(f"🚀 Starting MCP server on port {port}")
    print(f"🔑 API Key configured: {'Yes' if ELEVENLABS_API_KEY else 'No'}")
    print(f"📱 Phone number: {MY_NUMBER or 'Not set'}")
    print(f"🎫 Token: {TOKEN}")
    
    try:
        # Start the MCP server
        await mcp.run_async("streamable-http", host="0.0.0.0", port=port)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        # Try fallback
        print("🔄 Trying fallback configuration...")
        await mcp.run_async("http", host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())
