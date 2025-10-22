import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import re
from backend.app.core.config import settings
from backend.app.db.models.user import Trend
from sqlalchemy.ext.asyncio import AsyncSession
import os
from newsapi import NewsApiClient
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

class ViralTrendFinder:
    def __init__(self):
        self.session = None
        self.news_api = NewsApiClient(api_key=os.getenv('NEWS_API_KEY', 'demo'))
        self.pytrends = TrendReq(hl='en-US', tz=360)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def find_trending_topics(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Find trending topics from multiple platforms."""
        trends = []

        # Get news API trending topics
        try:
            news_trends = await self._get_news_api_trends()
            trends.extend(news_trends)
        except Exception as e:
            logger.error(f"News API trending failed: {e}")

        # Get Google Trends
        try:
            google_trends = await self._get_google_trends()
            trends.extend(google_trends)
        except Exception as e:
            logger.error(f"Google Trends failed: {e}")

        # Get YouTube trending
        try:
            youtube_trends = await self._get_youtube_trending()
            trends.extend(youtube_trends)
        except Exception as e:
            logger.error(f"YouTube trending failed: {e}")

        # Get TikTok trending
        try:
            tiktok_trends = await self._get_tiktok_trending()
            trends.extend(tiktok_trends)
        except Exception as e:
            logger.error(f"TikTok trending failed: {e}")

        # Get Twitter trending
        try:
            twitter_trends = await self._get_twitter_trending()
            trends.extend(twitter_trends)
        except Exception as e:
            logger.error(f"Twitter trending failed: {e}")

        # Calculate virality scores and save to database
        processed_trends = await self._process_and_save_trends(trends, db)

        return processed_trends

    async def _get_news_api_trends(self) -> List[Dict[str, Any]]:
        """Get trending topics from News API."""
        try:
            # Get top headlines
            top_headlines = self.news_api.get_top_headlines(
                language='en',
                page_size=20
            )

            trends = []
            for article in top_headlines.get('articles', []):
                trend = {
                    "platform": "news",
                    "trend_name": article.get('title', ''),
                    "description": article.get('description', '') or article.get('content', ''),
                    "hashtags": self._extract_hashtags(article.get('title', '') + " " + (article.get('description') or '')),
                    "view_count": 0,  # News doesn't have views
                    "engagement_rate": 0.0,
                    "category": "news",
                    "source": article.get('source', {}).get('name', ''),
                    "url": article.get('url', ''),
                    "published_at": article.get('publishedAt', '')
                }
                trends.append(trend)

            return trends
        except Exception as e:
            logger.error(f"News API error: {e}")
            return []

    async def _get_google_trends(self) -> List[Dict[str, Any]]:
        """Get trending searches from Google Trends."""
        try:
            # Get trending searches
            trending_searches_df = self.pytrends.trending_searches(pn='united_states')

            trends = []
            for _, row in trending_searches_df.head(10).iterrows():
                trend_name = str(row[0])
                trend = {
                    "platform": "google",
                    "trend_name": trend_name,
                    "description": f"Trending search on Google: {trend_name}",
                    "hashtags": [],
                    "search_volume": 100,  # High volume for trending
                    "category": "search",
                    "query": trend_name
                }
                trends.append(trend)

            return trends
        except Exception as e:
            logger.error(f"Google Trends error: {e}")
            return []

    async def _get_youtube_trending(self) -> List[Dict[str, Any]]:
        """Get trending videos from YouTube."""
        if not hasattr(settings, 'youtube_api_key') or not settings.youtube_api_key:
            return []

        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": "US",
            "maxResults": 20,
            "key": settings.youtube_api_key
        }

        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"YouTube API error: {response.status}")

            data = await response.json()
            trends = []

            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                trend = {
                    "platform": "youtube",
                    "trend_name": snippet.get("title", ""),
                    "description": snippet.get("description", "")[:500],
                    "hashtags": self._extract_hashtags(snippet.get("title", "") + " " + snippet.get("description", "")),
                    "view_count": int(stats.get("viewCount", 0)),
                    "engagement_rate": self._calculate_engagement_rate(stats),
                    "category": snippet.get("categoryId", ""),
                    "video_id": item.get("id", ""),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                }
                trends.append(trend)

            return trends

    async def _get_tiktok_trending(self) -> List[Dict[str, Any]]:
        """Get trending sounds and hashtags from TikTok."""
        if not hasattr(settings, 'tiktok_access_token') or not settings.tiktok_access_token:
            return []

        # TikTok Research API
        url = "https://open-api.tiktok.com/research/trending/sounds/"
        headers = {
            "Authorization": f"Bearer {settings.tiktok_access_token}"
        }
        params = {
            "period": "day",
            "limit": 10
        }

        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise Exception(f"TikTok API error: {response.status}")

            data = await response.json()
            trends = []

            for item in data.get("data", []):
                trend = {
                    "platform": "tiktok",
                    "trend_name": item.get("sound_name", ""),
                    "description": f"Trending sound: {item.get('sound_name', '')}",
                    "hashtags": [f"#{item.get('sound_name', '').replace(' ', '')}"],
                    "view_count": item.get("view_count", 0),
                    "engagement_rate": item.get("engagement_rate", 0.0),
                    "category": "music",
                    "sound_id": item.get("sound_id", ""),
                    "creator": item.get("creator_username", "")
                }
                trends.append(trend)

            return trends

    async def _get_twitter_trending(self) -> List[Dict[str, Any]]:
        """Get trending topics from Twitter."""
        if not all([hasattr(settings, attr) and getattr(settings, attr) for attr in
                   ['twitter_api_key', 'twitter_api_secret', 'twitter_access_token', 'twitter_access_token_secret']]):
            return []

        # Twitter API v2
        url = "https://api.twitter.com/2/trends/place.json"
        headers = {
            "Authorization": f"Bearer {settings.twitter_api_key}"
        }
        params = {
            "id": 1  # Worldwide
        }

        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise Exception(f"Twitter API error: {response.status}")

            data = await response.json()
            trends = []

            for trend in data[0].get("trends", [])[:10]:
                trend_data = {
                    "platform": "twitter",
                    "trend_name": trend.get("name", ""),
                    "description": f"Trending on Twitter: {trend.get('name', '')}",
                    "hashtags": [trend.get("name", "")] if trend.get("name", "").startswith("#") else [],
                    "tweet_volume": trend.get("tweet_volume", 0),
                    "category": "social",
                    "query": trend.get("query", "")
                }
                trends.append(trend_data)

            return trends

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        hashtags = re.findall(r'#\w+', text)
        return list(set(hashtags))  # Remove duplicates

    def _calculate_engagement_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate engagement rate from video statistics."""
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        if views == 0:
            return 0.0

        return ((likes + comments) / views) * 100

    async def _process_and_save_trends(self, trends: List[Dict[str, Any]], db: AsyncSession) -> List[Dict[str, Any]]:
        """Process trends, calculate virality scores, and save to database."""
        processed_trends = []

        for trend_data in trends:
            # Calculate virality score
            virality_score = self._calculate_virality_score(trend_data)

            # Create or update trend in database
            trend = Trend(
                platform=trend_data["platform"],
                trend_name=trend_data["trend_name"][:255],
                description=trend_data.get("description", ""),
                hashtags=trend_data.get("hashtags", []),
                virality_score=virality_score,
                view_count=trend_data.get("view_count", 0),
                engagement_rate=trend_data.get("engagement_rate", 0.0),
                category=trend_data.get("category", ""),
                is_active=True
            )

            db.add(trend)
            processed_trends.append({
                "id": trend.id,
                "platform": trend.platform,
                "trend_name": trend.trend_name,
                "virality_score": virality_score,
                "hashtags": trend.hashtags,
                "description": trend.description
            })

        await db.commit()
        return processed_trends

    def _calculate_virality_score(self, trend_data: Dict[str, Any]) -> float:
        """Calculate virality score based on various metrics."""
        score = 0.0

        # Platform weights
        platform_weights = {
            "youtube": 1.0,
            "tiktok": 1.2,
            "twitter": 0.8,
            "google": 0.9,
            "news": 0.7
        }

        base_weight = platform_weights.get(trend_data["platform"], 1.0)

        # View count score (logarithmic scaling)
        views = trend_data.get("view_count", 0)
        if views > 0:
            score += min(50, (views / 1000000) * 10)  # Max 50 points for 10M+ views

        # Engagement rate score
        engagement = trend_data.get("engagement_rate", 0.0)
        score += min(30, engagement * 10)  # Max 30 points for 3%+ engagement

        # Hashtag count score
        hashtags = len(trend_data.get("hashtags", []))
        score += min(10, hashtags * 2)  # Max 10 points for 5+ hashtags

        # Search volume score (for Google Trends)
        search_volume = trend_data.get("search_volume", 0)
        if search_volume > 0:
            score += min(20, search_volume / 10)  # Max 20 points for high search volume

        # Tweet volume score (for Twitter)
        tweet_volume = trend_data.get("tweet_volume", 0)
        if tweet_volume > 0:
            score += min(15, (tweet_volume / 10000) * 5)  # Max 15 points for high tweet volume

        # Recency bonus (newer trends get slight boost)
        score += 5  # Base recency score

        return score * base_weight

    async def get_top_trends(self, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top trending topics by virality score."""
        from sqlalchemy import desc

        result = await db.execute(
            db.query(Trend).filter(Trend.is_active == True).order_by(desc(Trend.virality_score)).limit(limit)
        )
        trends = result.scalars().all()

        return [
            {
                "id": trend.id,
                "platform": trend.platform,
                "trend_name": trend.trend_name,
                "virality_score": trend.virality_score,
                "hashtags": trend.hashtags,
                "description": trend.description,
                "view_count": trend.view_count,
                "engagement_rate": trend.engagement_rate
            }
            for trend in trends
        ]