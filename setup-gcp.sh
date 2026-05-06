#!/bin/bash

# Google Cloud Setup Script for FoodyFix Deployment
# This script sets up all necessary GCP services and permissions

set -e

echo "🚀 Setting up FoodyFix on Google Cloud..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install it first: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No project selected. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Using project: $PROJECT_ID"

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create service account for Cloud Run
echo "👤 Creating service account..."
SA_NAME="foodyfix-cloudrun"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

gcloud iam service-accounts create $SA_NAME \
    --display-name="FoodyFix Cloud Run Service Account" \
    --description="Service account for FoodyFix Cloud Run deployment"

# Grant necessary permissions to service account
echo "🔐 Granting permissions to service account..."

# Cloud Run permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.admin"

# Cloud Build permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudbuild.builds.builder"

# Artifact Registry permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/artifactregistry.writer"

# Secret Manager permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

# Firestore permissions (for Firebase)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/datastore.user"

# Create service account key
echo "🔑 Creating service account key..."
gcloud iam service-accounts keys create $SA_NAME \
    --key-file=foodyfix-service-account.json

# Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository..."
gcloud artifacts repositories create foodyfix-repo \
    --repository-format=docker \
    --location=us-central1

# Set up Cloud SQL (optional - for production database)
echo "🗄️ Setting up Cloud SQL (optional)..."
read -p "Do you want to create a Cloud SQL instance? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    gcloud sql instances create foodyfix-db \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=us-central1 \
        --authorized-networks=0.0.0.0/0 \
        --storage-auto-increase \
        --backup-start-time=02:00
    
    echo "📝 Creating database user..."
    gcloud sql users create foodyfix \
        --instance=foodyfix-db \
        --password=FOODYFIX_DB_PASSWORD_2026
    
    echo "🗄️ Cloud SQL instance created. Connection details:"
    echo "   Instance: foodyfix-db"
    echo "   Region: us-central1"
    echo "   User: foodyfix"
    echo "   Note: Save the password securely!"
fi

# Create Cloud Storage bucket (for static assets)
echo "🪣 Creating Cloud Storage bucket..."
BUCKET_NAME="foodyfix-static-$PROJECT_ID"
gsutil mb -l us-central1 gs://$BUCKET_NAME

# Set up logging
echo "📊 Setting up logging..."
gcloud logging sinks create foodyfix-logs \
    --logging.googleapis.com/projects/$PROJECT_ID \
    --log-filter='resource.type="cloud_run_revision"'

# Store secrets in Secret Manager
echo "🔐 Setting up secrets..."
echo "Please enter your Firebase configuration:"

read -p "Firebase Project ID: " FIREBASE_PROJECT_ID
read -p "Firebase Private Key ID: " FIREBASE_PRIVATE_KEY_ID
read -p "Firebase Client Email: " FIREBASE_CLIENT_EMAIL
read -p "Firebase Client ID: " FIREBASE_CLIENT_ID
read -p "Gemini API Key: " GEMINI_API_KEY

# Create secrets
echo "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo "$FIREBASE_PROJECT_ID" | gcloud secrets create FIREBASE_PROJECT_ID --data-file=-
echo "$FIREBASE_PRIVATE_KEY_ID" | gcloud secrets create FIREBASE_PRIVATE_KEY_ID --data-file=-
echo "$FIREBASE_CLIENT_EMAIL" | gcloud secrets create FIREBASE_CLIENT_EMAIL --data-file=-
echo "$FIREBASE_CLIENT_ID" | gcloud secrets create FIREBASE_CLIENT_ID --data-file=-

# Grant secret access to service account
for secret in GEMINI_API_KEY FIREBASE_PROJECT_ID FIREBASE_PRIVATE_KEY_ID FIREBASE_CLIENT_EMAIL FIREBASE_CLIENT_ID; do
    gcloud secrets add-iam-policy-binding $secret \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor"
done

echo "✅ Google Cloud setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update your .env file with the secrets"
echo "2. Deploy using: gcloud run deploy foodyfix --image gcr.io/$PROJECT_ID/foodyfix:latest --region us-central1 --allow-unauthenticated"
echo "3. Or use GitHub Actions with the service account key: foodyfix-service-account.json"
echo ""
echo "🔗 Useful commands:"
echo "- View logs: gcloud logs read 'resource.type=cloud_run_revision'"
echo "- List services: gcloud run services list"
echo "- Get service URL: gcloud run services describe foodyfix --region us-central1 --format='value(status.url)'"
