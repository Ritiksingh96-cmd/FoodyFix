# 🚀 FoodyFix Production & Deployment Guide

This guide explains how to set up the automated deployment pipeline for **FoodyFix** using GitHub Actions and Google Cloud Run.

## 1. GitHub Secrets Configuration
To enable the automated deployment workflow (`.github/workflows/deploy.yml`), you must add the following secrets to your GitHub repository:

1.  **`GCP_PROJECT_ID`**: Your Google Cloud Project ID.
2.  **`GCP_SA_KEY`**: The JSON key of a Google Cloud Service Account with `Cloud Run Admin` and `Storage Admin` permissions.
3.  **`GEMINI_API_KEY`**: Your Google AI Studio API Key.

### How to add secrets:
- Go to your repo: `https://github.com/Ritiksingh96-cmd/FoodyFix`
- Click **Settings** > **Secrets and variables** > **Actions**
- Click **New repository secret** for each item above.

## 2. Firebase Authentication Setup
The signup/login page is ready for Firebase. To activate it:
1.  Go to the [Firebase Console](https://console.firebase.google.com/).
2.  Create a new project (or use your existing Google Cloud project).
3.  Add a **Web App** to the project.
4.  Copy the `firebaseConfig` object.
5.  Paste it into `templates/auth.html` (lines 142-149).
6.  Enable **Google Sign-In** in the Firebase Auth "Sign-in method" tab.

## 3. Deployment Pipeline
Once the secrets are set:
- Every time you `git push` to the `main` branch, GitHub will:
  1.  Build a new Docker container.
  2.  Push it to Google Container Registry.
  3.  Deploy it to **Google Cloud Run**.
  4.  Inject your `GEMINI_API_KEY` automatically.

## 4. Local Development
To run locally:
```bash
pip install -r requirements.txt
python main.py
```
Visit `http://localhost:8080`.

---
**FoodyFix Health Systems** — *Precision Nutrition for the Digital Age.*
