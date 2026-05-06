# FoodyFix – Precision Nutrition & Health Intelligence

## Overview
FoodyFix is a modern, AI‑powered health utility tool that helps users visualize the nutritional impact of their meals, track daily intake, sync food orders, and receive actionable health insights. The platform combines a sleek, premium UI (Tailwind CSS, glass‑morphism, dynamic animations) with a robust FastAPI backend powered by Gemini‑1.5‑Flash for structured nutritional analysis and health forecasting.

---

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation & Run Locally](#installation--run-locally)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Frontend Routes](#frontend-routes)
- [Design System](#design-system)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Features
| Category | Description |
|---|---|
| **Instant Food Analyzer** | Type any food or upload an image – Gemini AI returns a detailed JSON with calories, macros, health grade, benefits, risks, and a healthier alternative. |
| **Dashboard** | Real‑time health gauges, circular credit ring, 7‑day caloric balance chart, AI suggestions, and quick actions. |
| **Order Sync** | Manual order entry or webhook integration (`/api/orders/webhook`) for Swiggy, Zomato, UberEats. Automatic AI analysis of each order. |
| **Health Forecast** | 30‑day weight change projection using the formula `((cal_in - cal_out) * 30) / 7700`. AI‑generated risk level, actionable items, and motivational message. |
| **Smart Reports** | Monthly summary with Chart.js visualisations, AI‑generated headline, biggest win/challenge, and next‑month goal. |
| **FoodyCredits** | Earn credits for healthy meals (high protein, low saturated fat, high grade). Unlock rewards (cheat‑meal, premium recipes, nutrition‑coach session). |
| **Profile / Rewards Page** | Shows user stats, credit ring, reward milestones, recent credit activity, and account settings. |
| **Image Scanner** | Drag‑and‑drop or file upload to `/scan` page. The backend uses Gemini Vision to analyse the image and auto‑log a meal with credits. |
| **Responsive & Premium UI** | Dark‑mode‑compatible, glass‑morphism cards, smooth hover micro‑animations, dynamic hero slider, and custom fonts (Plus Jakarta Sans, Inter). |

---

## Tech Stack
- **Backend**: Python 3.11, FastAPI, Uvicorn, Pydantic
- **AI**: Gemini‑1.5‑Flash (text) & Gemini Vision (image)
- **Frontend**: HTML5, Tailwind CSS (via CDN), Alpine.js for interactivity, Chart.js for charts
- **Styling**: Glass‑morphism, custom colour palette (emerald, amber, slate), premium typography
- **Deployment**: Dockerised for Google Cloud Run (default `PORT=8080`)
- **Data Store**: In‑memory `USER_DATA` dictionary (placeholder – replace with PostgreSQL/Firestore for production)

---

## Installation & Run Locally
```bash
# Clone the repo (assuming you are in the workspace folder)
git clone https://github.com/your-org/foodyfix.git
cd FoodyFix

# Create a virtual environment
python -m venv .venv
source .venv/Scripts/activate   # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Set required environment variables (example using .env file)
copy env.example .env
# Edit .env – set GEMINI_API_KEY and optionally BASE_URL, PORT

# Run the dev server
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```
Open your browser at `http://localhost:8080`.

---

## Environment Variables
| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Your Gemini API key – required for all AI calls. | *(none)* |
| `BASE_URL` | Base URL used in the webhook integration guide (e.g., Cloud Run URL). | `https://your-foodyfix-app.run.app` |
| `PORT` | Port FastAPI binds to (used by Cloud Run). | `8080` |

---

## API Endpoints
| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Guest landing page (`templates/index.html`). |
| `GET` | `/auth` | Placeholder login/signup page. |
| `GET` | `/dashboard` | Main dashboard UI. |
| `GET` | `/orders` | Order management page. |
| `GET` | `/reports` | Monthly reports UI. |
| `GET` | `/profile` | User profile & rewards page. |
| `GET` | `/scan` | Image scanner UI. |
| `POST` | `/api/analyze` | Text‑based food analysis – expects `{food_item, quantity}`. |
| `POST` | `/api/meals` | Log a meal – body `{name, quantity, date?}`. Auto‑calculates credits. |
| `GET` | `/api/meals` | Retrieve all logged meals (optional `date` query). |
| `POST` | `/api/calories-burned` | Log burned calories – body `{date, amount, activity?}`. |
| `GET` | `/api/credits` | Returns current credits, progress percentage, cheat threshold, and reward list. |
| `GET` | `/api/predict` | 30‑day health forecast (uses recent 7‑day data). |
| `GET` | `/api/reports` | Monthly report data, AI‑generated insights. |
| `POST` | `/api/orders` | Manual order entry – AI analyses the food name. |
| `POST` | `/api/orders/webhook` | Webhook endpoint for external order platforms (Swiggy, Zomato, UberEats). |
| `GET` | `/api/orders` | List all orders (filter by `source` & `date`). |
| `GET` | `/api/integration-guide` | Returns JSON with webhook URL, payload example, and required headers. |
| `POST` | `/api/scan` | **Image scanner** – upload `multipart/form-data` with `file`. Returns same JSON as `/api/analyze` plus auto‑log as a meal. |

---

## Frontend Routes
| Route | Template | Key UI Elements |
|---|---|---|
| `/` | `index.html` | Hero slider, feature grid, CTA buttons. |
| `/dashboard` | `dashboard.html` | Health gauge, credit ring, balance chart, AI suggestions, recent meals. |
| `/orders` | `orders.html` | Manual order form, webhook guide, order list. |
| `/reports` | `reports.html` | Chart.js calorie/grade visualisations, AI summary. |
| `/profile` | `profile.html` | Credit ring, reward milestones, recent credit activity, account settings. |
| `/scan` | `scan.html` | Drag‑and‑drop image uploader, result card with grade, benefits, risks, healthier alternative. |

---

## Design System
- **Palette**: Emerald (`#10b981`), Amber (`#fbbf24`), Slate (`#0f172a`), subtle gradients for depth. 
- **Typography**: `Plus Jakarta Sans` (primary), `Inter` (secondary). 
- **Components**: Glass‑card (`bg-white/5` + `backdrop-blur`), circular progress rings, hover‑lift cards, micro‑animations (`transition`, `transform`). 
- **Responsive Layout**: Mobile‑first grid, max‑width `7xl` container, sticky navigation. 
- **Accessibility**: Proper heading hierarchy, ARIA‑friendly button labels, high‑contrast text against glass cards. 

---

## Future Improvements
- **Persisted Database** – Replace in‑memory `USER_DATA` with PostgreSQL or Firestore (auth‑linked). 
- **Firebase Auth Integration** – Real login/signup flow, JWT session management for protected API routes. 
- **CI/CD Pipeline** – GitHub Actions to build Docker image and deploy to Google Cloud Run automatically. 
- **Secret Manager** – Move `GEMINI_API_KEY` to Google Secret Manager for production. 
- **Rate‑Limiting & Security** – Add API key verification for webhook endpoint (`X‑FoodyFix‑Key`). 
- **Unit Tests** – Coverage for API routes, Gemini wrapper, credit calculation logic. 
- **Internationalisation** – Multi‑language support for UI and AI prompts. 

---

## License
MIT © 2026 FoodyFix Team. Feel free to fork, modify, and deploy for personal or commercial use.
