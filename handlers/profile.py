"""
Profile handler for KlingBot.
Handles /profile command and user statistics.
"""

import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import db
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    """Handle /profile command - show user profile and stats."""
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer(t("error_generic", "ru"))
        return
    
    lang = user.get("language_code", "ru") or "ru"
    if lang not in ("ru", "en"):
        lang = "ru"
    
    # Get generation count
    generations = db.get_user_generations(message.from_user.id, limit=100)
    gen_count = len(generations)
    
    await message.answer(
        t("profile", lang,
          user_id=message.from_user.id,
          username=message.from_user.username or "-",
          balance=user.get("balance", 0),
          generations=gen_count)
    )
