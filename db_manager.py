import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self):
        self.db = None
        self.users_ref = None
        self._local_data = {
            "demo_user": {
                "id": "demo_user",
                "credits": 250,
                "meals": [],
                "activity_log": [],
                "orders": []
            }
        }
        
        # Try to initialize Firestore, fall back to in-memory if it fails
        try:
            from google.cloud import firestore
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "foodyfix-eef1f")
            self.db = firestore.Client(project=project_id)
            self.users_ref = self.db.collection("users")
            logger.info("Firestore connected successfully")
        except Exception as e:
            logger.warning(f"Firestore unavailable, using in-memory storage: {e}")
            self.db = None
            self.users_ref = None

    def get_user_data(self, user_id="demo_user"):
        if self.db and self.users_ref:
            try:
                doc = self.users_ref.document(user_id).get()
                if doc.exists:
                    return doc.to_dict()
                else:
                    default_data = self._default_data(user_id)
                    self.users_ref.document(user_id).set(default_data)
                    return default_data
            except Exception as e:
                logger.warning(f"Firestore read failed: {e}")
        
        # Fallback to local
        if user_id not in self._local_data:
            self._local_data[user_id] = self._default_data(user_id)
        return self._local_data[user_id]

    def _default_data(self, user_id):
        return {
            "id": user_id,
            "credits": 250,
            "meals": [],
            "activity_log": [],
            "orders": [],
            "profile": {
                "name": "Health Architect",
                "email": "architect@foodyfix.ai",
                "photo_url": None,
                "goals": {"daily_calories": 2000}
            },
            "rewards": {
                "current_goal": None,
                "streak": 0,
                "cheat_meals_available": 0,
                "completed_goals": 0,
                "progress": 0
            }
        }

    def add_meal(self, meal, user_id="demo_user"):
        if self.db and self.users_ref:
            try:
                from google.cloud import firestore
                user_ref = self.users_ref.document(user_id)
                user_ref.update({
                    "meals": firestore.ArrayUnion([meal]),
                    "credits": firestore.Increment(meal.get("credits_earned", 0))
                })
                return
            except Exception as e:
                logger.warning(f"Firestore write failed: {e}")
        
        # Fallback
        data = self.get_user_data(user_id)
        data["meals"].append(meal)
        data["credits"] = data.get("credits", 0) + meal.get("credits_earned", 0)

    def add_activity(self, activity, user_id="demo_user"):
        if self.db and self.users_ref:
            try:
                from google.cloud import firestore
                user_ref = self.users_ref.document(user_id)
                user_ref.update({
                    "activity_log": firestore.ArrayUnion([activity])
                })
                return
            except Exception as e:
                logger.warning(f"Firestore write failed: {e}")
        
        # Fallback
        data = self.get_user_data(user_id)
        data["activity_log"].append(activity)

    def add_order(self, order, user_id="demo_user"):
        if self.db and self.users_ref:
            try:
                from google.cloud import firestore
                user_ref = self.users_ref.document(user_id)
                user_ref.update({
                    "orders": firestore.ArrayUnion([order])
                })
                return
            except Exception as e:
                logger.warning(f"Firestore write failed: {e}")
        
        # Fallback
        data = self.get_user_data(user_id)
        data["orders"].append(order)

    def get_credits(self, user_id="demo_user"):
        data = self.get_user_data(user_id)
        credits = data.get("credits", 0)
        cheat_threshold = 500
        progress_pct = min(100, (credits / cheat_threshold) * 100)
        
        rewards = [
            {"id": "cheat1", "name": "🍕 Strategic Cheat Meal", "threshold": 500, "unlocked": credits >= 500},
            {"id": "coaching1", "name": "🥗 Pro Nutrition Session", "threshold": 1200, "unlocked": credits >= 1200},
            {"id": "master1", "name": "💪 Metabolic Master Class", "threshold": 2500, "unlocked": credits >= 2500}
        ]
        
        return {
            "credits": credits,
            "progress_pct": progress_pct,
            "cheat_threshold": cheat_threshold,
            "rewards": rewards
        }

    def update_rewards(self, rewards, user_id="demo_user"):
        if self.db and self.users_ref:
            try:
                user_ref = self.users_ref.document(user_id)
                user_ref.update({"rewards": rewards})
                return
            except Exception as e:
                logger.warning(f"Firestore rewards update failed: {e}")
        
        data = self.get_user_data(user_id)
        data["rewards"] = rewards

    def update_profile(self, profile, user_id="demo_user"):
        if self.db and self.users_ref:
            try:
                user_ref = self.users_ref.document(user_id)
                user_ref.update({"profile": profile})
                return
            except Exception as e:
                logger.warning(f"Firestore profile update failed: {e}")
        
        data = self.get_user_data(user_id)
        data["profile"] = profile

# Global instance
db_manager = DBManager()
