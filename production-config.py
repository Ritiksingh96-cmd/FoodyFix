"""
Production configuration for FoodyFix deployment
This file handles production-specific settings and error handling
"""

import os
import logging
from typing import Optional

# Production settings
PRODUCTION_SETTINGS = {
    "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
    "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
    "PORT": int(os.getenv("PORT", "8080")),
    "GCP_PROJECT_ID": os.getenv("GCP_PROJECT_ID"),
    "GCP_REGION": os.getenv("GCP_REGION", "us-central1"),
    "SERVICE_NAME": os.getenv("SERVICE_NAME", "foodyfix-api"),
    
    # API Keys
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "FIREBASE_PROJECT_ID": os.getenv("FIREBASE_PROJECT_ID"),
    "FIREBASE_PRIVATE_KEY_ID": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "FIREBASE_PRIVATE_KEY": os.getenv("FIREBASE_PRIVATE_KEY"),
    "FIREBASE_CLIENT_EMAIL": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "FIREBASE_CLIENT_ID": os.getenv("FIREBASE_CLIENT_ID"),
    
    # Database (optional)
    "DATABASE_URL": os.getenv("DATABASE_URL"),
    "REDIS_URL": os.getenv("REDIS_URL"),
    
    # Security
    "SECRET_KEY": os.getenv("SECRET_KEY"),
    "CORS_ORIGINS": os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"],
    "WEBHOOK_SECRET": os.getenv("WEBHOOK_SECRET"),
    
    # Monitoring
    "GCP_LOGGING_ENABLED": os.getenv("GCP_LOGGING_ENABLED", "true").lower() == "true",
    "SENTRY_DSN": os.getenv("SENTRY_DSN"),
}

def validate_production_config() -> bool:
    """Validate that all required production settings are present"""
    required_vars = [
        "GEMINI_API_KEY",
        "FIREBASE_PROJECT_ID", 
        "FIREBASE_PRIVATE_KEY",
        "FIREBASE_CLIENT_EMAIL",
        "FIREBASE_CLIENT_ID",
        "GCP_PROJECT_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not PRODUCTION_SETTINGS.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logging.info("✅ All required environment variables are present")
    return True

def get_database_config():
    """Get database configuration based on environment"""
    if PRODUCTION_SETTINGS["DATABASE_URL"]:
        return {
            "url": PRODUCTION_SETTINGS["DATABASE_URL"],
            "pool_size": 10,
            "max_overflow": 20
        }
    else:
        # Fallback to in-memory store for development
        return {
            "type": "memory",
            "warning": "Using in-memory store. Configure DATABASE_URL for production."
        }

def get_redis_config() -> Optional[dict]:
    """Get Redis configuration if available"""
    if PRODUCTION_SETTINGS["REDIS_URL"]:
        return {
            "url": PRODUCTION_SETTINGS["REDIS_URL"],
            "decode_responses": True,
            "health_check_interval": 30
        }
    return None

def get_firebase_config() -> Optional[dict]:
    """Get Firebase configuration if all required vars are present"""
    firebase_vars = [
        "FIREBASE_PROJECT_ID",
        "FIREBASE_PRIVATE_KEY", 
        "FIREBASE_CLIENT_EMAIL",
        "FIREBASE_CLIENT_ID"
    ]
    
    if all(PRODUCTION_SETTINGS.get(var) for var in firebase_vars):
        return {
            "project_id": PRODUCTION_SETTINGS["FIREBASE_PROJECT_ID"],
            "private_key": PRODUCTION_SETTINGS["FIREBASE_PRIVATE_KEY"],
            "client_email": PRODUCTION_SETTINGS["FIREBASE_CLIENT_EMAIL"],
            "client_id": PRODUCTION_SETTINGS["FIREBASE_CLIENT_ID"]
        }
    return None

def setup_production_logging():
    """Configure production logging"""
    log_level = logging.DEBUG if PRODUCTION_SETTINGS["DEBUG"] else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            # Add Cloud Logging handler if enabled
        ]
    )
    
    if PRODUCTION_SETTINGS["GCP_LOGGING_ENABLED"]:
        try:
            from google.cloud import logging as cloud_logging
            cloud_logging.Client()
            logging.info("✅ Google Cloud Logging enabled")
        except ImportError:
            logging.warning("⚠️ Google Cloud Logging not available")
        except Exception as e:
            logging.error(f"❌ Failed to enable Google Cloud Logging: {e}")

def get_cors_origins() -> list:
    """Get CORS origins from environment"""
    return PRODUCTION_SETTINGS["CORS_ORIGINS"]

def is_production() -> bool:
    """Check if running in production mode"""
    return PRODUCTION_SETTINGS["ENVIRONMENT"] == "production"

def get_service_url() -> str:
    """Get the expected service URL"""
    project_id = PRODUCTION_SETTINGS["GCP_PROJECT_ID"]
    region = PRODUCTION_SETTINGS["GCP_REGION"]
    service_name = PRODUCTION_SETTINGS["SERVICE_NAME"]
    return f"https://{service_name}-{random_string()}-{project_id}.{region}.run.app"

def random_string(length: int = 8) -> str:
    """Generate random string for service URL"""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
