"""
Cloudflare R2 Storage utility for video uploads.
Uses S3-compatible API via boto3.
"""

import logging
from typing import Optional
import boto3
from botocore.config import Config

from config import settings

logger = logging.getLogger(__name__)


class R2Storage:
    """Client for Cloudflare R2 storage operations."""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        """Lazy-initialize S3 client for R2."""
        if self._client is None:
            if not settings.r2_video_account_id:
                raise ValueError("R2_VIDEO_ACCOUNT_ID is not configured")
            
            self._client = boto3.client(
                's3',
                endpoint_url=f"https://{settings.r2_video_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.r2_video_access_key_id,
                aws_secret_access_key=settings.r2_video_secret_access_key,
                config=Config(signature_version='s3v4'),
                region_name='auto'
            )
        return self._client
    
    def upload_video(self, local_path: str, object_key: str) -> str:
        """
        Upload video file to R2 bucket.
        
        Args:
            local_path: Path to local video file
            object_key: Object key (filename) in R2 bucket
        
        Returns:
            Public URL of the uploaded video
        """
        try:
            self.client.upload_file(
                local_path,
                settings.r2_bucket_video_refs,
                object_key,
                ExtraArgs={'ContentType': 'video/mp4'}
            )
            
            public_url = f"{settings.r2_public_url_video_refs}/{object_key}"
            logger.info(f"Uploaded video to R2: {object_key}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload video to R2: {e}")
            raise
    
    def delete_video(self, object_key: str) -> bool:
        """
        Delete video from R2 bucket.
        
        Args:
            object_key: Object key (filename) in R2 bucket
        
        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_object(
                Bucket=settings.r2_bucket_video_refs,
                Key=object_key
            )
            logger.info(f"Deleted video from R2: {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete video from R2: {e}")
            return False


# Global R2 storage instance
r2_storage = R2Storage()
