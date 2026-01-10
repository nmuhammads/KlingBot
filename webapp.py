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
    
    # Register bot commands
    commands = [
        types.BotCommand(command="start", description="🏠 Главное меню"),
        types.BotCommand(command="generate", description="🎬 Сгенерировать видео"),
        types.BotCommand(command="profile", description="👤 Профиль"),
        types.BotCommand(command="topup", description="💳 Пополнить баланс"),
        types.BotCommand(command="help", description="❓ Помощь"),
        types.BotCommand(command="lang", description="🌐 Сменить язык"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands registered")
    
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


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming HTTP requests."""
    import time
    start_time = time.time()
    
    # Log request
    logger.info(f">>> HTTP {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(f"<<< HTTP {request.method} {request.url.path} -> {response.status_code} ({process_time:.2f}ms)")
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"<<< HTTP {request.method} {request.url.path} -> ERROR ({process_time:.2f}ms): {e}")
        raise


@app.post("/webhook")
async def webhook_handler(request: Request) -> Response:
    """Handle incoming Telegram updates via webhook."""
    try:
        body = await request.json()
        logger.info(f"Received update: {body.get('update_id', 'unknown')}")
        
        update = types.Update.model_validate(body)
        await dp.feed_update(bot, update)
        
        logger.info(f"Update {body.get('update_id', 'unknown')} processed successfully")
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
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
    
    Handles both success and fail states, updating generation status
    even if polling already marked it as failed (late callback recovery).
    """
    import json
    
    try:
        body = await request.json()
        logger.info(f"Kling callback received: {body}")
        
        # Parse callback data
        data = body.get("data", {})
        task_id = data.get("taskId")
        state = data.get("state")
        
        # Get query params
        generation_id = request.query_params.get("generationId")
        user_id = request.query_params.get("userId")
        
        if not all([task_id, state, generation_id]):
            logger.warning(f"Incomplete callback data: taskId={task_id}, state={state}, generationId={generation_id}")
            return {"status": "error", "message": "Missing required fields"}
        
        # Get generation from database
        generation = db.get_generation(int(generation_id))
        if not generation:
            logger.error(f"Generation {generation_id} not found")
            return {"status": "error", "message": "Generation not found"}
        
        # Get user language for notifications
        user = db.get_user(int(user_id))
        lang = user.get("language_code", "ru") if user else "ru"
        
        if state == "success":
            # Parse result URLs from resultJson
            result_json = data.get("resultJson", "{}")
            if isinstance(result_json, str):
                try:
                    result_data = json.loads(result_json)
                except json.JSONDecodeError:
                    result_data = {}
            else:
                result_data = result_json
            
            result_urls = result_data.get("resultUrls", [])
            video_url = result_urls[0] if result_urls else None
            
            if video_url:
                current_status = generation.get("status")
                
                # Late callback recovery: generation was already marked as fail
                if current_status == "fail":
                    logger.info(f"Late callback recovery for generation {generation_id}")
                    cost = generation.get("cost", 0)
                    
                    # Try to deduct balance again (it was refunded on timeout)
                    if not db.deduct_balance(int(user_id), cost):
                        logger.warning(f"Could not deduct balance for late callback: user {user_id}, cost {cost}")
                        # Still update generation to success but note the balance issue
                    
                    # Notify user about late recovery
                    try:
                        if lang == "ru":
                            msg = "🎉 Отличные новости! Ваше видео готово (оно заняло больше времени чем обычно):"
                        else:
                            msg = "🎉 Great news! Your video is ready (it took longer than usual):"
                        await bot.send_message(int(user_id), msg)
                        await bot.send_document(int(user_id), video_url)
                    except Exception as e:
                        logger.error(f"Error sending late callback result: {e}")
                
                elif current_status in ("processing", "pending"):
                    # Normal callback - generation still in progress
                    try:
                        if lang == "ru":
                            msg = "✅ Генерация завершена!"
                        else:
                            msg = "✅ Generation complete!"
                        await bot.send_message(int(user_id), msg)
                        await bot.send_document(int(user_id), video_url)
                    except Exception as e:
                        logger.error(f"Error sending callback result: {e}")
                
                # Update generation status to completed
                db.update_generation(int(generation_id), "completed", video_url=video_url)
                
        elif state == "fail":
            fail_msg = data.get("failMsg", "Unknown error")
            current_status = generation.get("status")
            
            # Only process if not already completed (don't override good state)
            if current_status != "completed":
                db.update_generation(int(generation_id), "fail", error_message=fail_msg)
                
                # Refund if not already refunded (status was still processing or pending)
                if current_status in ("processing", "pending"):
                    cost = generation.get("cost", 0)
                    db.update_user_balance(int(user_id), cost)
                    
                    try:
                        if lang == "ru":
                            msg = f"❌ Ошибка генерации: {fail_msg}"
                        else:
                            msg = f"❌ Generation failed: {fail_msg}"
                        await bot.send_message(int(user_id), msg)
                    except Exception as e:
                        logger.error(f"Error sending fail notification: {e}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Kling callback: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

