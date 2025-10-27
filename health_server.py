# health_server.py
from aiohttp import web
import asyncio
import threading

async def health_check(request):
    return web.Response(text="Bot is running!")

def start_health_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    
    # Run on port 10000 (Render provides PORT env var in production)
    port = int(os.environ.get('PORT', 10000))
    
    web.run_app(app, port=port, host='0.0.0.0')

def run_health_server():
    """Run health server in a separate thread"""
    thread = threading.Thread(target=start_health_server, daemon=True)
    thread.start()
