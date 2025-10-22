import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import json
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class SocialPosterService:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def post_to_all_platforms(self, video_url: str, prompt: str, video_id: int, db) -> Dict[str, str]:
        """Post video to all configured social media platforms."""
        platform_urls = {}

        # Post to YouTube
        try:
            youtube_url = await self._post_to_youtube(video_url, prompt, video_id)
            if youtube_url:
                platform_urls["youtube"] = youtube_url
        except Exception as e:
            logger.error(f"YouTube posting failed: {e}")

        # Post to TikTok
        try:
            tiktok_url = await self._post_to_tiktok(video_url, prompt, video_id)
            if tiktok_url:
                platform_urls["tiktok"] = tiktok_url
        except Exception as e:
            logger.error(f"TikTok posting failed: {e}")

        # Post to Instagram
        try:
            instagram_url = await self._post_to_instagram(video_url, prompt, video_id)
            if instagram_url:
                platform_urls["instagram"] = instagram_url
        except Exception as e:
            logger.error(f"Instagram posting failed: {e}")

        # Post to Facebook
        try:
            facebook_url = await self._post_to_facebook(video_url, prompt, video_id)
            if facebook_url:
                platform_urls["facebook"] = facebook_url
        except Exception as e:
            logger.error(f"Facebook posting failed: {e}")

        return platform_urls

    async def _post_to_youtube(self, video_url: str, prompt: str, video_id: int) -> Optional[str]:
        """Post video to YouTube Shorts."""
        if not hasattr(settings, 'youtube_api_key') or not settings.youtube_api_key:
            return None

        try:
            # Download video file
            video_path = f"/tmp/video_{video_id}.mp4"
            await self._download_video(video_url, video_path)

            # Authenticate with YouTube
            creds = self._get_youtube_credentials()
            youtube = build('youtube', 'v3', credentials=creds)

            # Prepare video metadata
            title = f"Viral Video #{video_id} - {prompt[:50]}..."
            description = f"Amazing viral content! {prompt}\n\n#viral #video #trending"
            tags = ["viral", "video", "trending", "shorts"]

            # Upload video
            request = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                        "tags": tags,
                        "categoryId": "22"  # People & Blogs
                    },
                    "status": {
                        "privacyStatus": "public",
                        "madeForKids": False
                    }
                },
                media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
            )

            response = request.execute()
            video_id_yt = response['id']

            # Clean up
            os.remove(video_path)

            return f"https://www.youtube.com/shorts/{video_id_yt}"

        except Exception as e:
            logger.error(f"YouTube posting error: {e}")
            return None

    def _get_youtube_credentials(self):
        """Get YouTube OAuth credentials."""
        creds = None
        token_path = 'token.pickle'

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secrets.json',
                    ['https://www.googleapis.com/auth/youtube.upload']
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        return creds

    async def _post_to_tiktok(self, video_url: str, prompt: str, video_id: int) -> Optional[str]:
        """Post video to TikTok."""
        if not hasattr(settings, 'tiktok_access_token') or not settings.tiktok_access_token:
            return None

        try:
            # Download video
            video_path = f"/tmp/tiktok_video_{video_id}.mp4"
            await self._download_video(video_url, video_path)

            # TikTok Content Posting API
            url = "https://open-api.tiktok.com/share/video/upload/"
            headers = {
                "Authorization": f"Bearer {settings.tiktok_access_token}",
                "Content-Type": "application/json"
            }

            # Upload video first
            with open(video_path, 'rb') as f:
                video_data = f.read()

            upload_data = {
                "video": video_data,
                "title": f"Viral TikTok #{video_id}",
                "description": prompt[:200],
                "privacy_level": "public"
            }

            async with self.session.post(url, headers=headers, data=upload_data) as response:
                if response.status != 200:
                    raise Exception(f"TikTok upload failed: {response.status}")
                upload_result = await response.json()
                video_id_tt = upload_result["data"]["video_id"]

            # Post the video
            post_url = "https://open-api.tiktok.com/share/video/publish/"
            post_data = {
                "video_id": video_id_tt,
                "text": f"🔥 {prompt[:100]}... #viral #tiktok",
                "music_id": "auto",  # Use trending music
                "effects": ["trending_effect"]
            }

            async with self.session.post(post_url, headers=headers, json=post_data) as response:
                if response.status != 200:
                    raise Exception(f"TikTok posting failed: {response.status}")
                post_result = await response.json()
                share_id = post_result["data"]["share_id"]

            # Clean up
            os.remove(video_path)

            return f"https://www.tiktok.com/@youraccount/video/{share_id}"

        except Exception as e:
            logger.error(f"TikTok posting error: {e}")
            return None

    async def _post_to_instagram(self, video_url: str, prompt: str, video_id: int) -> Optional[str]:
        """Post video to Instagram Reels."""
        if not hasattr(settings, 'instagram_access_token') or not settings.instagram_access_token:
            return None

        try:
            # Instagram Graph API
            url = f"https://graph.instagram.com/me/media"
            params = {
                "access_token": settings.instagram_access_token,
                "media_type": "REELS",
                "video_url": video_url,  # Instagram can accept URLs
                "caption": f"🎬 {prompt[:100]}...\n\n#reels #viral #instagram",
                "share_to_feed": "true"
            }

            async with self.session.post(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Instagram posting failed: {response.status}")
                result = await response.json()
                media_id = result["id"]

            # Publish the media
            publish_url = f"https://graph.instagram.com/{media_id}/publish"
            publish_params = {
                "access_token": settings.instagram_access_token
            }

            async with self.session.post(publish_url, params=publish_params) as response:
                if response.status != 200:
                    raise Exception(f"Instagram publishing failed: {response.status}")
                publish_result = await response.json()
                post_id = publish_result["id"]

            return f"https://www.instagram.com/reel/{post_id}/"

        except Exception as e:
            logger.error(f"Instagram posting error: {e}")
            return None

    async def _post_to_facebook(self, video_url: str, prompt: str, video_id: int) -> Optional[str]:
        """Post video to Facebook."""
        # Facebook Graph API implementation
        try:
            # Download video
            video_path = f"/tmp/facebook_video_{video_id}.mp4"
            await self._download_video(video_url, video_path)

            # Facebook API endpoint
            url = f"https://graph.facebook.com/v18.0/me/videos"
            params = {
                "access_token": getattr(settings, 'facebook_access_token', ''),
                "description": f"🎥 {prompt[:200]}... #viral #facebook",
                "title": f"Viral Video #{video_id}"
            }

            # Upload video file
            with open(video_path, 'rb') as f:
                video_data = f.read()

            # Facebook requires multipart form data
            data = aiohttp.FormData()
            data.add_field('source', video_data, filename=f'video_{video_id}.mp4')
            data.add_field('description', f"🎥 {prompt[:200]}... #viral #facebook")
            data.add_field('title', f"Viral Video #{video_id}")

            headers = {
                "Authorization": f"Bearer {getattr(settings, 'facebook_access_token', '')}"
            }

            async with self.session.post(url, headers=headers, data=data) as response:
                if response.status != 200:
                    raise Exception(f"Facebook posting failed: {response.status}")
                result = await response.json()
                post_id = result["id"]

            # Clean up
            os.remove(video_path)

            return f"https://www.facebook.com/watch/?v={post_id}"

        except Exception as e:
            logger.error(f"Facebook posting error: {e}")
            return None

    async def _download_video(self, video_url: str, save_path: str):
        """Download video from URL to local file."""
        async with self.session.get(video_url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download video: {response.status}")

            with open(save_path, 'wb') as f:
                f.write(await response.read())

    async def get_platform_analytics(self, platform: str, post_id: str) -> Dict[str, int]:
        """Get analytics for a posted video."""
        if platform == "youtube":
            return await self._get_youtube_analytics(post_id)
        elif platform == "tiktok":
            return await self._get_tiktok_analytics(post_id)
        elif platform == "instagram":
            return await self._get_instagram_analytics(post_id)
        elif platform == "facebook":
            return await self._get_facebook_analytics(post_id)
        else:
            return {"views": 0, "likes": 0, "shares": 0}

    async def _get_youtube_analytics(self, video_id: str) -> Dict[str, int]:
        """Get YouTube video analytics."""
        try:
            creds = self._get_youtube_credentials()
            youtube = build('youtube', 'v3', credentials=creds)

            request = youtube.videos().list(
                part="statistics",
                id=video_id
            )
            response = request.execute()

            if response['items']:
                stats = response['items'][0]['statistics']
                return {
                    "views": int(stats.get('viewCount', 0)),
                    "likes": int(stats.get('likeCount', 0)),
                    "shares": int(stats.get('shareCount', 0))
                }
        except Exception as e:
            logger.error(f"YouTube analytics error: {e}")

        return {"views": 0, "likes": 0, "shares": 0}

    async def _get_tiktok_analytics(self, video_id: str) -> Dict[str, int]:
        """Get TikTok video analytics."""
        try:
            url = f"https://open-api.tiktok.com/research/video/query/?video_id={video_id}"
            headers = {
                "Authorization": f"Bearer {getattr(settings, 'tiktok_access_token', '')}"
            }

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "views": data.get("view_count", 0),
                        "likes": data.get("like_count", 0),
                        "shares": data.get("share_count", 0)
                    }
        except Exception as e:
            logger.error(f"TikTok analytics error: {e}")

        return {"views": 0, "likes": 0, "shares": 0}

    async def _get_instagram_analytics(self, media_id: str) -> Dict[str, int]:
        """Get Instagram media analytics."""
        try:
            url = f"https://graph.instagram.com/{media_id}/insights"
            params = {
                "access_token": getattr(settings, 'instagram_access_token', ''),
                "metric": "impressions,reach,engagement"
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "views": data.get("impressions", 0),
                        "likes": data.get("engagement", 0),
                        "shares": data.get("reach", 0)
                    }
        except Exception as e:
            logger.error(f"Instagram analytics error: {e}")

        return {"views": 0, "likes": 0, "shares": 0}

    async def _get_facebook_analytics(self, post_id: str) -> Dict[str, int]:
        """Get Facebook video analytics."""
        try:
            url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
            params = {
                "access_token": getattr(settings, 'facebook_access_token', ''),
                "metric": "post_impressions,post_engaged_users"
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "views": data.get("post_impressions", 0),
                        "likes": data.get("post_engaged_users", 0),
                        "shares": 0  # Facebook doesn't provide shares in basic API
                    }
        except Exception as e:
            logger.error(f"Facebook analytics error: {e}")

        return {"views": 0, "likes": 0, "shares": 0}