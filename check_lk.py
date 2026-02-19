import os
import asyncio
from livekit import api
from dotenv import load_dotenv

async def main():
    load_dotenv(dotenv_path='c:/Users/inigo2.solana/ausarta-robot-voice-agent-platform/backend/.env')
    LIVEKIT_URL = os.getenv('LIVEKIT_URL')
    LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY')
    LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET')
    
    lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    print("Attributes of lkapi.agent_dispatch:")
    for attr in dir(lkapi.agent_dispatch):
        if not attr.startswith('_'):
            print(attr)
    
    # Also check if there is anything inside lkapi that looks like dispatch
    print("\nAll non-private attributes of lkapi:")
    for attr in dir(lkapi):
        if not attr.startswith('_'):
            print(attr)
            
    await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
