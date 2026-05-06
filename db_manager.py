import os
from google.cloud import firestore
from datetime import datetime

class DBManager:
    def __init__(self):
        # Initialize Firestore client
        # In production, it uses GOOGLE_APPLICATION_CREDENTIALS or the default project identity
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "foodyfix-eef1f")
        self.db = firestore.Client(project=project_id)
        self.users_ref = self.db.collection("users")

    def get_user_data(self, user_id="demo_user"):
        doc = self.users_ref.document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        else:
            # Initialize default user data if not exists
            default_data = {
                "id": user_id,
                "credits": 250,
                "meals": [],
                "activity_log": [],
                "orders": []
            }
            self.users_ref.document(user_id).set(default_data)
            return default_data

    def add_meal(self, meal, user_id="demo_user"):
        user_ref = self.users_ref.document(user_id)
        user_ref.update({
            "meals": firestore.ArrayUnion([meal]),
            "credits": firestore.Increment(meal.get("credits_earned", 0))
        })

    def add_activity(self, activity, user_id="demo_user"):
        user_ref = self.users_ref.document(user_id)
        user_ref.update({
            "activity_log": firestore.ArrayUnion([activity])
        })

    def add_order(self, order, user_id="demo_user"):
        user_ref = self.users_ref.document(user_id)
        user_ref.update({
            "orders": firestore.ArrayUnion([order])
        })

    def get_credits(self, user_id="demo_user"):
        data = self.get_user_data(user_id)
        credits = data.get("credits", 0)
        # Calculate level/progress (simple logic for now)
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

# Global instance
db_manager = DBManager()
