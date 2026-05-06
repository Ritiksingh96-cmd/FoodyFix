import os, json, re, base64
import httpx
from typing import Optional

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
GEMINI_VISION_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


# ─── Shared nutrition JSON schema used by both text & vision prompts ─────────
_NUTRITION_SCHEMA = """
{
  "food_name": "detected food name",
  "quantity": "estimated portion",
  "calories": <number>,
  "protein_g": <number>,
  "carbs_g": <number>,
  "fat_g": <number>,
  "saturated_fat_g": <number>,
  "fiber_g": <number>,
  "sugar_g": <number>,
  "sodium_mg": <number>,
  "health_grade": "<A|B|C|D|F>",
  "grade_reason": "one sentence why this grade",
  "benefits": ["benefit 1", "benefit 2", "benefit 3"],
  "risks": ["risk 1", "risk 2"],
  "health_tips": ["tip 1", "tip 2"],
  "healthier_alternative": "suggest a healthier swap",
  "good_for": ["weight loss", "muscle gain", "heart health"],
  "avoid_if": ["diabetes", "high cholesterol"],
  "is_high_protein": <true|false>,
  "is_low_saturated_fat": <true|false>,
  "recommendation": "<eat freely|eat in moderation|eat rarely|avoid>"
}
"""

_GRADE_CRITERIA = (
    "Health grade criteria: "
    "A=excellent (high protein, low sat fat, high fiber, low sugar), "
    "B=good, "
    "C=moderate (average macros), "
    "D=poor (high sat fat, low nutrients, high sugar), "
    "F=very poor (processed/junk, negligible nutrition)."
)


class GeminiEngine:
    """Gemini API wrapper — supports text analysis and vision (image) analysis."""

    def __init__(self):
        self.api_key  = GEMINI_API_KEY
        self.headers  = {"Content-Type": "application/json"}

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _call(self, payload: dict, url: str = GEMINI_TEXT_URL) -> dict:
        """Send a payload to Gemini and return parsed JSON."""
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                f"{url}?key={self.api_key}",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            raw  = resp.json()
            text = raw["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_json(text)

    def _call_text(self, prompt: str) -> dict:
        """Build a text-only Gemini payload."""
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.25, "maxOutputTokens": 1500},
        }

    def _call_vision(self, prompt: str, image_b64: str, mime_type: str) -> dict:
        """Build a multimodal (text + image) Gemini payload."""
        return {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                    {"text": prompt},
                ]
            }],
            "generationConfig": {"temperature": 0.25, "maxOutputTokens": 1500},
        }

    def _parse_json(self, text: str) -> dict:
        """Strip markdown fences and parse JSON robustly."""
        clean = re.sub(r"```(?:json)?|```", "", text).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            return {"error": "Could not parse AI response", "raw": text[:400]}

    @staticmethod
    def _fallback_nutrition(food_name: str, quantity: str, error: str) -> dict:
        return {
            "food_name": food_name, "quantity": quantity,
            "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0,
            "saturated_fat_g": 0, "fiber_g": 0, "sugar_g": 0, "sodium_mg": 0,
            "health_grade": "C", "grade_reason": "Analysis unavailable.",
            "benefits": [], "risks": [], "health_tips": [],
            "healthier_alternative": "",
            "good_for": [], "avoid_if": [],
            "is_high_protein": False, "is_low_saturated_fat": True,
            "recommendation": "eat in moderation",
            "error": error,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def analyze_food(self, food_item: str, quantity: str = "1 serving") -> dict:
        """Text-based food analysis using Gemini 1.5 Flash."""
        prompt = (
            f'You are a precision nutritionist AI. '
            f'Analyze "{quantity} of {food_item}" and respond ONLY with this exact JSON '
            f'(no markdown, no extra text):\n{_NUTRITION_SCHEMA}\n{_GRADE_CRITERIA}'
        )
        try:
            return await self._call(self._call_text(prompt))
        except Exception as exc:
            return self._fallback_nutrition(food_item, quantity, str(exc))

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """
        Vision-based food analysis — accepts raw image bytes.
        Gemini 1.5 Flash identifies the food, estimates portions, and
        returns the same structured nutrition JSON as analyze_food().
        """
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            "You are an expert nutritionist AI with computer vision capabilities. "
            "Look at this food image carefully. Identify every food item visible, "
            "estimate the portion size, and respond ONLY with this exact JSON "
            "(no markdown, no extra text):\n"
            + _NUTRITION_SCHEMA
            + "\n" + _GRADE_CRITERIA
            + "\n\nIf multiple foods are visible, analyze the dominant item and mention others "
            "in the food_name field. If the image does not contain food, set food_name to "
            "'Unknown' and calories to 0."
        )
        try:
            payload = self._call_vision(prompt, image_b64, mime_type)
            return await self._call(payload, url=GEMINI_VISION_URL)
        except Exception as exc:
            return self._fallback_nutrition("Image food", "estimated portion", str(exc))

    async def generate_health_forecast(self, cal_in: float, cal_out: float, weight_change: float) -> dict:
        """30-day weight and health projection."""
        direction  = "gain" if weight_change > 0 else "loss"
        abs_change = abs(round(weight_change, 2))
        prompt = (
            f"You are a predictive health AI. A user averages {cal_in:.0f} calories consumed "
            f"and {cal_out:.0f} calories burned daily. "
            f"Predicted 30-day weight {direction}: {abs_change} kg.\n\n"
            "Respond ONLY with this JSON (no markdown):\n"
            "{\n"
            '  "summary": "2-sentence plain-English forecast",\n'
            '  "risk_level": "<low|moderate|high|critical>",\n'
            '  "primary_risk": "main health risk in 5 words",\n'
            '  "fatigue_warning": "<describe fatigue risk if net positive calories>",\n'
            '  "action_items": ["action1", "action2", "action3"],\n'
            '  "motivational_message": "one encouraging sentence",\n'
            '  "weeks_to_goal": <estimated weeks to healthy balance as integer>\n'
            "}"
        )
        try:
            return await self._call(self._call_text(prompt))
        except Exception as exc:
            return {
                "summary": "Unable to generate forecast at this time.",
                "risk_level": "moderate",
                "primary_risk": "Caloric imbalance detected",
                "fatigue_warning": "",
                "action_items": [
                    "Track meals consistently",
                    "Add 30 mins of activity",
                    "Drink more water",
                ],
                "motivational_message": "Every healthy choice counts!",
                "weeks_to_goal": 8,
                "error": str(exc),
            }

    async def generate_report_insights(self, report_data: dict) -> dict:
        """AI-generated monthly health report insights."""
        prompt = (
            "You are a nutritional data analyst. Here is a user's monthly health data:\n"
            + json.dumps(report_data, indent=2)
            + "\n\nRespond ONLY with this JSON:\n"
            "{\n"
            '  "headline": "one punchy headline about their month",\n'
            '  "biggest_win": "their best achievement this month",\n'
            '  "biggest_challenge": "their main struggle",\n'
            '  "next_month_goal": "one specific, measurable goal",\n'
            '  "diet_pattern": "<balanced|calorie_surplus|calorie_deficit|erratic>",\n'
            '  "recommendations": ["rec1", "rec2", "rec3"]\n'
            "}"
        )
        try:
            return await self._call(self._call_text(prompt))
        except Exception as exc:
            return {
                "headline": "Keep pushing your health goals!",
                "biggest_win": "You tracked your meals consistently",
                "biggest_challenge": "Maintaining caloric balance",
                "next_month_goal": "Log meals every day",
                "diet_pattern": "balanced",
                "recommendations": [
                    "Eat more vegetables",
                    "Exercise 3x per week",
                    "Drink 2L water daily",
                ],
                "error": str(exc),
            }
