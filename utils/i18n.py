"""
Localization (i18n) module for KlingBot.
Contains all text messages in Russian and English.
"""

from typing import Dict, Any

MESSAGES: Dict[str, Dict[str, str]] = {
    # Common
    "welcome": {
        "ru": "🎬 <b>Добро пожаловать в KlingBot!</b>\n\nЯ помогу вам создавать видео с помощью ИИ Kling 2.6.\n\n🎥 <b>Text to Video</b> — видео из текста\n🖼 <b>Image to Video</b> — анимация изображения\n💃 <b>Motion Control</b> — перенос движений\n\n💰 Ваш баланс: <b>{balance} 🪙</b>",
        "en": "🎬 <b>Welcome to KlingBot!</b>\n\nI'll help you create videos with Kling 2.6 AI.\n\n🎥 <b>Text to Video</b> — video from text\n🖼 <b>Image to Video</b> — image animation\n💃 <b>Motion Control</b> — motion transfer\n\n💰 Your balance: <b>{balance} 🪙</b>"
    },
    "help": {
        "ru": "📖 <b>Справка по KlingBot</b>\n\n<b>Команды:</b>\n/start — Главное меню\n/generate — Создать видео\n/profile — Профиль и баланс\n/topup — Пополнить баланс\n/lang — Сменить язык\n\n<b>Режимы генерации:</b>\n🎥 T2V — видео по текстовому описанию\n🖼 I2V — анимация вашего изображения\n💃 MC — перенос движений с видео на фото",
        "en": "📖 <b>KlingBot Help</b>\n\n<b>Commands:</b>\n/start — Main menu\n/generate — Create video\n/profile — Profile & balance\n/topup — Add funds\n/lang — Change language\n\n<b>Generation modes:</b>\n🎥 T2V — video from text description\n🖼 I2V — animate your image\n💃 MC — transfer motion from video to photo"
    },
    
    # Main menu
    "main_menu": {
        "ru": "📱 <b>Главное меню</b>\n\nВыберите действие:",
        "en": "📱 <b>Main Menu</b>\n\nChoose an action:"
    },
    
    # Buttons
    "btn_generate": {
        "ru": "🎬 Сгенерировать",
        "en": "🎬 Generate"
    },
    "btn_profile": {
        "ru": "👤 Профиль",
        "en": "👤 Profile"
    },
    "btn_topup": {
        "ru": "💳 Пополнить",
        "en": "💳 Top up"
    },
    "btn_help": {
        "ru": "❓ Помощь",
        "en": "❓ Help"
    },
    "btn_back": {
        "ru": "◀️ Назад",
        "en": "◀️ Back"
    },
    "btn_cancel": {
        "ru": "❌ Отмена",
        "en": "❌ Cancel"
    },
    "btn_confirm": {
        "ru": "✅ Подтвердить",
        "en": "✅ Confirm"
    },
    
    # Generation modes
    "select_mode": {
        "ru": "🎬 <b>Выберите режим генерации:</b>",
        "en": "🎬 <b>Select generation mode:</b>"
    },
    "btn_t2v": {
        "ru": "🎥 Text to Video",
        "en": "🎥 Text to Video"
    },
    "btn_i2v": {
        "ru": "🖼 Image to Video",
        "en": "🖼 Image to Video"
    },
    "btn_mc": {
        "ru": "💃 Motion Control",
        "en": "💃 Motion Control"
    },
    
    # T2V Flow
    "t2v_prompt": {
        "ru": "🎥 <b>Text to Video</b>\n\nОтправьте текстовое описание видео (до 2500 символов):",
        "en": "🎥 <b>Text to Video</b>\n\nSend a text description for the video (up to 2500 characters):"
    },
    "t2v_aspect": {
        "ru": "📐 Выберите соотношение сторон:",
        "en": "📐 Select aspect ratio:"
    },
    "t2v_duration": {
        "ru": "⏱ Выберите длительность:",
        "en": "⏱ Select duration:"
    },
    "t2v_audio": {
        "ru": "🔊 Добавить озвучку?",
        "en": "🔊 Add audio?"
    },
    "btn_yes": {
        "ru": "✅ Да",
        "en": "✅ Yes"
    },
    "btn_no": {
        "ru": "❌ Нет",
        "en": "❌ No"
    },
    
    # I2V Flow
    "i2v_image": {
        "ru": "🖼 <b>Image to Video</b>\n\nОтправьте изображение для анимации:",
        "en": "🖼 <b>Image to Video</b>\n\nSend an image to animate:"
    },
    "i2v_prompt": {
        "ru": "📝 Введите текст-промпт (опишите желаемый сценарий):",
        "en": "📝 Enter a text prompt (describe the desired scenario):"
    },
    "btn_skip": {
        "ru": "⏭ Пропустить",
        "en": "⏭ Skip"
    },
    
    # MC Flow
    "mc_image": {
        "ru": "💃 <b>Motion Control</b>\n\nОтправьте фото (лицо видно чётко, голова + плечи + торс):",
        "en": "💃 <b>Motion Control</b>\n\nSend a photo (face visible, head + shoulders + torso):"
    },
    "mc_orientation_detailed": {
        "ru": "🔄 <b>Выберите ориентацию персонажа:</b>\n\n<b>🖼 Как на фото</b> — персонаж будет повёрнут так же, как на исходном фото.\n⚠️ Максимум <b>10 секунд</b> видео.\n\n<b>🎬 Как в видео</b> — персонаж повторит ориентацию актёра из референсного видео.\n✅ Максимум <b>30 секунд</b> видео.",
        "en": "🔄 <b>Select character orientation:</b>\n\n<b>🖼 As in photo</b> — character will be oriented as in the source photo.\n⚠️ Maximum <b>10 seconds</b> video.\n\n<b>🎬 As in video</b> — character will follow the orientation of the actor in reference video.\n✅ Maximum <b>30 seconds</b> video."
    },
    "btn_orient_image_full": {
        "ru": "🖼 Как на фото (до 10 сек)",
        "en": "🖼 As in photo (up to 10 sec)"
    },
    "btn_orient_video_full": {
        "ru": "🎬 Как в видео (до 30 сек)",
        "en": "🎬 As in video (up to 30 sec)"
    },
    "mc_video": {
        "ru": "🎬 Отправьте референсное видео с движениями (3-30 сек):",
        "en": "🎬 Send a reference video with motions (3-30 sec):"
    },
    "mc_video_with_limit": {
        "ru": "🎬 Отправьте референсное видео с движениями (3-{max_duration} сек):\n\n<b>📋 Требования:</b>\n• Минимум 720p разрешение\n• Формат: MP4, MOV\n• Размер: до 100 МБ\n• Видео должно чётко показывать голову, плечи и торс",
        "en": "🎬 Send a reference video with motions (3-{max_duration} sec):\n\n<b>📋 Requirements:</b>\n• Minimum 720p resolution\n• Format: MP4, MOV\n• Size: up to 100 MB\n• Video must clearly show head, shoulders and torso"
    },
    "mc_prompt": {
        "ru": "📝 Отправьте описание (опционально):",
        "en": "📝 Send a description (optional):"
    },
    "mc_orientation": {
        "ru": "🔄 Выберите ориентацию персонажа:",
        "en": "🔄 Select character orientation:"
    },
    "btn_orient_image": {
        "ru": "🖼 Как на фото",
        "en": "🖼 As in photo"
    },
    "btn_orient_video": {
        "ru": "🎬 Как в видео",
        "en": "🎬 As in video"
    },
    "mc_mode": {
        "ru": "📺 Выберите качество:",
        "en": "📺 Select quality:"
    },
    
    # Confirmation
    "confirm_generation": {
        "ru": "📋 <b>Подтвердите генерацию:</b>\n\n{details}\n\n💰 Стоимость: <b>{cost} 🪙</b>\n💳 Ваш баланс: <b>{balance} 🪙</b>",
        "en": "📋 <b>Confirm generation:</b>\n\n{details}\n\n💰 Cost: <b>{cost} 🪙</b>\n💳 Your balance: <b>{balance} 🪙</b>"
    },
    "insufficient_balance": {
        "ru": "❌ <b>Недостаточно средств!</b>\n\nСтоимость: {cost} 🪙\nВаш баланс: {balance} 🪙\n\nПополните баланс командой /topup",
        "en": "❌ <b>Insufficient funds!</b>\n\nCost: {cost} 🪙\nYour balance: {balance} 🪙\n\nTop up your balance with /topup"
    },
    
    # Generation status
    "generation_started": {
        "ru": "⏳ <b>Генерация запущена!</b>\n\nЭто может занять 1-3 минуты. Я пришлю результат, когда всё будет готово.",
        "en": "⏳ <b>Generation started!</b>\n\nThis may take 1-3 minutes. I'll send the result when it's ready."
    },
    "generation_success": {
        "ru": "✅ <b>Готово!</b>\n\nВаше видео сгенерировано:",
        "en": "✅ <b>Done!</b>\n\nYour video has been generated:"
    },
    "generation_failed": {
        "ru": "❌ <b>Ошибка генерации</b>\n\n{error}\n\n💰 Средства возвращены на баланс.",
        "en": "❌ <b>Generation failed</b>\n\n{error}\n\n💰 Funds have been refunded."
    },
    
    # Profile
    "profile": {
        "ru": "👤 <b>Ваш профиль</b>\n\n🆔 ID: <code>{user_id}</code>\n👤 Username: @{username}\n💰 Баланс: <b>{balance} 🪙</b>\n📊 Генераций: {generations}",
        "en": "👤 <b>Your Profile</b>\n\n🆔 ID: <code>{user_id}</code>\n👤 Username: @{username}\n💰 Balance: <b>{balance} 🪙</b>\n📊 Generations: {generations}"
    },
    
    # Top up
    "topup_method": {
        "ru": "💳 <b>Пополнение баланса</b>\n\nВыберите способ оплаты:",
        "en": "💳 <b>Top up balance</b>\n\nSelect payment method:"
    },
    "topup_amount": {
        "ru": "💵 Выберите сумму пополнения:",
        "en": "💵 Select top-up amount:"
    },
    "btn_stars": {
        "ru": "⭐ Telegram Stars",
        "en": "⭐ Telegram Stars"
    },
    "btn_sbp": {
        "ru": "💳 СБП",
        "en": "💳 SBP"
    },
    "btn_card": {
        "ru": "💳 Карта",
        "en": "💳 Card"
    },
    
    # Errors
    "error_generic": {
        "ru": "❌ Произошла ошибка. Попробуйте позже.",
        "en": "❌ An error occurred. Please try again later."
    },
    "error_invalid_image": {
        "ru": "❌ Некорректное изображение. Отправьте JPG, PNG или WebP.",
        "en": "❌ Invalid image. Send JPG, PNG or WebP."
    },
    "error_invalid_video": {
        "ru": "❌ Некорректное видео. Отправьте MP4 (3-30 сек).",
        "en": "❌ Invalid video. Send MP4 (3-30 sec)."
    },
    "error_video_too_short": {
        "ru": "❌ Видео слишком короткое (минимум 3 сек).",
        "en": "❌ Video too short (minimum 3 sec)."
    },
    "error_video_too_long": {
        "ru": "❌ Видео слишком длинное (максимум 30 сек).",
        "en": "❌ Video too long (maximum 30 sec)."
    },
    "error_video_exceeds_limit": {
        "ru": "❌ Видео слишком длинное для выбранного режима (максимум {max_duration} сек).",
        "en": "❌ Video too long for selected mode (maximum {max_duration} sec)."
    },
    
    # Language
    "lang_select": {
        "ru": "🌐 Выберите язык / Select language:",
        "en": "🌐 Выберите язык / Select language:"
    },
    "lang_changed": {
        "ru": "✅ Язык изменён на Русский",
        "en": "✅ Language changed to English"
    },
    
    # Cancelled
    "cancelled": {
        "ru": "❌ Действие отменено.",
        "en": "❌ Action cancelled."
    }
}


def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    """
    Get localized text by key.
    
    Args:
        key: Message key
        lang: Language code ('ru' or 'en')
        **kwargs: Format arguments
    
    Returns:
        Formatted localized string
    """
    if key not in MESSAGES:
        return f"[{key}]"
    
    text = MESSAGES[key].get(lang, MESSAGES[key].get("ru", f"[{key}]"))
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    
    return text


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Shorthand for get_text."""
    return get_text(key, lang, **kwargs)
