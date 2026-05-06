# 🚀 FoodyFix Setup Guide for GitHub Repository

## Quick Setup for Your Repository

### 1. 📋 Fill in Your .env File

Edit the `.env` file with your actual API keys and configuration:

```bash
# Required: Get from Gemini AI Console
GEMINI_API_KEY=AIzaSyCxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Required: Get from Firebase Console
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKwggSiAgEAAoIBAQwCAQAAggE
YOUR_ACTUAL_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id

# Required: Get from Google Cloud Console
GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# Optional: Update with your actual deployment URL
BASE_URL=https://foodyfix-xxxxxxxxx-uc.a.run.app
```

### 2. 🔧 Firebase Setup

1. **Create Firebase Project**:
   - Go to https://console.firebase.google.com
   - Create new project or use existing one
   - Note the **Project ID**

2. **Enable Authentication**:
   - Go to Authentication > Sign-in method
   - Enable Email/Password and Google providers
   - Copy **Web API Key** from settings

3. **Create Service Account**:
   - Go to Project Settings > Service accounts
   - Click "Create Service Account"
   - Name it "firebase-admin-sdk"
   - Grant "Firebase Admin" role
   - Create and download JSON key
   - Copy values from JSON to `.env` file

### 3. ☁️ Google Cloud Setup

1. **Enable APIs**:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```

2. **Create Service Account for Deployment**:
   ```bash
   gcloud iam service-accounts create foodyfix-deployer \
       --display-name="FoodyFix Deployer" \
       --description="Service account for deploying FoodyFix"
   ```

3. **Grant Permissions**:
   ```bash
   PROJECT_ID=your-gcp-project-id
   SA_EMAIL=foodyfix-deployer@$PROJECT_ID.iam.gserviceaccount.com
   
   # Cloud Run permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="serviceAccount:$SA_EMAIL" \
       --role="roles/run.admin"
   
   # Cloud Build permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="serviceAccount:$SA_EMAIL" \
       --role="roles/cloudbuild.builds.builder"
   ```

### 4. 🐙 GitHub Repository Setup

1. **Add to GitHub**:
   - Push all files to your repository: https://github.com/Ritiksingh96-cmd/FoodyFix
   - Make sure `.env` is included (or use GitHub secrets)

2. **Configure GitHub Secrets**:
   Go to your repository > Settings > Secrets and variables > Actions
   
   Add these secrets:
   ```
   GCP_PROJECT_ID=your-gcp-project-id
   GEMINI_API_KEY=your_gemini_api_key
   FIREBASE_PROJECT_ID=your_firebase_project_id
   FIREBASE_PRIVATE_KEY_ID=your_private_key_id
   FIREBASE_PRIVATE_KEY=your_firebase_private_key
   FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
   FIREBASE_CLIENT_ID=your_client_id
   ```

3. **Enable GitHub Actions**:
   - Go to Settings > Actions > General
   - Allow "Actions" to run
   - Approve the workflow

### 5. 🚀 Deploy Options

#### Option A: Automated GitHub Actions (Recommended)
```bash
# Just push to main branch
git add .
git commit -m "Configure for production deployment"
git push origin main
```

#### Option B: Manual Deployment
```bash
# Make setup script executable
chmod +x setup-gcp.sh

# Run setup
./setup-gcp.sh

# Deploy
./deploy-gcp.sh
```

### 6. 🔍 Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

Test endpoints:
- Health: http://localhost:8080/api/health
- API Docs: http://localhost:8080/api/docs
- Frontend: http://localhost:8080

### 7. 📊 Monitoring After Deployment

Once deployed, monitor:
- **Application Logs**: Google Cloud Console > Logging
- **Service Health**: `https://your-url/api/health`
- **Error Tracking**: Check Cloud Run logs
- **Performance**: Cloud Run metrics

### 8. 🔧 Troubleshooting

#### Common Issues and Solutions:

**Firebase Authentication Errors**:
```bash
# Check service account permissions
gcloud projects get-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL"

# Test Firebase connection
python -c "
import firebase_admin
from firebase_admin import credentials
try:
    creds = credentials.Certificate({
        'type': 'service_account',
        'project_id': '$FIREBASE_PROJECT_ID',
        'private_key': '$FIREBASE_PRIVATE_KEY'.replace('\\\\n', '\\n'),
        'client_email': '$FIREBASE_CLIENT_EMAIL',
        'client_id': '$FIREBASE_CLIENT_ID'
    })
    app = firebase_admin.initialize_app(credential=creds)
    print('✅ Firebase connection successful')
except Exception as e:
    print(f'❌ Firebase error: {e}')
"
```

**Google Cloud Deployment Errors**:
```bash
# Check API enablement
gcloud services list --enabled --project=$PROJECT_ID

# Check service account permissions
gcloud iam service-accounts describe foodyfix-deployer@$PROJECT_ID.iam.gserviceaccount.com

# View build logs
gcloud builds list --limit=10
```

**Docker Build Issues**:
```bash
# Test Docker build locally
docker build -t foodyfix-test .

# Run container locally
docker run -p 8080:8080 foodyfix-test
```

### 9. 📱 Environment Variables Reference

| Variable | Required | Description | Where to Get |
|-----------|-----------|-------------|---------------|
| `GEMINI_API_KEY` | ✅ | Gemini AI API key | Google AI Studio |
| `FIREBASE_PROJECT_ID` | ✅ | Firebase project ID | Firebase Console |
| `FIREBASE_PRIVATE_KEY` | ✅ | Firebase service account key | Firebase Console |
| `FIREBASE_CLIENT_EMAIL` | ✅ | Firebase service email | Firebase Console |
| `FIREBASE_CLIENT_ID` | ✅ | Firebase client ID | Firebase Console |
| `GOOGLE_CLOUD_PROJECT` | ✅ | Google Cloud project ID | Google Cloud Console |
| `ENVIRONMENT` | ❌ | Set to "production" automatically | - |
| `PORT` | ❌ | Set to 8080 automatically | - |

### 10. 🎯 Next Steps

1. **Fill in actual values** in `.env` file
2. **Set up Firebase project** and get credentials
3. **Configure Google Cloud** project and service accounts
4. **Push to GitHub** and add secrets
5. **Deploy and monitor** your application

### 📞 Support

If you encounter issues:
1. Check the logs: `gcloud logs read "resource.type=cloud_run_revision"`
2. Verify environment variables are set correctly
3. Check API quotas in Google Cloud Console
4. Review deployment logs in GitHub Actions

**Your application is now ready for production deployment!** 🚀
