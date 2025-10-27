# run.py
import asyncio
import os
import threading
from src.bot.main import run_bot
from health_server import run_health_server

def main():
    # Start health check server in background
    run_health_server()
    
    # Run the bot
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
