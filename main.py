from fastapi import FastAPI, Request, Depends, HTTPException, File, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import io
import csv
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
import os, json, logging, asyncio
from datetime import datetime, timedelta, date
from gemini_engine import GeminiEngine
from db_manager import db_manager

# Firebase and Google Cloud imports
try:
    import firebase_admin
    from firebase_admin import credentials, auth
    from google.cloud import logging as cloud_logging
    from google.cloud import secretmanager
    import psutil
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Warning: Firebase dependencies not installed. Run: pip install firebase-admin google-cloud-logging")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Google Cloud Logging if available
if os.getenv('GCP_LOGGING_ENABLED', 'false').lower() == 'true' and FIREBASE_AVAILABLE:
    try:
        cloud_logging.Client()
        logger.info("Google Cloud Logging initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Google Cloud Logging: {e}")

app = FastAPI(
    title="FoodyFix API", 
    version="1.0.0",
    description="AI-powered nutrition intelligence API",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware with proper origins
cors_origins = os.getenv('CORS_ORIGINS', '*').split(',') if os.getenv('CORS_ORIGINS') else ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Fix Firebase private key handling
if FIREBASE_AVAILABLE and os.getenv('FIREBASE_PROJECT_ID'):
    try:
        private_key = os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
        
        # Validate private key format
        if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
            logger.warning("Firebase private key format may be incorrect")
        
        firebase_creds = credentials.Certificate({
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": private_key,
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_X509_CERT_URL'),
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
        })
        firebase_app = firebase_admin.initialize_app(credential=firebase_creds)
        logger.info("Firebase Admin initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        firebase_app = None

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
gemini = GeminiEngine()

# Firestore is now used via db_manager
# USER_DATA is used for session management and transient state
# Global Data (Migrating to Firestore via db_manager)
# We keep these for transient session state if needed, but primary data is in db_manager
USER_ID = "demo_user"
USER_DATA = {
    "user_sessions": {}
}

# ─── Pydantic Models ──────────────────────────────────────────────────────────
class FoodQuery(BaseModel):
    food_item: str
    quantity: Optional[str] = "1 serving"

class MealLog(BaseModel):
    name: str
    quantity: str
    date: Optional[str] = None

class CaloriesBurned(BaseModel):
    date: str
    amount: float
    activity: Optional[str] = "General Activity"

class OrderItem(BaseModel):
    name: str
    quantity: int = 1
    notes: Optional[str] = ""

class ManualOrder(BaseModel):
    restaurant: str
    items: List[OrderItem]
    date: Optional[str] = None

class WebhookOrder(BaseModel):
    source: str          # "swiggy", "zomato", "ubereats", "custom"
    order_id: str
    restaurant: str
    items: List[dict]
    total_amount: Optional[float] = None
    timestamp: Optional[str] = None

class UserProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    daily_calories: Optional[int] = None
    target_weight: Optional[float] = None
    activity_level: Optional[str] = None
    photo_url: Optional[str] = None

class HealthGoal(BaseModel):
    target_weight: Optional[float] = None
    daily_calories: Optional[int] = None
    activity_level: Optional[str] = "moderate"

class FirebaseUser(BaseModel):
    uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    email_verified: bool = False

class LoginRequest(BaseModel):
    id_token: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None

class HealthGoalRequest(BaseModel):
    goal_name: str
    target_days: int = 7
    description: Optional[str] = ""

class DietPlanRequest(BaseModel):
    preferences: str
    target_calories: Optional[int] = 2000
    diet_type: Optional[str] = "Balanced"
    allergies: Optional[List[str]] = []

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def guest_portal(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

@app.get("/auth", response_class=HTMLResponse)
async def auth_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth.html", context={})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={})

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    return templates.TemplateResponse(request=request, name="orders.html", context={})

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    return templates.TemplateResponse(request=request, name="reports.html", context={})

@app.get("/scan", response_class=HTMLResponse)
async def scan_page(request: Request):
    return templates.TemplateResponse(request=request, name="scan.html", context={})

@app.get("/rewards", response_class=HTMLResponse)
async def rewards_page(request: Request):
    return templates.TemplateResponse(request=request, name="rewards.html", context={})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse(request=request, name="profile.html", context={})

@app.get("/diet", response_class=HTMLResponse)
async def diet_page(request: Request):
    return templates.TemplateResponse(request=request, name="diet.html", context={})

# ─── Firebase Authentication Endpoints ─────────────────────────────────────
@app.post("/api/auth/login")
async def firebase_login(request: LoginRequest):
    """Login with Firebase ID token"""
    if not firebase_app:
        raise HTTPException(status_code=503, detail="Firebase not configured")
    
    try:
        decoded_token = auth.verify_id_token(request.id_token)
        uid = decoded_token['uid']
        
        # Get user info from Firebase
        user_record = auth.get_user(uid)
        
        user_data = {
            "uid": uid,
            "email": user_record.email,
            "display_name": user_record.display_name,
            "photo_url": user_record.photo_url,
            "email_verified": user_record.email_verified
        }
        
        # Store user session (in production, use Redis/Database)
        USER_DATA.setdefault('user_sessions', {})
        USER_DATA['user_sessions'][uid] = {
            'user': user_data,
            'login_time': datetime.now().isoformat()
        }
        
        return JSONResponse(content={
            "success": True, 
            "user": user_data,
            "message": "Login successful"
        })
    except Exception as e:
        logger.error(f"Firebase login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/auth/register")
async def firebase_register(request: RegisterRequest):
    """Register new user (placeholder for Firebase client-side auth)"""
    # In production, user registration happens on client-side with Firebase SDK
    # This endpoint can be used for additional server-side user setup
    return JSONResponse(content={
        "success": True,
        "message": "Registration endpoint ready. Use Firebase client SDK for actual registration."
    })

@app.post("/api/auth/logout")
async def firebase_logout(request: Request):
    """Logout user"""
    # Get user from session (simplified - in production use proper session management)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token['uid']
            if 'user_sessions' in USER_DATA and uid in USER_DATA['user_sessions']:
                del USER_DATA['user_sessions'][uid]
            return JSONResponse(content={"success": True, "message": "Logged out successfully"})
        except:
            pass
    
    return JSONResponse(content={"success": True, "message": "Session cleared"})

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current authenticated user"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No authorization token")
    
    token = auth_header.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        
        if 'user_sessions' in USER_DATA and uid in USER_DATA['user_sessions']:
            return JSONResponse(content={
                "success": True,
                "user": USER_DATA['user_sessions'][uid]['user']
            })
        else:
            raise HTTPException(status_code=401, detail="Session expired")
    except Exception as e:
        logger.error(f"Auth verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
# ─── Health Check Endpoint ───────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        system_info = {}
        try:
            import psutil
            system_info = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
            }
        except Exception:
            system_info = {"note": "psutil unavailable"}
        
        firebase_status = "not_configured"
        try:
            if firebase_app:
                firebase_status = "connected"
        except NameError:
            firebase_status = "not_initialized"
        
        return JSONResponse(content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "system": system_info,
            "services": {
                "firebase": firebase_status,
                "gemini_api": "configured" if os.getenv('GEMINI_API_KEY') else "not_configured"
            }

        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

# ─── API: Analyze Food ────────────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze_food(query: FoodQuery):
    try:
        logger.info(f"Analyzing food: {query.food_item}")
        result = await gemini.analyze_food(query.food_item, query.quantity)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error analyzing food: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze food. Please try again.")

# ─── API: Log Meal ────────────────────────────────────────────────────────────
@app.post("/api/meals")
async def log_meal(meal: MealLog):
    analysis = await gemini.analyze_food(meal.name, meal.quantity)
    entry = {
        "name": meal.name,
        "quantity": meal.quantity,
        "calories": analysis.get("calories", 0),
        "fat": analysis.get("fat_g", 0),
        "protein": analysis.get("protein_g", 0),
        "saturated_fat": analysis.get("saturated_fat_g", 0),
        "grade": analysis.get("health_grade", "C"),
        "date": meal.date or datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis
    }
    # Award credits
    credits_earned = _calculate_credits(entry)
    entry["credits_earned"] = credits_earned
    
    db_manager.add_meal(entry)
    stats = db_manager.get_credits()
    
    return JSONResponse(content={
        "success": True, 
        "meal": entry,
        "total_credits": stats["credits"]
    })

@app.post("/api/scan")
async def scan_food_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        analysis = await gemini.analyze_food_image(contents, file.content_type)
        
        entry = {
            "name": analysis.get("food_name", "Scanned Food"),
            "quantity": analysis.get("quantity", "1 serving"),
            "calories": analysis.get("calories", 0),
            "fat": analysis.get("fat_g", 0),
            "protein": analysis.get("protein_g", 0),
            "saturated_fat": analysis.get("saturated_fat_g", 0),
            "grade": analysis.get("health_grade", "C"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis
        }
        credits_earned = _calculate_credits(entry)
        entry["credits_earned"] = credits_earned
        
        db_manager.add_meal(entry)
        
        return JSONResponse(content={"success": True, "meal": entry})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/api/meals")
async def get_meals(date: Optional[str] = None):
    data = db_manager.get_user_data()
    meals = data.get("meals", [])
    if date:
        meals = [m for m in meals if m["date"] == date]
    return JSONResponse(content={"meals": meals})

# ─── API: Calories Burned ─────────────────────────────────────────────────────
@app.post("/api/calories-burned")
async def log_calories_burned(data: CaloriesBurned):
    entry = {"date": data.date, "amount": data.amount, "activity": data.activity}
    db_manager.add_activity(entry)
    return JSONResponse(content={"success": True})

# ─── API: Credits ─────────────────────────────────────────────────────────────
@app.get("/api/credits")
async def get_credits():
    stats = db_manager.get_credits()
    return JSONResponse(content=stats)

# ─── API: Health Prediction ───────────────────────────────────────────────────
@app.get("/api/predict")
async def health_prediction():
    user_data = db_manager.get_user_data()
    today = datetime.now().strftime("%Y-%m-%d")
    last_7 = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    calories_in = sum(m["calories"] for m in user_data.get("meals", []) if m["date"] in last_7)
    calories_out = sum(e["amount"] for e in user_data.get("activity_log", []) if e["date"] in last_7)
    
    daily_avg_in = calories_in / 7 if calories_in else 2000
    daily_avg_out = calories_out / 7 if calories_out else 1800
    
    net_daily = daily_avg_in - daily_avg_out
    weight_change_30d = (net_daily * 30) / 7700
    
    fatigue_risk = min(95, max(5, round(50 + (net_daily / 50), 1)))
    weight_gain_risk = min(95, max(5, round(50 + (weight_change_30d * 10), 1))) if weight_change_30d > 0 else 5
    
    prediction = await gemini.generate_health_forecast(daily_avg_in, daily_avg_out, weight_change_30d)
    
    return JSONResponse(content={
        "daily_avg_calories_in": round(daily_avg_in, 1),
        "daily_avg_calories_out": round(daily_avg_out, 1),
        "net_daily_calories": round(net_daily, 1),
        "weight_change_30d_kg": round(weight_change_30d, 2),
        "fatigue_risk_pct": fatigue_risk,
        "weight_gain_risk_pct": weight_gain_risk,
        "forecast": prediction,
        "period_days": 7
    })

# ─── API: Smart Report ────────────────────────────────────────────────────────
# ─── API: Smart Report ────────────────────────────────────────────────────────
@app.get("/api/reports")
async def monthly_report(month: Optional[str] = None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    user_data = db_manager.get_user_data()
    monthly_meals = [m for m in user_data.get("meals", []) if m["date"].startswith(month)]
    monthly_burned = [e for e in user_data.get("activity_log", []) if e["date"].startswith(month)]
    
    total_in = sum(m["calories"] for m in monthly_meals)
    total_out = sum(e["amount"] for e in monthly_burned)
    net_calories = total_in - total_out
    fat_change_kg = (net_calories * 30) / 7700 if monthly_meals else 0
    
    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for m in monthly_meals:
        g = m.get("grade", "C")
        grade_counts[g] = grade_counts.get(g, 0) + 1
    
    report_context = {
        "total_calories_in": total_in,
        "total_calories_out": total_out,
        "net_fat_g": round(fat_change_kg * 1000, 1),
        "grade_distribution": grade_counts
    }
    
    ai_insights = await gemini.generate_report_insights(report_context)
    
    report = {
        "month": month,
        "total_calories_in": round(total_in, 1),
        "total_calories_out": round(total_out, 1),
        "net_calories": round(net_calories, 1),
        "net_fat_g": round(fat_change_kg * 1000, 1),
        "grade_distribution": grade_counts,
        "monthly_summary": ai_insights.get("headline", "Great progress this month!"),
        "health_alerts": ai_insights.get("recommendations", ["Maintain consistent tracking"]),
        "improvement_goals": [ai_insights.get("next_month_goal", "Reduce saturated fat intake")],
        "daily_breakdown": _get_daily_breakdown(month)
    }
    
    return JSONResponse(content={"report": report})

@app.get("/api/reports/download")
async def download_monthly_report(month: Optional[str] = None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    user_data = db_manager.get_user_data()
    monthly_meals = [m for m in user_data.get("meals", []) if m["date"].startswith(month)]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Meal Name", "Quantity", "Calories", "Protein (g)", "Fat (g)", "Grade", "Reason"])
    
    for m in monthly_meals:
        writer.writerow([
            m.get("date"),
            m.get("name"),
            m.get("quantity"),
            m.get("calories"),
            m.get("protein"),
            m.get("fat"),
            m.get("grade"),
            m.get("analysis", {}).get("grade_reason", "")
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=FoodyFix_Report_{month}.csv"}
    )

# ─── API: User Profile ───────────────────────────────────────────────────────
@app.get("/api/profile")
async def get_user_profile():
    data = db_manager.get_user_data(USER_ID)
    profile = data.get("profile", {})
    return JSONResponse(content={
        "profile": profile,
        "stats": {
            "total_meals": len(data.get("meals", [])),
            "total_orders": len(data.get("orders", [])),
            "member_since": "2026-05-01"
        }
    })

@app.put("/api/profile")
async def update_user_profile(profile: UserProfile):
    try:
        data = db_manager.get_user_data(USER_ID)
        current_profile = data.get("profile", {})
        
        if profile.name:
            current_profile["name"] = profile.name
        if profile.email:
            current_profile["email"] = profile.email
        if profile.daily_calories:
            if "goals" not in current_profile: current_profile["goals"] = {}
            current_profile["goals"]["daily_calories"] = profile.daily_calories
        if profile.target_weight:
            if "goals" not in current_profile: current_profile["goals"] = {}
            current_profile["goals"]["target_weight"] = profile.target_weight
        if profile.activity_level:
            if "goals" not in current_profile: current_profile["goals"] = {}
            current_profile["goals"]["activity_level"] = profile.activity_level
        if profile.photo_url:
            current_profile["photo_url"] = profile.photo_url
        
        db_manager.update_profile(current_profile, USER_ID)
        return JSONResponse(content={"success": True, "profile": current_profile})
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@app.post("/api/profile/upload")
async def upload_profile_image(file: UploadFile = File(...)):
    try:
        os.makedirs("static/uploads", exist_ok=True)
        filename = f"avatar_{int(datetime.now().timestamp())}_{file.filename}"
        file_path = f"static/uploads/{filename}"
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        photo_url = f"/static/uploads/{filename}"
        data = db_manager.get_user_data(USER_ID)
        profile = data.get("profile", {})
        profile["photo_url"] = photo_url
        db_manager.update_profile(profile, USER_ID)
        
        return JSONResponse(content={"success": True, "photo_url": photo_url})
    except Exception as e:
        logger.error(f"Error uploading profile image: {str(e)}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)
# ─── API: Enhanced Health Stats ─────────────────────────────────────────────────
@app.get("/api/health-stats")
async def get_health_stats():
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        last_7_days = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        
        data = db_manager.get_user_data()
        meals = data.get("meals", [])
        
        today_meals = [m for m in meals if m["date"] == today]
        week_meals = [m for m in meals if m["date"] in last_7_days]
        
        today_calories = sum(m.get("calories", 0) for m in today_meals)
        week_calories = sum(m.get("calories", 0) for m in week_meals)
        
        # Calculate average health grade
        grades = [m.get("grade", "C") for m in week_meals]
        grade_points = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
        avg_grade_score = sum(grade_points.get(g, 2) for g in grades) / len(grades) if grades else 2
        
        return JSONResponse(content={
            "today": {
                "calories": today_calories,
                "meals_count": len(today_meals),
                "protein": sum(m.get("protein", 0) for m in today_meals)
            },
            "week": {
                "avg_calories": round(week_calories / 7, 1) if week_meals else 0,
                "total_meals": len(week_meals),
                "avg_grade": round(avg_grade_score, 1),
                "protein_total": sum(m.get("protein", 0) for m in week_meals)
            },
            "credits": USER_DATA["credits"]
        })
    except Exception as e:
        logger.error(f"Error getting health stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get health stats")

class OrderPost(BaseModel):
    food_name: str
    platform: str
    cost: Optional[float] = 0

@app.post("/api/orders/manual")
async def add_manual_order(order: ManualOrder):
    try:
        items_text = ", ".join([f"{i.quantity}x {i.name}" for i in order.items])
        analysis = await gemini.analyze_food(items_text, "full order")
        
        entry = {
            "id": f"FF-{datetime.now().strftime('%M%S')}",
            "source": "manual",
            "restaurant": order.restaurant,
            "items": [i.dict() for i in order.items],
            "total_calories": analysis.get("calories", 0),
            "total_fat": analysis.get("fat_g", 0),
            "total_protein": analysis.get("protein_g", 0),
            "health_grade": analysis.get("health_grade", "C"),
            "date": order.date or datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "status": "logged"
        }
        db_manager.add_order(entry)
        
        # Auto-log to meals as a single entry
        meal_entry = {
            "name": f"Order from {order.restaurant}",
            "quantity": f"{len(order.items)} items",
            "calories": entry["total_calories"],
            "fat": entry["total_fat"],
            "protein": entry["total_protein"],
            "grade": entry["health_grade"],
            "date": entry["date"],
            "timestamp": entry["timestamp"],
            "analysis": analysis
        }
        credits = _calculate_credits(meal_entry)
        meal_entry["credits_earned"] = credits
        db_manager.add_meal(meal_entry)
        
        stats = db_manager.get_credits()
        return JSONResponse(content={
            "success": True, 
            "order": entry, 
            "credits_earned": credits,
            "total_credits": stats["credits"]
        })
    except Exception as e:
        logger.error(f"Error adding manual order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders")
async def add_simple_order(order: OrderPost):
    try:
        analysis = await gemini.analyze_food(order.food_name, "1 order")
        # ... existing logic for simple order if still needed ...
        # For now, let's keep it but fix the duplicate decorator
        entry = {
            "source": order.platform,
            "platform": order.platform,
            "food_name": order.food_name,
            "cost": order.cost,
            "calories": analysis.get("calories", 0),
            "fat_g": analysis.get("fat_g", 0),
            "protein_g": analysis.get("protein_g", 0),
            "health_grade": analysis.get("health_grade", "C"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "status": "logged"
        }
        db_manager.add_order(entry)
        
        meal_entry = {
            "name": order.food_name,
            "quantity": "1 order",
            "calories": entry["calories"],
            "fat": entry["fat_g"],
            "protein": entry["protein_g"],
            "grade": entry["health_grade"],
            "date": entry["date"],
            "timestamp": entry["timestamp"],
            "analysis": analysis
        }
        credits = _calculate_credits(meal_entry)
        db_manager.add_meal(meal_entry)
        stats = db_manager.get_credits()
        
        return JSONResponse(content={
            "success": True, 
            "order": entry, 
            "credits_earned": credits,
            "total_credits": stats["credits"]
        })
    except Exception as e:
        logger.error(f"Error adding order: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add order")

@app.post("/api/orders/webhook")
async def webhook_order(order: WebhookOrder):
    """Endpoint for Swiggy/Zomato/UberEats webhook integration"""
    items_text = ", ".join([f"{i.get('quantity',1)}x {i.get('name','item')}" for i in order.items])
    analysis = await gemini.analyze_food(items_text, "full order")
    
    entry = {
        "id": f"FF-{datetime.now().strftime('%M%S')}",
        "source": order.source,
        "external_order_id": order.order_id,
        "restaurant": order.restaurant,
        "items": order.items,
        "total_calories": analysis.get("calories", 0),
        "total_fat": analysis.get("fat_g", 0),
        "total_protein": analysis.get("protein_g", 0),
        "health_grade": analysis.get("health_grade", "C"),
        "date": (order.timestamp or datetime.now().isoformat())[:10],
        "timestamp": order.timestamp or datetime.now().isoformat(),
        "status": "synced"
    }
    db_manager.add_order(entry)
    
    # Auto-log to meals
    meal_entry = {
        "name": f"Order from {order.restaurant}",
        "quantity": f"{len(order.items)} items",
        "calories": entry["total_calories"],
        "fat": entry["total_fat"],
        "protein": entry["total_protein"],
        "grade": entry["health_grade"],
        "date": entry["date"],
        "timestamp": entry["timestamp"],
        "analysis": analysis
    }
    credits = _calculate_credits(meal_entry)
    meal_entry["credits_earned"] = credits
    db_manager.add_meal(meal_entry)
    
    return JSONResponse(content={"success": True, "order_id": entry["id"], "analysis": analysis, "credits_earned": credits})

@app.get("/api/orders")
async def get_orders(source: Optional[str] = None, date: Optional[str] = None):
    user_data = db_manager.get_user_data()
    orders = user_data.get("orders", [])
    if source:
        orders = [o for o in orders if o["source"] == source]
    if date:
        orders = [o for o in orders if o["date"] == date]
    return JSONResponse(content={"orders": orders, "total": len(orders)})

@app.get("/api/orders/download")
async def download_orders():
    user_data = db_manager.get_user_data()
    orders = user_data.get("orders", [])
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID", "Source", "Restaurant", "Date", "Calories", "Grade", "Status"])
    
    for o in orders:
        writer.writerow([
            o.get("id") or o.get("order_id") or "N/A",
            o.get("source") or o.get("platform") or "manual",
            o.get("restaurant") or o.get("food_name") or "Unknown",
            o.get("date") or o.get("timestamp", "")[:10],
            o.get("total_calories") or o.get("calories") or 0,
            o.get("health_grade") or o.get("grade") or "C",
            o.get("status") or "logged"
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=FoodyFix_Orders_Export.csv"}
    )

@app.get("/api/integration-guide")
async def integration_guide():
    """Returns webhook/API integration guide for external ordering apps"""
    base_url = os.getenv("BASE_URL", "https://your-foodyfix-app.run.app")
    return JSONResponse(content={
        "webhook_url": f"{base_url}/api/orders/webhook",
        "method": "POST",
        "supported_sources": ["swiggy", "zomato", "ubereats", "custom"],
        "payload_example": {
            "source": "swiggy",
            "order_id": "SWG123456",
            "restaurant": "Healthy Bowl Co.",
            "items": [{"name": "Grilled Chicken Bowl", "quantity": 1}],
            "timestamp": "2025-01-15T19:30:00Z"
        },
        "headers": {"Content-Type": "application/json", "X-FoodyFix-Key": "your-api-key"}
    })

# ─── API: Rewards & Goals ───────────────────────────────────────────────────
@app.get("/api/rewards/status")
async def get_reward_status():
    data = db_manager.get_user_data()
    rewards = data.get("rewards", {
        "current_goal": None,
        "streak": 0,
        "cheat_meals_available": 0,
        "completed_goals": 0,
        "progress": 0
    })
    
    # Calculate streak based on recent meals
    meals = data.get("meals", [])
    today_date = date.today()
    
    streak = 0
    if meals:
        # Sort meals by date descending
        sorted_meals = sorted(meals, key=lambda x: x.get("date", ""), reverse=True)
        today_str = date.today().strftime("%Y-%m-%d")
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Start checking from today or yesterday
        has_today = any(m.get("date") == today_str for m in sorted_meals)
        has_yesterday = any(m.get("date") == yesterday_str for m in sorted_meals)
        
        if has_today or has_yesterday:
            checked_date = date.today() if has_today else date.today() - timedelta(days=1)
            while True:
                day_str = checked_date.strftime("%Y-%m-%d")
                day_meals = [m for m in sorted_meals if m.get("date") == day_str]
                
                if not day_meals:
                    break
                
                # Strict streak: Day is healthy only if ALL meals are A, B, or C, AND at least one is A or B.
                # Or simpler: no D or F meals on that day.
                has_unhealthy = any(m.get("grade") in ["D", "F"] for m in day_meals)
                has_very_healthy = any(m.get("grade") in ["A", "B"] for m in day_meals)
                
                if not has_unhealthy and has_very_healthy:
                    streak += 1
                    checked_date -= timedelta(days=1)
                else:
                    break
    
    rewards["streak"] = streak
    
    # Update progress if goal exists
    if rewards.get("current_goal"):
        target = rewards["current_goal"].get("target_days", 7)
        rewards["progress"] = min(100, (streak / target) * 100)
    else:
        rewards["progress"] = 0
    
    db_manager.update_rewards(rewards)
    
    return JSONResponse(content={
        "success": True,
        "rewards": rewards,
        "total_credits": data.get("credits", 0)
    })

@app.post("/api/rewards/goal")
async def set_reward_goal(goal: HealthGoalRequest):
    data = db_manager.get_user_data()
    rewards = data.get("rewards", {})
    
    rewards["current_goal"] = {
        "name": goal.goal_name,
        "target_days": goal.target_days,
        "description": goal.description,
        "started_at": datetime.now().isoformat()
    }
    rewards["progress"] = 0
    db_manager.update_rewards(rewards)
    
    return JSONResponse(content={"success": True, "goal": rewards["current_goal"]})

@app.post("/api/rewards/claim-cheat-meal")
async def claim_cheat_meal():
    data = db_manager.get_user_data()
    rewards = data.get("rewards", {})
    goal = rewards.get("current_goal")
    
    if not goal:
        return JSONResponse(content={"success": False, "message": "No active goal."}, status_code=400)
        
    if rewards.get("streak", 0) >= goal.get("target_days", 7):
        rewards["cheat_meals_available"] = rewards.get("cheat_meals_available", 0) + 1
        rewards["completed_goals"] = rewards.get("completed_goals", 0) + 1
        rewards["current_goal"] = None
        rewards["progress"] = 0
        db_manager.update_rewards(rewards)
        return JSONResponse(content={"success": True, "message": "Cheat Meal Unlocked! Enjoy your reward."})
    
    return JSONResponse(content={"success": False, "message": f"Goal not yet reached. Need {goal.get('target_days', 7)} days streak."}, status_code=400)

# ─── API: Diet Plan ──────────────────────────────────────────────────────────
@app.post("/api/diet/generate")
async def generate_diet_plan(req: DietPlanRequest):
    try:
        plan = await gemini.generate_diet_plan(
            req.preferences, 
            req.target_calories, 
            req.diet_type, 
            req.allergies
        )
        return JSONResponse(content={"success": True, "plan": plan})
    except Exception as e:
        logger.error(f"Error generating diet plan: {str(e)}")
        raise HTTPException(status_code=500, detail="Neural Engine failed to generate plan.")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _calculate_credits(meal: dict) -> int:
    credits = 0
    if meal.get("protein", 0) > 20: credits += 50
    if meal.get("saturated_fat", 0) < 5: credits += 30
    grade = meal.get("grade", "C")
    grade_credits = {"A": 100, "B": 60, "C": 20, "D": 0, "F": 0}
    credits += grade_credits.get(grade, 0)
    return credits

def _get_rewards(credits: int) -> list:
    rewards = [
        {"name": "Cheat Meal Unlock 🍕", "threshold": 500, "unlocked": credits >= 500},
        {"name": "Premium Recipe Pack 🥗", "threshold": 1000, "unlocked": credits >= 1000},
        {"name": "Nutrition Coach Session 💪", "threshold": 2000, "unlocked": credits >= 2000},
    ]
    return rewards

def _get_daily_breakdown(month: str) -> list:
    from collections import defaultdict
    user_data = db_manager.get_user_data()
    daily = defaultdict(lambda: {"calories_in": 0, "calories_out": 0})
    for m in user_data.get("meals", []):
        if m["date"].startswith(month):
            daily[m["date"]]["calories_in"] += m["calories"]
    for e in user_data.get("activity_log", []):
        if e["date"].startswith(month):
            daily[e["date"]]["calories_out"] += e["amount"]
    return [{"date": k, **v} for k, v in sorted(daily.items())]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
