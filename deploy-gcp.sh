#!/bin/bash

# Google Cloud Deployment Script for FoodyFix
# This script handles the complete deployment process

set -e

echo "🚀 Deploying FoodyFix to Google Cloud Run..."

# Configuration
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="us-central1"
SERVICE_NAME="foodyfix-api"
REPOSITORY="foodyfix-repo"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ No project ID provided. Usage: ./deploy-gcp.sh PROJECT_ID"
    echo "Or set default project: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Using project: $PROJECT_ID"
echo "📍 Region: $REGION"
echo "🔧 Service: $SERVICE_NAME"

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository..."
gcloud artifacts repositories create $REPOSITORY \
    --repository-format=docker \
    --location=$REGION \
    --project=$PROJECT_ID \
    --description="FoodyFix Docker images" || echo "Repository already exists"

# Build and push Docker image
echo "🐳 Building Docker image..."
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/foodyfix"
IMAGE_TAG="${IMAGE_NAME}:$(git rev-parse --short HEAD)"

# Configure Docker for Google Artifact Registry
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build the image
docker build -t $IMAGE_TAG .
docker tag $IMAGE_TAG ${IMAGE_NAME}:latest

# Push the image
echo "📤 Pushing Docker image..."
docker push $IMAGE_TAG
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_TAG \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=10 \
    --set-env-vars="ENVIRONMENT=production" \
    --set-env-vars="PORT=8080" \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID" \
    --set-env-vars="GCP_LOGGING_ENABLED=true"

# Grant public access
echo "🔓 Granting public access..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format='value(status.url)')

echo ""
echo "✅ Deployment successful!"
echo "📍 Service URL: $SERVICE_URL"
echo "📊 API Documentation: $SERVICE_URL/api/docs"
echo "🏥 Health Check: $SERVICE_URL/api/health"

# Test the deployment
echo "🧪 Testing deployment..."
sleep 10  # Wait for service to be ready

# Test health endpoint
if curl -f "$SERVICE_URL/api/health" > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check failed. Check logs with: gcloud logs read 'resource.type=cloud_run_revision' --limit=50"
fi

# Show logs command
echo ""
echo "📋 Useful commands:"
echo "View logs: gcloud logs read 'resource.type=cloud_run_revision' --limit=50"
echo "List services: gcloud run services list --region=$REGION"
echo "Delete deployment: gcloud run services delete $SERVICE_NAME --region=$REGION"
echo "Update deployment: gcloud run services update $SERVICE_NAME --region=$REGION --image=$IMAGE_TAG"

echo ""
echo "🎉 FoodyFix is now live at: $SERVICE_URL"
