import os, json, re, base64
import httpx
from typing import Optional

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

GEMINI_TEXT_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

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
    """Gemini API wrapper — supports text analysis and vision (image) analysis with OpenRouter fallback."""

    def __init__(self):
        self.api_key  = GEMINI_API_KEY
        self.or_key = OPENROUTER_API_KEY
        self.headers  = {"Content-Type": "application/json"}

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _call_gemini(self, payload: dict, url: str = GEMINI_TEXT_URL) -> dict:
        """Send a payload to Gemini and return parsed JSON."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{url}?key={self.api_key}",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            raw  = resp.json()
            text = raw["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_json(text)

    async def _call_openrouter(self, prompt: str) -> dict:
        """Fallback call to OpenRouter (using Llama 3 or similar) if Gemini fails."""
        if not self.or_key:
            raise Exception("OpenRouter API key not configured")
            
        headers = {
            "Authorization": f"Bearer {self.or_key}",
            "HTTP-Referer": "https://foodyfix.ai", # Optional
            "X-Title": "FoodyFix",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "meta-llama/llama-3-8b-instruct:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()
            text = raw["choices"][0]["message"]["content"]
            return self._parse_json(text)

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
        """Analyze food with Gemini, fallback to OpenRouter on failure."""
        prompt = (
            f'You are a precision nutritionist AI. '
            f'Analyze "{quantity} of {food_item}" and respond ONLY with this exact JSON '
            f'(no markdown, no extra text):\n{_NUTRITION_SCHEMA}\n{_GRADE_CRITERIA}'
        )
        try:
            # Try Gemini First
            return await self._call_gemini({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000},
            })
        except Exception as e:
            # Fallback to OpenRouter
            try:
                return await self._call_openrouter(prompt)
            except Exception as or_e:
                return self._fallback_nutrition(food_item, quantity, f"Gemini: {e} | OpenRouter: {or_e}")

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """Analyze food image with Gemini (multimodal). Fallback to text-only OpenRouter if vision fails."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            "You are an expert nutritionist AI. Identify food items in this image, "
            "estimate portion size, and respond ONLY with this JSON:\n"
            + _NUTRITION_SCHEMA + "\n" + _GRADE_CRITERIA
        )
        try:
            payload = {
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                        {"text": prompt},
                    ]
                }],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000},
            }
            return await self._call_gemini(payload)
        except Exception as e:
            # Note: OpenRouter doesn't easily support vision on free models, 
            # so we just return the error for vision for now, or fallback to a text-only guess.
            return self._fallback_nutrition("Image food", "estimated portion", str(e))

    async def generate_health_forecast(self, cal_in: float, cal_out: float, weight_change: float) -> dict:
        """30-day health projection."""
        direction  = "gain" if weight_change > 0 else "loss"
        abs_change = abs(round(weight_change, 2))
        prompt = (
            f"Predict 30-day weight {direction}: {abs_change} kg. "
            f"Calories In: {cal_in:.0f}, Out: {cal_out:.0f}. "
            "Respond ONLY with JSON:\n"
            '{"summary": "...", "risk_level": "...", "primary_risk": "...", "action_items": [], "motivational_message": "...", "weeks_to_goal": 0}'
        )
        try:
            return await self._call_gemini({"contents": [{"parts": [{"text": prompt}]}]})
        except Exception:
            try:
                return await self._call_openrouter(prompt)
            except Exception:
                return {"summary": "Forecasting unavailable.", "error": "AI failure"}

    async def generate_report_insights(self, report_data: dict) -> dict:
        """Monthly health report insights."""
        prompt = (
            "Nutritional data analysis for month. Data:\n" + json.dumps(report_data) +
            "\nRespond ONLY with JSON: {\"headline\": \"...\", \"biggest_win\": \"...\", \"biggest_challenge\": \"...\", \"next_month_goal\": \"...\", \"recommendations\": []}"
        )
        try:
            return await self._call_gemini({"contents": [{"parts": [{"text": prompt}]}]})
        except Exception:
            try:
                return await self._call_openrouter(prompt)
            except Exception:
                return {"headline": "Keep going!", "recommendations": ["Log more meals"]}

    async def generate_diet_plan(self, preferences: str, calories: int, diet_type: str, allergies: list) -> dict:
        """Generate a personalized diet plan."""
        prompt = (
            f"Generate a 1-day professional diet plan. Target: {calories} calories. "
            f"Diet Type: {diet_type}. Preferences: {preferences}. Allergies: {', '.join(allergies)}. "
            "Respond ONLY with JSON: {"
            "\"title\": \"Plan Name\", "
            "\"meals\": ["
            "{\"type\": \"Breakfast\", \"name\": \"...\", \"calories\": 0, \"protein\": 0, \"notes\": \"...\"},"
            "{\"type\": \"Lunch\", \"name\": \"...\", \"calories\": 0, \"protein\": 0, \"notes\": \"...\"},"
            "{\"type\": \"Dinner\", \"name\": \"...\", \"calories\": 0, \"protein\": 0, \"notes\": \"...\"}"
            "], "
            "\"nutritional_summary\": \"...\", "
            "\"why_it_works\": \"...\", "
            "\"pro_tip\": \"...\""
            "}"
        )
        try:
            return await self._call_gemini({"contents": [{"parts": [{"text": prompt}]}]})
        except Exception:
            try:
                return await self._call_openrouter(prompt)
            except Exception:
                return {"title": "Sample Plan", "meals": [], "error": "AI Plan generation failed."}
