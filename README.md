# Amazon Price Tracker (Multi-User, API-first)

A container-ready Flask API that tracks Amazon product prices, stores history in PostgreSQL, and sends notifications on price drops. The app now supports multiple users. Each user owns products, history, and notification settings. History APIs use product_id.

- API-first service (Flask)
- PostgreSQL storage via SQLAlchemy
- Multi-user domain model (Users own Products; PriceHistory ties to Products; NotificationSettings per User)
- Price history and statistics per product
- Email notifications
- Docker + GitHub Actions + GCP (Cloud Run/GKE) friendly

## Contents
- Features
- Architecture
- Data Model
- Setup (Local)
- Running (Local)
- API Overview
- Environment Variables
- Docker
- CI/CD to GCP (via GitHub Actions)
- Project Structure

---

## Features
- Track multiple Amazon products per user
- Price history and statistics (min, max, average, change)
- Email notifications per user
- REST API with validation
- Dockerized; deployable to Cloud Run/GKE

## Architecture
- Flask API in api/app.py
- Core services in core/
  - price_tracker.py: fetch prices, manage products, notifications (user-scoped)
  - price_history.py: retrieve/manage history (user-scoped, product_id-based)
  - notifications.py: email sending
- Database layer in database/
  - db.py: session and engine
  - models.py: SQLAlchemy models (User, Product, PriceHistory, NotificationSettings)

## Data Model
- users
  - id, email (unique), name, timestamps
- products
  - id, user_id (FK), url, title, threshold, current_price, is_active, timestamps
  - unique constraint: (user_id, url)
- price_history
  - id, product_id (FK), price, timestamp
- notification_settings
  - id, user_id (unique FK), email, phone_number, timestamps

## Setup (Local)
1) Python dependencies
   ```bash
   pip install -r requirements.txt
   ```

2) Configure environment
   Create .env (see Environment Variables section):
   - DATABASE_URL is required (PostgreSQL)
   - EMAIL_ID/EMAIL_PASS/SMTP_SERVER/SMTP_PORT for email notifications

3) Initialize database tables
   The app auto-creates tables on first run. For schema changes from older versions, drop and recreate or migrate.

## Running (Local)
- API server
  ```bash
  python run_api.py
  ```
  Default: http://localhost:5000

- Tracker loop for a specific user (optional utility)
  ```bash
  python run_tracker.py <user_id>
  ```

## API Overview
All user-specific endpoints require user_id. Price history uses product_id.

Health
- GET /api/health

Users
- POST /api/users
  - Body: { email: string, name?: string }
- GET /api/users[?email=...]
- GET /api/users/{user_id}
- DELETE /api/users/{user_id}

Products
- GET /api/products?user_id={int}
- POST /api/products
  - Body: { user_id: int, url: string, threshold: number }
- DELETE /api/products/{product_id}?user_id={int}
- POST /api/products/check
  - Body: { user_id: int, url: string }
- POST /api/products/update-all?user_id={int}
  - Or in body: { user_id: int }

Notifications
- GET /api/notifications?user_id={int}
- PUT /api/notifications
  - Body: { user_id: int, email?: string, phone_number?: string }
- POST /api/notifications/send (alias: /api/notify)
  - Body: { user_id: int, title: string, url: string }

Tracking
- POST /api/track/check
  - user_id via query or body

Price History (product_id-based)
- GET /api/history?user_id={int}[&limit={int}]
  - All products’ histories for the user (keys by product URL)
- GET /api/history/by-id?user_id={int}&product_id={int}[&limit={int}][&stats=true|false]
  - stats=true -> statistics; otherwise entries + product info
- GET /api/history/stats/by-id?user_id={int}&product_id={int}
- GET /api/history/{product_id}?user_id={int}[&limit={int}][&stats=true|false]
- GET /api/history/{product_id}/stats?user_id={int}
- DELETE /api/history/{product_id}?user_id={int}

Notes
- URL-based history endpoints have been replaced by product_id-based endpoints per current logic.

## Environment Variables (.env)
Required
- DATABASE_URL=postgresql://USER:PASS@HOST:PORT/DB
- CORS_ORIGIN=* (or your frontend origin)

Email (optional but recommended for alerts)
- EMAIL_ID
- EMAIL_PASS
- SMTP_SERVER (e.g., smtp.gmail.com)
- SMTP_PORT (e.g., 587 or 465)

## Docker
Build & run locally
```bash
docker build -t amazon-price-tracker:local .
# Run API on port 5000
docker run -p 5000:5000 --env-file .env amazon-price-tracker:local
```

## CI/CD to GCP via GitHub Actions
Overview
- Push to GitHub main triggers GitHub Actions workflow to:
  - Authenticate to GCP (via service account key)
  - Build Docker image
  - Push to Artifact Registry (or GCR)
  - Deploy to Cloud Run (or apply to GKE)

Secrets (in GitHub repo -> Settings -> Secrets and variables -> Actions)
- GCP_PROJECT_ID
- GCP_REGION (e.g., us-central1)
- GCP_SA_KEY (JSON contents of service account key)
- SERVICE_NAME (e.g., amazon-price-tracker)
- REGISTRY_REPO (Artifact Registry repo name, e.g., app-images)
- App env vars: DATABASE_URL, CORS_ORIGIN, EMAIL_ID, EMAIL_PASS, SMTP_SERVER, SMTP_PORT

Example Cloud Run workflow (.github/workflows/deploy-cloudrun.yml)
```yaml
name: Build and Deploy to Cloud Run
on:
  push:
    branches: [ "main" ]
env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: ${{ secrets.GCP_REGION }}
  SERVICE_NAME: ${{ secrets.SERVICE_NAME }}
  REPO_NAME: ${{ secrets.REGISTRY_REPO }}
  IMAGE: ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/${{ secrets.REGISTRY_REPO }}/${{ secrets.SERVICE_NAME }}
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: google-github-actions/setup-gcloud@v2
      with:
        project_id: ${{ env.PROJECT_ID }}
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        export_default_credentials: true
    - run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev --quiet
    - name: Build and push image
      run: |
        SHORT_SHA=$(git rev-parse --short HEAD)
        docker build -t $IMAGE:$SHORT_SHA -t $IMAGE:latest .
        docker push $IMAGE:$SHORT_SHA
        docker push $IMAGE:latest
    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy $SERVICE_NAME \
          --image $IMAGE:latest \
          --region $REGION \
          --platform managed \
          --allow-unauthenticated \
          --port 5000 \
          --set-env-vars "CORS_ORIGIN=${{ secrets.CORS_ORIGIN }},DATABASE_URL=${{ secrets.DATABASE_URL }},EMAIL_ID=${{ secrets.EMAIL_ID }},EMAIL_PASS=${{ secrets.EMAIL_PASS }},SMTP_SERVER=${{ secrets.SMTP_SERVER }},SMTP_PORT=${{ secrets.SMTP_PORT }}"
```

GCP prerequisites
- Enable APIs: artifactregistry.googleapis.com, run.googleapis.com, cloudbuild.googleapis.com
- Artifact Registry repo created: e.g., app-images in REGION
- Service Account with roles: artifactregistry.writer, run.admin, iam.serviceAccountUser

## Project Structure
```
Amazon_Price_Tracker/
├── api/
│   ├── app.py               # Flask API
│   └── schemas.py           # Marshmallow schemas
├── core/
│   ├── price_tracker.py     # User-scoped product + notifications
│   ├── price_history.py     # User-scoped history (product_id-based)
│   ├── notifications.py     # Email sender
│   └── url_utils.py
├── database/
│   ├── db.py                # Engine and sessions
│   ├── models.py            # User, Product, PriceHistory, NotificationSettings
│   └── test_connection.py
├── Dockerfile
├── docker-compose.yml
├── k8s-deployment.yaml
├── run_api.py
├── run_tracker.py
├── requirements.txt
├── init_db.py
└── README.md
```

## Notes
- All API operations are scoped by user_id.
- History endpoints require product_id.
- For legacy deployments, re-create tables or migrate to the new schema.
- Consider using gunicorn for production serving behind Cloud Run; development uses Flask’s built-in server.
