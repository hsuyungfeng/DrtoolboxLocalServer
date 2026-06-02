"""
Google Maps / Business Profile Service - Task 12.1

Handles fetching, analyzing, and replying to Google Maps reviews.
Uses AI to generate draft replies for staff approval.
"""

import os
import sys
import json
import logging
import sqlite3
from datetime import datetime

import requests

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.agent.hermes_core import get_hermes_agent
from src.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
GBP_API_BASE = "https://mybusiness.googleapis.com/v4"
# Account and Location IDs would typically be in .env
GBP_ACCOUNT_ID = os.getenv("GBP_ACCOUNT_ID", "")
GBP_LOCATION_ID = os.getenv("GBP_LOCATION_ID", "")
GBP_ACCESS_TOKEN = os.getenv("GBP_ACCESS_TOKEN", "")

DB_PATH = "data/db/clinic.db"

class GoogleMapsService:
    """Manages Google Business Profile reviews and AI-powered replies."""

    def __init__(self):
        self.agent = get_hermes_agent()

    def fetch_and_process_reviews(self):
        """
        Polls for new reviews, saves them to DB, and generates AI drafts.
        (Note: For a production system, this would use OAuth2 refresh tokens)
        """
        if not GBP_ACCESS_TOKEN or not GBP_LOCATION_ID:
            logger.warning("GBP credentials not fully configured. Skipping fetch.")
            return []

        url = f"{GBP_API_BASE}/accounts/{GBP_ACCOUNT_ID}/locations/{GBP_LOCATION_ID}/reviews"
        headers = {"Authorization": f"Bearer {GBP_ACCESS_TOKEN}"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            reviews = resp.json().get('reviews', [])
            
            processed_count = 0
            for r in reviews:
                review_id = r.get('reviewId')
                author = r.get('reviewer', {}).get('displayName', 'Anonymous')
                content = r.get('comment', '')
                rating = r.get('starRating') # e.g., 'FIVE'
                
                # Convert rating string to int
                rating_map = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5}
                rating_int = rating_map.get(rating, 0)

                if self._is_new_review(review_id):
                    self._process_single_review(review_id, author, content, rating_int)
                    processed_count += 1
            
            return processed_count
        except Exception as e:
            logger.error(f"Failed to fetch Google reviews: {e}")
            return 0

    def _is_new_review(self, review_id):
        """Check if review already exists in external_comments table."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM external_comments WHERE external_id = ?", (review_id,))
        exists = cursor.fetchone()
        conn.close()
        return not exists

    def _process_single_review(self, review_id, author, content, rating):
        """Generates AI draft and saves to DB."""
        logger.info(f"Processing new Google review from {author} ({rating} stars)")
        
        # 1. Generate AI Draft Reply
        draft_reply = self._generate_draft(author, content, rating)
        
        # 2. Save to DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO external_comments (platform, external_id, author_name, rating, content, ai_draft_reply, status)
            VALUES ('google_maps', ?, ?, ?, ?, ?, 'pending')
        """, (review_id, author, rating, content, draft_reply))
        conn.commit()
        conn.close()

        # 3. Notify Staff if rating is low
        if rating <= 3:
            notification_service.notify_high_risk(
                patient_id=f"Reviewer:{author}",
                message=f"獲得 {rating} 星評論：\"{content[:100]}\"",
                risk_type="Google Maps Negative Review"
            )

    def _generate_draft(self, author, content, rating):
        """Uses Hermes to create a context-aware response."""
        if rating >= 4:
            prompt = f"你是一個專業溫暖的診所公關。收到來自『{author}』的 {rating} 星 Google 好評：『{content}』。請寫一段親切的感謝回覆。"
        else:
            prompt = f"你是一個專業且富有同理心的醫療糾紛協調員。收到來自『{author}』的 {rating} 星 Google 負評：『{content}』。請寫一段誠懇、不卑不亢的專業回覆，並邀請對方私下溝通解決問題。"
        
        response, _, _, _ = self.agent.chat(prompt)
        return response

    def post_reply(self, review_id, reply_text):
        """Submit the approved reply back to Google."""
        if not GBP_ACCESS_TOKEN: return False
        
        url = f"{GBP_API_BASE}/accounts/{GBP_ACCOUNT_ID}/locations/{GBP_LOCATION_ID}/reviews/{review_id}/reply"
        headers = {"Authorization": f"Bearer {GBP_ACCESS_TOKEN}", "Content-Type": "application/json"}
        payload = {"comment": reply_text}
        
        try:
            resp = requests.put(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                # Update DB status
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE external_comments SET status='replied', replied_at=CURRENT_TIMESTAMP WHERE external_id=?", (review_id,))
                conn.commit()
                conn.close()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to post Google review reply: {e}")
            return False

# Singleton
google_maps_service = GoogleMapsService()
