# Configuration
$PROJECT_ID = "foodyfix-495510"
$SERVICE_NAME = "foodyfix-portal"
$REGION = "us-central1"
$IMAGE_URL = "gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

Write-Host "🚀 Starting Deployment for $SERVICE_NAME..." -ForegroundColor Cyan

# 1. Enable Required Services
Write-Host "🔧 Enabling Google Cloud Services..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable iam.googleapis.com --project=$PROJECT_ID
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID
gcloud services enable firestore.googleapis.com --project=$PROJECT_ID

# 2. Build and Push Docker Image
Write-Host "📦 Building Docker Image..." -ForegroundColor Yellow
docker build -t $IMAGE_URL .

Write-Host "📤 Pushing Image to Google Container Registry..." -ForegroundColor Yellow
gcloud auth configure-docker --quiet
docker push $IMAGE_URL

# 3. Deploy to Cloud Run
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
    --image=$IMAGE_URL `
    --region=$REGION `
    --platform=managed `
    --allow-unauthenticated `
    --set-env-vars="GCP_LOGGING_ENABLED=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID" `
    --project=$PROJECT_ID

Write-Host "✅ Deployment Complete!" -ForegroundColor Green
gcloud run services describe $SERVICE_NAME --platform=managed --region=$REGION --format='value(status.url)'
