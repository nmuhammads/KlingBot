"""
Result Sender Module.
Unified video delivery with fallback logic.
"""

import logging
import httpx

from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# Deeplink to profile in app
PROFILE_DEEPLINK = "https://t.me/AiVerseAppBot?startapp=profile"


async def send_video_result(
    bot: Bot,
    user_id: int,
    video_url: str,
    generation_id: int,
    lang: str = "ru",
    message_prefix: str = None
) -> bool:
    """
    Send video to user with robust fallback logic.
    
    Fallback strategy:
    1. Send as document by URL
    2. Download and send as document (file)
    3. Download and send as video (media)
    4. Send deeplink to profile in app
    
    Args:
        bot: Aiogram Bot instance
        user_id: Telegram user ID
        video_url: URL to the video file
        generation_id: Generation ID for logging
        lang: User language (ru/en)
        message_prefix: Optional message to send before video
        
    Returns:
        True if video was delivered, False if only deeplink was sent
    """
    
    # Success messages
    if message_prefix is None:
        message_prefix = "✅ Генерация завершена!" if lang == "ru" else "✅ Generation complete!"
    
    # Step 1: Try sending document by URL
    try:
        logger.info(f"[ResultSender] Gen {generation_id}: Trying send_document by URL")
        await bot.send_message(user_id, message_prefix)
        await bot.send_document(user_id, video_url, disable_content_type_detection=True)
        logger.info(f"[ResultSender] Gen {generation_id}: Success via URL")
        return True
    except Exception as e:
        logger.warning(f"[ResultSender] Gen {generation_id}: URL failed: {e}")
    
    # Step 2-3: Download video and try sending as file
    video_bytes = None
    try:
        logger.info(f"[ResultSender] Gen {generation_id}: Downloading video...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            video_bytes = response.content
            logger.info(f"[ResultSender] Gen {generation_id}: Downloaded {len(video_bytes)} bytes")
    except Exception as e:
        logger.error(f"[ResultSender] Gen {generation_id}: Download failed: {e}")
    
    if video_bytes:
        # Step 2: Try as document
        try:
            logger.info(f"[ResultSender] Gen {generation_id}: Trying send_document with file")
            input_file = BufferedInputFile(video_bytes, filename=f"video_{generation_id}.mp4")
            await bot.send_document(user_id, input_file, caption=message_prefix, disable_content_type_detection=True)
            logger.info(f"[ResultSender] Gen {generation_id}: Success as document file")
            return True
        except Exception as e:
            logger.warning(f"[ResultSender] Gen {generation_id}: Document file failed: {e}")
        
        # Step 3: Try as video (media)
        try:
            logger.info(f"[ResultSender] Gen {generation_id}: Trying send_video")
            input_file = BufferedInputFile(video_bytes, filename=f"video_{generation_id}.mp4")
            await bot.send_video(user_id, input_file, caption=message_prefix)
            logger.info(f"[ResultSender] Gen {generation_id}: Success as video media")
            return True
        except Exception as e:
            logger.warning(f"[ResultSender] Gen {generation_id}: Video media failed: {e}")
    
    # Step 4: Last resort - deeplink to profile
    try:
        logger.error(f"[ResultSender] Gen {generation_id}: All delivery methods failed, sending deeplink")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📱 Открыть профиль" if lang == "ru" else "📱 Open profile",
                url=PROFILE_DEEPLINK
            )]
        ])
        
        if lang == "ru":
            msg = (
                "⚠️ Не удалось отправить видео.\n\n"
                "Ваша генерация успешно завершена!\n"
                "Вы можете просмотреть результат в вашем профиле в приложении:"
            )
        else:
            msg = (
                "⚠️ Could not send the video.\n\n"
                "Your generation completed successfully!\n"
                "You can view the result in your profile in the app:"
            )
        
        await bot.send_message(user_id, msg, reply_markup=keyboard)
        return False
    except Exception as e:
        logger.error(f"[ResultSender] Gen {generation_id}: Even deeplink failed: {e}")
        return False


async def send_failure_result(
    bot: Bot,
    user_id: int,
    generation_id: int,
    error_msg: str,
    lang: str = "ru"
) -> bool:
    """
    Notify user about failed generation.
    
    Args:
        bot: Aiogram Bot instance
        user_id: Telegram user ID
        generation_id: Generation ID for logging
        error_msg: Error message from API
        lang: User language (ru/en)
        
    Returns:
        True if notification was sent
    """
    try:
        if lang == "ru":
            msg = f"❌ <b>Ошибка генерации</b>\n\n{error_msg}\n\n💰 Средства возвращены на баланс."
        else:
            msg = f"❌ <b>Generation failed</b>\n\n{error_msg}\n\n💰 Funds have been refunded."
        
        await bot.send_message(user_id, msg, parse_mode="HTML")
        logger.info(f"[ResultSender] Gen {generation_id}: Failure notification sent")
        return True
    except Exception as e:
        logger.error(f"[ResultSender] Gen {generation_id}: Failed to send failure notification: {e}")
        return False
