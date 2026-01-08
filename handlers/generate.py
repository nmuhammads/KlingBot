"""
Generate handler for KlingBot.
Handles video generation flows: T2V, I2V, Motion Control.
"""

import logging
import asyncio
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from database import db
from config import settings
from utils.i18n import t
from utils.kling_api import kling_client, KlingPricing, KlingModel, TaskState

logger = logging.getLogger(__name__)
router = Router()


# ==================== FSM States ====================

class T2VStates(StatesGroup):
    """States for Text-to-Video flow."""
    waiting_prompt = State()
    waiting_aspect = State()
    waiting_duration = State()
    waiting_audio = State()
    confirming = State()


class I2VStates(StatesGroup):
    """States for Image-to-Video flow."""
    waiting_image = State()
    waiting_prompt = State()
    waiting_duration = State()
    waiting_audio = State()
    confirming = State()


class MCStates(StatesGroup):
    """States for Motion Control flow."""
    waiting_image = State()
    waiting_video = State()
    waiting_prompt = State()
    waiting_orientation = State()
    waiting_mode = State()
    confirming = State()


# ==================== Helpers ====================

def get_user_lang(user_id: int) -> str:
    """Get user language from database."""
    user = db.get_user(user_id)
    lang = user.get("language_code", "ru") if user else "ru"
    return lang if lang in ("ru", "en") else "ru"


async def upload_file_to_storage(bot: Bot, file_id: str, user_id: int) -> str:
    """
    Download file from Telegram and upload to storage.
    Returns public URL for the file.
    
    TODO: Implement actual file upload to Supabase Storage or other service.
    For now, we use Telegram's file URL which may expire.
    """
    try:
        file = await bot.get_file(file_id)
        # Telegram file URL (expires after some time)
        file_url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file.file_path}"
        return file_url
    except Exception as e:
        logger.error(f"Error getting file URL: {e}")
        raise


async def poll_task_and_send_result(
    bot: Bot,
    chat_id: int,
    task_id: str,
    generation_id: int,
    user_id: int,
    cost: int,
    lang: str
) -> None:
    """
    Poll Kling API for task completion and send result to user.
    Runs as background task.
    """
    max_attempts = 60  # 5 minutes max
    poll_interval = 5  # seconds
    
    for attempt in range(max_attempts):
        try:
            await asyncio.sleep(poll_interval)
            
            response = await kling_client.get_task_status(task_id)
            data = response.get("data", {})
            state = data.get("state")
            
            if state == TaskState.SUCCESS.value:
                # Get result URLs
                result_urls = kling_client.parse_task_result(response)
                if result_urls:
                    video_url = result_urls[0]
                    
                    # Update generation in DB
                    db.update_generation(generation_id, "success", video_url=video_url)
                    
                    # Send video to user
                    await bot.send_message(chat_id, t("generation_success", lang))
                    await bot.send_video(chat_id, video_url)
                    return
                    
            elif state == TaskState.FAIL.value:
                error_msg = data.get("failMsg", "Unknown error")
                
                # Update generation in DB
                db.update_generation(generation_id, "fail", error_message=error_msg)
                
                # Refund balance
                db.update_user_balance(user_id, cost)
                
                # Notify user
                await bot.send_message(
                    chat_id,
                    t("generation_failed", lang, error=error_msg)
                )
                return
                
        except Exception as e:
            logger.error(f"Error polling task {task_id}: {e}")
    
    # Timeout - refund and notify
    db.update_generation(generation_id, "fail", error_message="Timeout")
    db.update_user_balance(user_id, cost)
    await bot.send_message(chat_id, t("generation_failed", lang, error="Timeout"))


# ==================== Mode Selection ====================

@router.message(Command("generate"))
async def cmd_generate(message: Message, state: FSMContext) -> None:
    """Handle /generate command."""
    await state.clear()
    await show_mode_selection(message)


async def show_mode_selection(message: Message) -> None:
    """Show generation mode selection."""
    lang = get_user_lang(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_t2v", lang), callback_data="gen_mode_t2v")],
        [InlineKeyboardButton(text=t("btn_i2v", lang), callback_data="gen_mode_i2v")],
        [InlineKeyboardButton(text=t("btn_mc", lang), callback_data="gen_mode_mc")]
    ])
    
    await message.answer(t("select_mode", lang), reply_markup=keyboard)


@router.callback_query(F.data.startswith("gen_mode_"))
async def callback_gen_mode(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle generation mode selection."""
    mode = callback.data.split("_")[2]  # t2v, i2v, mc
    lang = get_user_lang(callback.from_user.id)
    
    await callback.answer()
    
    if mode == "t2v":
        await callback.message.edit_text(t("t2v_prompt", lang))
        await state.set_state(T2VStates.waiting_prompt)
        
    elif mode == "i2v":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
        ])
        await callback.message.edit_text(t("i2v_image", lang), reply_markup=keyboard)
        await state.set_state(I2VStates.waiting_image)
        
    elif mode == "mc":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
        ])
        await callback.message.edit_text(t("mc_image", lang), reply_markup=keyboard)
        await state.set_state(MCStates.waiting_image)


@router.callback_query(F.data == "gen_cancel")
async def callback_gen_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel generation flow."""
    lang = get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(t("cancelled", lang))
    await callback.answer()


# ==================== T2V Flow ====================

@router.message(T2VStates.waiting_prompt)
async def t2v_prompt_received(message: Message, state: FSMContext) -> None:
    """Handle T2V prompt input."""
    lang = get_user_lang(message.from_user.id)
    
    await state.update_data(prompt=message.text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="16:9", callback_data="t2v_aspect_16:9"),
            InlineKeyboardButton(text="9:16", callback_data="t2v_aspect_9:16"),
            InlineKeyboardButton(text="1:1", callback_data="t2v_aspect_1:1")
        ],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await message.answer(t("t2v_aspect", lang), reply_markup=keyboard)
    await state.set_state(T2VStates.waiting_aspect)


@router.callback_query(F.data.startswith("t2v_aspect_"))
async def t2v_aspect_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle T2V aspect ratio selection."""
    aspect = callback.data.split("_")[2]  # 16:9, 9:16, 1:1
    lang = get_user_lang(callback.from_user.id)
    
    await state.update_data(aspect_ratio=aspect)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 сек", callback_data="t2v_duration_5"),
            InlineKeyboardButton(text="10 сек", callback_data="t2v_duration_10")
        ],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await callback.message.edit_text(t("t2v_duration", lang), reply_markup=keyboard)
    await state.set_state(T2VStates.waiting_duration)
    await callback.answer()


@router.callback_query(F.data.startswith("t2v_duration_"))
async def t2v_duration_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle T2V duration selection."""
    duration = callback.data.split("_")[2]  # 5 or 10
    lang = get_user_lang(callback.from_user.id)
    
    await state.update_data(duration=duration)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_yes", lang), callback_data="t2v_audio_yes"),
            InlineKeyboardButton(text=t("btn_no", lang), callback_data="t2v_audio_no")
        ],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await callback.message.edit_text(t("t2v_audio", lang), reply_markup=keyboard)
    await state.set_state(T2VStates.waiting_audio)
    await callback.answer()


@router.callback_query(F.data.startswith("t2v_audio_"))
async def t2v_audio_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle T2V audio selection and show confirmation."""
    with_audio = callback.data.split("_")[2] == "yes"
    lang = get_user_lang(callback.from_user.id)
    
    await state.update_data(with_audio=with_audio)
    
    # Calculate price
    data = await state.get_data()
    duration = int(data.get("duration", 5))
    cost = KlingPricing.get_t2v_i2v_price(duration, with_audio)
    
    await state.update_data(cost=cost)
    
    # Get user balance
    user = db.get_user(callback.from_user.id)
    balance = user.get("balance", 0)
    
    # Build details string
    details = (
        f"🎥 Text to Video\n"
        f"📐 {data.get('aspect_ratio', '16:9')}\n"
        f"⏱ {duration} сек\n"
        f"🔊 {'Да' if with_audio else 'Нет'}"
    )
    
    if balance < cost:
        await callback.message.edit_text(
            t("insufficient_balance", lang, cost=cost, balance=balance)
        )
        await state.clear()
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_confirm", lang), callback_data="t2v_confirm")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await callback.message.edit_text(
        t("confirm_generation", lang, details=details, cost=cost, balance=balance),
        reply_markup=keyboard
    )
    await state.set_state(T2VStates.confirming)
    await callback.answer()


@router.callback_query(F.data == "t2v_confirm", T2VStates.confirming)
async def t2v_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm and start T2V generation."""
    lang = get_user_lang(callback.from_user.id)
    data = await state.get_data()
    
    prompt = data.get("prompt", "")
    aspect_ratio = data.get("aspect_ratio", "16:9")
    duration = data.get("duration", "5")
    with_audio = data.get("with_audio", False)
    cost = data.get("cost", 55)
    
    # Deduct balance
    if not db.deduct_balance(callback.from_user.id, cost):
        await callback.message.edit_text(
            t("insufficient_balance", lang, cost=cost, balance=0)
        )
        await state.clear()
        await callback.answer()
        return
    
    # Build callback URL
    callback_url = f"{settings.webhook_url}/callback/kling" if settings.webhook_url else None
    
    try:
        # Create task
        response = await kling_client.create_text_to_video(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            sound=with_audio,
            callback_url=callback_url
        )
        
        task_id = response.get("data", {}).get("taskId")
        
        if not task_id:
            raise Exception("No taskId in response")
        
        # Create generation record
        generation = db.create_generation(
            user_id=callback.from_user.id,
            prompt=prompt,
            model=KlingModel.TEXT_TO_VIDEO.value,
            provider_task_id=task_id,
            cost=cost,
            video_duration=float(duration),
            video_resolution=aspect_ratio
        )
        
        await callback.message.edit_text(t("generation_started", lang))
        await state.clear()
        await callback.answer()
        
        # Start polling in background
        if generation:
            asyncio.create_task(
                poll_task_and_send_result(
                    callback.bot,
                    callback.message.chat.id,
                    task_id,
                    generation["id"],
                    callback.from_user.id,
                    cost,
                    lang
                )
            )
        
    except Exception as e:
        logger.error(f"Error creating T2V task: {e}")
        # Refund on error
        db.update_user_balance(callback.from_user.id, cost)
        await callback.message.edit_text(t("error_generic", lang))
        await state.clear()
        await callback.answer()


# ==================== I2V Flow ====================

@router.message(I2VStates.waiting_image, F.photo)
async def i2v_image_received(message: Message, state: FSMContext) -> None:
    """Handle I2V image upload."""
    lang = get_user_lang(message.from_user.id)
    
    # Get largest photo size
    photo = message.photo[-1]
    
    try:
        image_url = await upload_file_to_storage(message.bot, photo.file_id, message.from_user.id)
        await state.update_data(image_url=image_url)
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        await message.answer(t("error_invalid_image", lang))
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_skip", lang), callback_data="i2v_prompt_skip")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await message.answer(t("i2v_prompt", lang), reply_markup=keyboard)
    await state.set_state(I2VStates.waiting_prompt)


@router.message(I2VStates.waiting_prompt)
async def i2v_prompt_received(message: Message, state: FSMContext) -> None:
    """Handle I2V prompt input."""
    lang = get_user_lang(message.from_user.id)
    
    await state.update_data(prompt=message.text)
    await show_i2v_duration(message, state, lang)


@router.callback_query(F.data == "i2v_prompt_skip")
async def i2v_prompt_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip I2V prompt."""
    lang = get_user_lang(callback.from_user.id)
    await state.update_data(prompt="")
    await show_i2v_duration(callback.message, state, lang, edit=True)
    await callback.answer()


async def show_i2v_duration(message: Message, state: FSMContext, lang: str, edit: bool = False) -> None:
    """Show I2V duration selection."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 сек", callback_data="i2v_duration_5"),
            InlineKeyboardButton(text="10 сек", callback_data="i2v_duration_10")
        ],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    if edit:
        await message.edit_text(t("t2v_duration", lang), reply_markup=keyboard)
    else:
        await message.answer(t("t2v_duration", lang), reply_markup=keyboard)
    
    await state.set_state(I2VStates.waiting_duration)


@router.callback_query(F.data.startswith("i2v_duration_"))
async def i2v_duration_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle I2V duration selection."""
    duration = callback.data.split("_")[2]
    lang = get_user_lang(callback.from_user.id)
    
    await state.update_data(duration=duration)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_yes", lang), callback_data="i2v_audio_yes"),
            InlineKeyboardButton(text=t("btn_no", lang), callback_data="i2v_audio_no")
        ],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await callback.message.edit_text(t("t2v_audio", lang), reply_markup=keyboard)
    await state.set_state(I2VStates.waiting_audio)
    await callback.answer()


@router.callback_query(F.data.startswith("i2v_audio_"))
async def i2v_audio_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle I2V audio selection and show confirmation."""
    with_audio = callback.data.split("_")[2] == "yes"
    lang = get_user_lang(callback.from_user.id)
    
    await state.update_data(with_audio=with_audio)
    
    data = await state.get_data()
    duration = int(data.get("duration", 5))
    cost = KlingPricing.get_t2v_i2v_price(duration, with_audio)
    
    await state.update_data(cost=cost)
    
    user = db.get_user(callback.from_user.id)
    balance = user.get("balance", 0)
    
    details = (
        f"🖼 Image to Video\n"
        f"⏱ {duration} сек\n"
        f"🔊 {'Да' if with_audio else 'Нет'}"
    )
    
    if balance < cost:
        await callback.message.edit_text(
            t("insufficient_balance", lang, cost=cost, balance=balance)
        )
        await state.clear()
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_confirm", lang), callback_data="i2v_confirm")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await callback.message.edit_text(
        t("confirm_generation", lang, details=details, cost=cost, balance=balance),
        reply_markup=keyboard
    )
    await state.set_state(I2VStates.confirming)
    await callback.answer()


@router.callback_query(F.data == "i2v_confirm", I2VStates.confirming)
async def i2v_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm and start I2V generation."""
    lang = get_user_lang(callback.from_user.id)
    data = await state.get_data()
    
    image_url = data.get("image_url", "")
    prompt = data.get("prompt", "")
    duration = data.get("duration", "5")
    with_audio = data.get("with_audio", False)
    cost = data.get("cost", 55)
    
    if not db.deduct_balance(callback.from_user.id, cost):
        await callback.message.edit_text(
            t("insufficient_balance", lang, cost=cost, balance=0)
        )
        await state.clear()
        await callback.answer()
        return
    
    callback_url = f"{settings.webhook_url}/callback/kling" if settings.webhook_url else None
    
    try:
        response = await kling_client.create_image_to_video(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            sound=with_audio,
            callback_url=callback_url
        )
        
        task_id = response.get("data", {}).get("taskId")
        
        if not task_id:
            raise Exception("No taskId in response")
        
        generation = db.create_generation(
            user_id=callback.from_user.id,
            prompt=prompt,
            model=KlingModel.IMAGE_TO_VIDEO.value,
            provider_task_id=task_id,
            cost=cost,
            input_images=[image_url],
            video_duration=float(duration)
        )
        
        await callback.message.edit_text(t("generation_started", lang))
        await state.clear()
        await callback.answer()
        
        if generation:
            asyncio.create_task(
                poll_task_and_send_result(
                    callback.bot,
                    callback.message.chat.id,
                    task_id,
                    generation["id"],
                    callback.from_user.id,
                    cost,
                    lang
                )
            )
        
    except Exception as e:
        logger.error(f"Error creating I2V task: {e}")
        db.update_user_balance(callback.from_user.id, cost)
        await callback.message.edit_text(t("error_generic", lang))
        await state.clear()
        await callback.answer()


# ==================== Motion Control Flow ====================

@router.message(MCStates.waiting_image, F.photo)
async def mc_image_received(message: Message, state: FSMContext) -> None:
    """Handle MC source image upload."""
    lang = get_user_lang(message.from_user.id)
    
    photo = message.photo[-1]
    
    try:
        image_url = await upload_file_to_storage(message.bot, photo.file_id, message.from_user.id)
        await state.update_data(image_url=image_url)
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        await message.answer(t("error_invalid_image", lang))
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await message.answer(t("mc_video", lang), reply_markup=keyboard)
    await state.set_state(MCStates.waiting_video)


@router.message(MCStates.waiting_video, F.video)
async def mc_video_received(message: Message, state: FSMContext) -> None:
    """Handle MC reference video upload."""
    lang = get_user_lang(message.from_user.id)
    video = message.video
    
    # Validate video duration
    duration = video.duration or 0
    
    if duration < 3:
        await message.answer(t("error_video_too_short", lang))
        return
    
    if duration > 30:
        await message.answer(t("error_video_too_long", lang))
        return
    
    try:
        video_url = await upload_file_to_storage(message.bot, video.file_id, message.from_user.id)
        await state.update_data(video_url=video_url, video_duration=duration)
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        await message.answer(t("error_invalid_video", lang))
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_skip", lang), callback_data="mc_prompt_skip")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await message.answer(t("mc_prompt", lang), reply_markup=keyboard)
    await state.set_state(MCStates.waiting_prompt)


@router.message(MCStates.waiting_prompt)
async def mc_prompt_received(message: Message, state: FSMContext) -> None:
    """Handle MC prompt input."""
    lang = get_user_lang(message.from_user.id)
    await state.update_data(prompt=message.text)
    await show_mc_orientation(message, state, lang)


@router.callback_query(F.data == "mc_prompt_skip")
async def mc_prompt_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip MC prompt."""
    lang = get_user_lang(callback.from_user.id)
    await state.update_data(prompt="")
    await show_mc_orientation(callback.message, state, lang, edit=True)
    await callback.answer()


async def show_mc_orientation(message: Message, state: FSMContext, lang: str, edit: bool = False) -> None:
    """Show MC orientation selection."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_orient_image", lang), callback_data="mc_orient_image"),
            InlineKeyboardButton(text=t("btn_orient_video", lang), callback_data="mc_orient_video")
        ],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    if edit:
        await message.edit_text(t("mc_orientation", lang), reply_markup=keyboard)
    else:
        await message.answer(t("mc_orientation", lang), reply_markup=keyboard)
    
    await state.set_state(MCStates.waiting_orientation)


@router.callback_query(F.data.startswith("mc_orient_"))
async def mc_orientation_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle MC orientation selection."""
    orientation = callback.data.split("_")[2]  # image or video
    lang = get_user_lang(callback.from_user.id)
    
    await state.update_data(orientation=orientation)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="720p", callback_data="mc_mode_720p"),
            InlineKeyboardButton(text="1080p", callback_data="mc_mode_1080p")
        ],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await callback.message.edit_text(t("mc_mode", lang), reply_markup=keyboard)
    await state.set_state(MCStates.waiting_mode)
    await callback.answer()


@router.callback_query(F.data.startswith("mc_mode_"))
async def mc_mode_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle MC mode selection and show confirmation."""
    mode = callback.data.split("_")[2]  # 720p or 1080p
    lang = get_user_lang(callback.from_user.id)
    
    await state.update_data(mode=mode)
    
    data = await state.get_data()
    video_duration = data.get("video_duration", 5)
    cost = KlingPricing.get_motion_control_price(video_duration, mode)
    
    await state.update_data(cost=cost)
    
    user = db.get_user(callback.from_user.id)
    balance = user.get("balance", 0)
    
    orientation_text = "Как на фото" if data.get("orientation") == "image" else "Как в видео"
    
    details = (
        f"💃 Motion Control\n"
        f"⏱ {video_duration} сек\n"
        f"🔄 {orientation_text}\n"
        f"📺 {mode}"
    )
    
    if balance < cost:
        await callback.message.edit_text(
            t("insufficient_balance", lang, cost=cost, balance=balance)
        )
        await state.clear()
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_confirm", lang), callback_data="mc_confirm")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="gen_cancel")]
    ])
    
    await callback.message.edit_text(
        t("confirm_generation", lang, details=details, cost=cost, balance=balance),
        reply_markup=keyboard
    )
    await state.set_state(MCStates.confirming)
    await callback.answer()


@router.callback_query(F.data == "mc_confirm", MCStates.confirming)
async def mc_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm and start Motion Control generation."""
    lang = get_user_lang(callback.from_user.id)
    data = await state.get_data()
    
    image_url = data.get("image_url", "")
    video_url = data.get("video_url", "")
    prompt = data.get("prompt", "")
    orientation = data.get("orientation", "video")
    mode = data.get("mode", "720p")
    video_duration = data.get("video_duration", 5)
    cost = data.get("cost", 30)
    
    if not db.deduct_balance(callback.from_user.id, cost):
        await callback.message.edit_text(
            t("insufficient_balance", lang, cost=cost, balance=0)
        )
        await state.clear()
        await callback.answer()
        return
    
    callback_url = f"{settings.webhook_url}/callback/kling" if settings.webhook_url else None
    
    try:
        response = await kling_client.create_motion_control(
            input_image_url=image_url,
            video_url=video_url,
            prompt=prompt,
            character_orientation=orientation,
            mode=mode,
            callback_url=callback_url
        )
        
        task_id = response.get("data", {}).get("taskId")
        
        if not task_id:
            raise Exception("No taskId in response")
        
        generation = db.create_generation(
            user_id=callback.from_user.id,
            prompt=prompt,
            model=KlingModel.MOTION_CONTROL.value,
            provider_task_id=task_id,
            cost=cost,
            input_images=[image_url],
            video_duration=float(video_duration),
            video_resolution=mode
        )
        
        await callback.message.edit_text(t("generation_started", lang))
        await state.clear()
        await callback.answer()
        
        if generation:
            asyncio.create_task(
                poll_task_and_send_result(
                    callback.bot,
                    callback.message.chat.id,
                    task_id,
                    generation["id"],
                    callback.from_user.id,
                    cost,
                    lang
                )
            )
        
    except Exception as e:
        logger.error(f"Error creating MC task: {e}")
        db.update_user_balance(callback.from_user.id, cost)
        await callback.message.edit_text(t("error_generic", lang))
        await state.clear()
        await callback.answer()
