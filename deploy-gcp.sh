#!/bin/bash

# Configuration
PROJECT_ID="foodyfix-eef1f"
SERVICE_NAME="foodyfix-portal"
REGION="us-central1"
IMAGE_URL="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

echo "🚀 Starting Deployment for $SERVICE_NAME..."

# 1. Enable Required Services
echo "🔧 Enabling Google Cloud Services..."
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable iam.googleapis.com --project=$PROJECT_ID
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID
gcloud services enable firestore.googleapis.com --project=$PROJECT_ID

# 2. Build and Push Docker Image
echo "📦 Building Docker Image..."
docker build -t $IMAGE_URL .

echo "📤 Pushing Image to Google Container Registry..."
gcloud auth configure-docker --quiet
docker push $IMAGE_URL

# 3. Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_URL \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --set-env-vars="GCP_LOGGING_ENABLED=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --project=$PROJECT_ID

echo "✅ Deployment Complete!"
gcloud run services describe $SERVICE_NAME --platform=managed --region=$REGION --format='value(status.url)'
