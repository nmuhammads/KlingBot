"""
Video processing utility for upscaling low-resolution videos.
Uses FFmpeg for video manipulation.
"""

import logging
import os
import tempfile
import uuid
import subprocess
import asyncio
from typing import Tuple, Optional

import httpx
import aiofiles

from config import settings
from utils.r2_storage import r2_storage

logger = logging.getLogger(__name__)

MIN_RESOLUTION = 720


def get_video_resolution(video_path: str) -> Tuple[int, int]:
    """
    Get video resolution using ffprobe.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Tuple of (width, height)
    """
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0',
                video_path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        output = result.stdout.strip()
        if 'x' in output:
            width, height = map(int, output.split('x'))
            return width, height
        else:
            logger.error(f"Failed to parse resolution: {output}")
            return 0, 0
            
    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe error: {e.stderr}")
        return 0, 0
    except Exception as e:
        logger.error(f"Error getting video resolution: {e}")
        return 0, 0


def upscale_video(input_path: str, output_path: str, target_min: int = MIN_RESOLUTION) -> bool:
    """
    Upscale video to meet minimum resolution requirement.
    Preserves aspect ratio.
    
    Args:
        input_path: Path to input video
        output_path: Path for output video
        target_min: Minimum dimension (width or height)
    
    Returns:
        True if successful
    """
    try:
        # Scale filter: if width < height, set height to target_min
        # Otherwise set width to target_min
        # -2 ensures even number for encoding compatibility
        scale_filter = f"scale='if(gt(iw,ih),{target_min},-2)':'if(gt(iw,ih),-2,{target_min})'"
        
        result = subprocess.run(
            [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', scale_filter,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'copy',
                output_path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"Upscaled video to {target_min}p: {output_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg upscale error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error upscaling video: {e}")
        return False


async def download_video(url: str, dest_path: str) -> bool:
    """
    Download video from URL to local path.
    
    Args:
        url: Video URL
        dest_path: Destination file path
    
    Returns:
        True if successful
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            async with aiofiles.open(dest_path, 'wb') as f:
                await f.write(response.content)
        
        logger.info(f"Downloaded video: {dest_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return False


async def process_video_for_api(
    telegram_file_url: str,
    user_id: int
) -> Tuple[Optional[str], Optional[str]]:
    """
    Process video for Kling API: download, check resolution, upscale if needed, upload to R2.
    
    Args:
        telegram_file_url: Original Telegram file URL
        user_id: User ID for generating unique filename
    
    Returns:
        Tuple of (public_url, r2_object_key) or (None, None) on error.
        If video doesn't need upscaling, returns (telegram_file_url, None).
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        input_path = os.path.join(temp_dir, f"input_{unique_id}.mp4")
        output_path = os.path.join(temp_dir, f"output_{unique_id}.mp4")
        
        # Download video from Telegram
        if not await download_video(telegram_file_url, input_path):
            logger.error("Failed to download video from Telegram")
            return None, None
        
        # Check resolution
        width, height = get_video_resolution(input_path)
        
        if width == 0 or height == 0:
            logger.error("Could not determine video resolution")
            return None, None
        
        min_dim = min(width, height)
        
        # If resolution is already >= 720, use original Telegram URL
        if min_dim >= MIN_RESOLUTION:
            logger.info(f"Video resolution {width}x{height} is sufficient, using original URL")
            return telegram_file_url, None
        
        # Upscale video
        logger.info(f"Video resolution {width}x{height} is below {MIN_RESOLUTION}, upscaling...")
        
        if not upscale_video(input_path, output_path, MIN_RESOLUTION):
            logger.error("Failed to upscale video")
            return None, None
        
        # Upload to R2
        r2_key = f"{user_id}/{unique_id}.mp4"
        
        # Run upload in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        public_url = await loop.run_in_executor(
            None,
            r2_storage.upload_video,
            output_path,
            r2_key
        )
        
        logger.info(f"Video processed and uploaded: {public_url}")
        return public_url, r2_key
        
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return None, None
        
    finally:
        # Cleanup temp files
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")


async def cleanup_r2_video(r2_key: Optional[str]) -> None:
    """
    Delete video from R2 storage.
    
    Args:
        r2_key: R2 object key to delete (can be None)
    """
    if not r2_key:
        return
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            r2_storage.delete_video,
            r2_key
        )
        logger.info(f"Cleaned up R2 video: {r2_key}")
    except Exception as e:
        logger.error(f"Failed to cleanup R2 video {r2_key}: {e}")
