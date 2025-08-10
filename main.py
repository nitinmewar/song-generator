import os
import asyncio
from datetime import datetime
from typing import Optional, List
import aiosqlite
from fastmcp import FastMCP
from dotenv import load_dotenv
from typing import Annotated
from pydantic import BaseModel, Field
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import base64
import tempfile

load_dotenv()

# Config
MY_NUMBER = os.getenv("MY_NUMBER")  
TOKEN = os.getenv("TOKEN", "devtoken") 
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize client only if API key exists
client = None
if ELEVENLABS_API_KEY:
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

class ToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

mcp = FastMCP("song generator")

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
    """
    Generate a song and return as base64 encoded audio data.
    """
    try:
        # Check if API key is configured
        if not ELEVENLABS_API_KEY:
            return "❌ Error: ELEVENLABS_API_KEY not found in environment variables. Please check your .env file."
        
        if not client:
            return "❌ Error: ElevenLabs client not initialized"
        
        # Validate input
        if not lyrics or not lyrics.strip():
            return "❌ Error: No lyrics provided"
        
        processed_lyrics = lyrics.strip()
        
        # Expand short lyrics for better audio generation
        if len(processed_lyrics.split()) < 5:
            processed_lyrics = f"♪ {processed_lyrics} ♪\n" * 2
        
        print(f"Processing lyrics: {processed_lyrics[:50]}...")
        
        # Test API connection first
        try:
            voices = client.voices.get_all()
            print(f"✅ API connection successful. Available voices: {len(voices.voices)}")
        except Exception as api_error:
            return f"❌ Error connecting to ElevenLabs API: {str(api_error)}"
        
        # Generate audio with better error handling
        try:
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
            
            print("✅ Audio generation request sent")
            
            # Collect audio bytes
            audio_bytes = b"".join(response)
            
            if not audio_bytes:
                return "❌ Error: No audio data received from API"
            
            print(f"✅ Audio generated successfully. Size: {len(audio_bytes)} bytes")
            
            # Encode as base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return f"✅ Song generated successfully!\n🎵 Lyrics: {lyrics[:50]}...\n📊 Audio size: {len(audio_bytes)} bytes\n🔗 Base64 audio data:\ndata:audio/mpeg;base64,{audio_base64[:100]}..."
            
        except Exception as gen_error:
            return f"❌ Error during audio generation: {type(gen_error).__name__}: {str(gen_error)}"
        
    except Exception as e:
        return f"❌ Unexpected error: {type(e).__name__}: {str(e)}"

# Alternative function that saves to file
@mcp.tool
async def generate_song_file(
    lyrics: Annotated[str, Field(description="lyrics of the song")]
) -> str:
    """
    Generate a song and save to a temporary file.
    """
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
        
        # Save to temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.gettempdir()
        audio_filename = f"song_{timestamp}.mp3"
        audio_path = os.path.join(temp_dir, audio_filename)
        
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        
        # Verify file was created
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            return f"✅ Song saved to file!\n📁 Path: {audio_path}\n📊 Size: {file_size} bytes\n🎵 Lyrics: {lyrics[:50]}..."
        else:
            return "❌ Error: File was not created"
        
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {str(e)}"

# Test function to check ElevenLabs connection
@mcp.tool
async def test_elevenlabs_connection() -> str:
    """
    Test the ElevenLabs API connection.
    """
    try:
        if not ELEVENLABS_API_KEY:
            return "❌ No API key configured"
        
        if not client:
            return "❌ Client not initialized"
        
        # Test API connection
        voices = client.voices.get_all()
        voice_names = [voice.name for voice in voices.voices[:5]]  # Get first 5 voice names
        
        return f"✅ ElevenLabs connection successful!\n🎤 Available voices: {', '.join(voice_names)}\n📊 Total voices: {len(voices.voices)}"
        
    except Exception as e:
        return f"❌ Connection failed: {type(e).__name__}: {str(e)}"

# Runner
async def main():
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Starting MCP server on port {port}")
    print(f"🔑 API Key configured: {'Yes' if ELEVENLABS_API_KEY else 'No'}")
    print(f"📱 Phone number: {MY_NUMBER or 'Not set'}")
    
    await mcp.run_async("streamable-http", host="0.0.0.0", port=port)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())