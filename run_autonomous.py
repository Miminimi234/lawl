#!/usr/bin/env python3
import asyncio
from app.services.autonomous_worker import AutonomousLegalSystem
import os

print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     ⚖️  AUTONOMOUS JUDICIAL SYSTEM                        ║
║     📡 CONNECTED TO COURTLISTENER FEED                   ║
║                                                           ║
║     Three AI judges now analyzing real court cases...    ║
║     Press Ctrl+C to stop                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")

async def main():
    # Optional: Set your CourtListener API token for higher rate limits
    # Free tier: 5000 requests/day
    # Get token: https://www.courtlistener.com/api/rest-info/
    
    COURTLISTENER_TOKEN = os.getenv('COURTLISTENER_API_TOKEN')
    
    if COURTLISTENER_TOKEN:
        print("✅ CourtListener API token loaded (higher rate limits)")
    else:
        print("ℹ️  No CourtListener token - using free tier limits")
        print("   Get token at: https://www.courtlistener.com/api/rest-info/\n")
    
    system = AutonomousLegalSystem(courtlistener_token=COURTLISTENER_TOKEN)
    try:
        await system.run_forever()
    except KeyboardInterrupt:
        system.stop()
        print("\n\n⚖️  System adjourned.\n")

if __name__ == "__main__":
    asyncio.run(main())






