"""
FastAPI Web Application for KlingBot.
Handles Telegram Webhook and API callbacks.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from aiogram import types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

from bot import bot, dp
from config import settings
from database import db

# Import handlers to register them
from handlers import start, generate, profile, topup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting KlingBot...")
    
    # Register handlers
    dp.include_router(start.router)
    dp.include_router(generate.router)
    dp.include_router(profile.router)
    dp.include_router(topup.router)
    
    # Set webhook if URL is configured
    if settings.webhook_url:
        webhook_url = f"{settings.webhook_url}/webhook"
        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"Webhook set to: {webhook_url}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down KlingBot...")
    await bot.session.close()


# Create FastAPI application
app = FastAPI(title="KlingBot", lifespan=lifespan)


@app.post("/webhook")
async def webhook_handler(request: Request) -> Response:
    """Handle incoming Telegram updates via webhook."""
    try:
        update = types.Update.model_validate(await request.json())
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return Response(status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "bot": "KlingBot"}


@app.post("/callback/kling")
async def kling_callback(request: Request):
    """
    Callback endpoint for Kling API task completion notifications.
    This is called by kie.ai when a generation task completes.
    """
    try:
        data = await request.json()
        logger.info(f"Kling callback received: {data}")
        
        task_id = data.get("data", {}).get("taskId")
        state = data.get("data", {}).get("state")
        
        if task_id and state:
            # TODO: Process callback - update generation status and send result to user
            pass
            
    except Exception as e:
        logger.error(f"Error processing Kling callback: {e}")
    
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
