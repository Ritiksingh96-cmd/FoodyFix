# 🚀 FoodyFix Deployment Guide

## Google Cloud Run Deployment

### Prerequisites
- Google Cloud Project with billing enabled
- Google Cloud SDK installed and configured
- Docker installed locally

### Environment Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/foodyfix.git
   cd foodyfix
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

3. **Required Environment Variables**
   - `GEMINI_API_KEY`: Your Gemini API key
   - `FIREBASE_PROJECT_ID`: Firebase project ID
   - `FIREBASE_PRIVATE_KEY`: Firebase service account private key
   - `FIREBASE_CLIENT_EMAIL`: Firebase service account email
   - `FIREBASE_CLIENT_ID`: Firebase client ID
   - `GCP_PROJECT_ID`: Google Cloud project ID

### Firebase Setup
1. Create a Firebase project at https://console.firebase.google.com
2. Enable Authentication (Email/Password and Google providers)
3. Go to Project Settings > Service Accounts
4. Generate a new private key and save the JSON file
5. Copy the credentials to your .env file

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### Google Cloud Deployment

#### Option 1: Using gcloud CLI
```bash
# Build and deploy
gcloud run deploy foodyfix-api \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars "$(cat .env | grep -v '^#' | xargs)"
```

#### Option 2: Using GitHub Actions (Recommended)
1. **Add GitHub Secrets**:
   - `GCP_PROJECT_ID`: Your Google Cloud project ID
   - `GCP_SA_KEY`: Base64 encoded service account key
   - `GEMINI_API_KEY`: Your Gemini API key
   - `FIREBASE_PROJECT_ID`: Firebase project ID
   - `FIREBASE_PRIVATE_KEY_ID`: Firebase private key ID
   - `FIREBASE_PRIVATE_KEY`: Firebase private key
   - `FIREBASE_CLIENT_EMAIL`: Firebase service account email
   - `FIREBASE_CLIENT_ID`: Firebase client ID

2. **Push to main branch**:
   ```bash
   git add .
   git commit -m "Deploy to production"
   git push origin main
   ```

### Monitoring and Logs
- **Application logs**: Google Cloud Logging
- **Error tracking**: Sentry (if configured)
- **Health checks**: `/api/health` endpoint
- **API documentation**: `/api/docs` (Swagger UI)

### Database Migration (Production)
For production use, replace the in-memory store with a proper database:

#### PostgreSQL Setup
```bash
# Create Cloud SQL instance
gcloud sql instances create foodyfix-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Set DATABASE_URL in .env
DATABASE_URL=postgresql://username:password@host:5432/foodyfix
```

#### Redis for Sessions
```bash
# Create Memorystore instance
gcloud redis instances create foodyfix-cache \
  --size=1 \
  --region=us-central1

# Set REDIS_URL in .env
REDIS_URL=redis://host:6379
```

### Security Configuration
- **CORS**: Configure allowed origins in environment
- **Rate limiting**: Implement with Redis
- **API keys**: Use Google Secret Manager for production
- **HTTPS**: Automatic with Cloud Run

### Performance Optimization
- **Caching**: Redis for frequently accessed data
- **CDN**: Cloud CDN for static assets
- **Compression**: Enabled by default in Cloud Run
- **Scaling**: Automatic scaling configured (1-10 instances)

### Troubleshooting

#### Common Issues
1. **Firebase Authentication Errors**
   - Verify service account credentials
   - Check Firebase project configuration
   - Ensure proper token format in frontend

2. **Deployment Failures**
   - Check environment variables
   - Verify Docker build
   - Review Cloud Run logs

3. **Performance Issues**
   - Monitor memory usage
   - Check API response times
   - Review scaling configuration

#### Health Check Response
```json
{
  "status": "healthy",
  "timestamp": "2026-05-06T15:30:00.000Z",
  "version": "1.0.0",
  "environment": "production",
  "system": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "memory_available_gb": 0.85
  },
  "services": {
    "firebase": "connected",
    "gemini_api": "configured"
  }
}
```

### Rollback
```bash
# List deployments
gcloud run services list

# Rollback to previous version
gcloud run services update-traffic foodyfix-api \
  --to-revisions=REVISION_ID \
  --region=us-central1
```

## Support
- **Documentation**: Check API docs at `/api/docs`
- **Monitoring**: Google Cloud Console
- **Logs**: `gcloud logs read "resource.type=cloud_run_revision"`
- **Health**: Application health at `/api/health`
