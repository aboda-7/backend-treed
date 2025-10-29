# Tree-D Backend

A FastAPI-based backend service for a museum audio guide application that tracks visitor interactions with artifacts through QR code scans and provides analytics on audio completion rates.

## Overview

Tree-D Backend is a RESTful API that powers an interactive museum experience. The system:
- Tracks visitor scans of museum artifact QR codes
- Records multi-language audio playback sessions
- Calculates completion rates based on listening behavior (90% threshold)
- Provides secure analytics endpoints for museum administrators
- Supports 24 artifacts across 10 languages

The backend integrates with Firebase for authentication and data storage, and is designed for serverless deployment on Vercel.

## File and Directory Structure

```
backend-treed/
├── main.py                 # Main FastAPI application and all endpoints
├── requirements.txt        # Python dependencies
├── vercel.json            # Vercel deployment configuration
├── .env                   # Environment variables
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Firebase project with Firestore enabled
- Firebase service account credentials (JSON)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI |
| **Web Server** | Uvicorn (ASGI) |
| **Database** | Firebase Firestore (NoSQL) |
| **Authentication** | Firebase Auth (JWT tokens) |
| **Deployment** | Vercel Serverless |
| **Language** | Python 3.9+ |

**Key Dependencies:**
- `fastapi` - Modern web framework
- `uvicorn` - Lightning-fast ASGI server
- `firebase-admin` - Firebase SDK for Python
- `python-dotenv` - Environment variable management

## Local Development

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend-treed
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv

   # On macOS/Linux:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   FIREBASE_CREDENTIALS={"type":"service_account","project_id":"project-id",...}
   ```

   To obtain Firebase credentials:
   1. Go to Firebase Console → Project Settings → Service Accounts
   2. Click "Generate New Private Key"
   3. Copy the entire JSON content into the `FIREBASE_CREDENTIALS` variable as a single line

### Build and Run

**Development server with hot reload:**
```bash
python main.py
```
The server will start on `http://0.0.0.0:8000`

**Alternative using uvicorn directly:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode (without reload):**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Testing Endpoints

#### Public Endpoints (No Authentication Required)

**1. Health Check - Get Server Time**
```bash
curl http://localhost:8000/gettime
```

**2. Submit Scan Data**
```bash
curl -X POST http://localhost:8000/postdata \
  -H "Content-Type: application/json" \
  -d '{
    "id": "device-123",
    "statue": "Ain Ghazal",
    "language": "English"
  }'
```

**Sample Response:**
```json
{
  "message": "Incremented artifacts.st1.en"
}
```

#### Protected Endpoints (Authentication Required)

First, obtain a Firebase ID token from the client app. Then:

**3. Get All Scan Data**
```bash
curl http://localhost:8000/getdata \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

**4. Get Completion Rates**
```bash
curl http://localhost:8000/analytics/completion-rates \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

**5. Get Completion Summary**
```bash
curl http://localhost:8000/analytics/completion-summary \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

## Testing

### Unit Testing

Currently, this project does not have automated tests. To add unit testing:

**1. Install testing dependencies:**
```bash
pip install pytest pytest-asyncio httpx
```

**2. Create test file** (`test_main.py`):
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_time():
    response = client.get("/gettime")
    assert response.status_code == 200
    assert "current_time" in response.json()

def test_postdata():
    response = client.post("/postdata", json={
        "id": "test-device",
        "statue": "Ain Ghazal",
        "language": "English"
    })
    assert response.status_code == 200
    assert "message" in response.json()
```

**3. Run tests:**
```bash
pytest
```

### Manual Testing Checklist

- [ ] Server starts without errors
- [ ] `/gettime` returns current timestamp
- [ ] `/postdata` accepts scan data and increments counters
- [ ] Protected endpoints reject requests without auth token
- [ ] Protected endpoints accept valid Firebase tokens
- [ ] Completion rate calculation returns expected results

## Configuration

### CORS (Cross-Origin Resource Sharing)

CORS is configured in `main.py` lines 22-31. Currently allowed origins:

- `http://localhost:3000` - Local development
- `https://tree-d-dashboard.vercel.app` - Production dashboard

**To add a new allowed origin:**

Edit the `allow_origins` list:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://tree-d-dashboard.vercel.app",
        "https://new-domain.com",  # Add new domains here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Adding New Artifacts

1. Add to `STATUE_TO_SLOT` dictionary (main.py:71-94):
   ```python
   "New Artifact Name": "st25",
   ```

2. Add audio lengths for all languages in `AUDIO_LENGTHS` (main.py:111-135):
   ```python
   "st25": {
       "ar": 90, "en": 95, "fr": 98, "sp": 100,
       "de": 93, "ja": 105, "ko": 102, "ru": 97,
       "nl": 94, "zh": 101
   },
   ```

### Adding New Languages

1. Add to `LANG_TO_KEY` dictionary (main.py:96-107):
   ```python
   "Italian": "it",
   ```

2. Update all entries in `AUDIO_LENGTHS` to include the new language code

## Deployment

### Deploy to Vercel (Current Configuration)

**1. Install Vercel CLI:**
```bash
npm i -g vercel
```

**2. Login to Vercel:**
```bash
vercel login
```

**3. Deploy:**
```bash
vercel
```

**4. Set environment variables:**
```bash
vercel env add FIREBASE_CREDENTIALS
```
Paste the Firebase credentials JSON when prompted.

**5. Deploy to production:**
```bash
vercel --prod
```

The `vercel.json` configuration automatically handles routing all requests to `main.py`.

### Deploy to Firebase Cloud Functions

**1. Install Firebase CLI:**
```bash
npm install -g firebase-tools
```

**2. Initialize Firebase:**
```bash
firebase login
firebase init functions
```
- Select Python as the language
- Select the Firebase project

**3. Modify project structure:**

Create `functions/main.py` with the FastAPI app and add:
```python
from firebase_functions import https_fn
from firebase_admin import initialize_app

initialize_app()

@https_fn.on_request()
def api(req: https_fn.Request) -> https_fn.Response:
    return app(req)
```

**4. Update `functions/requirements.txt`:**
```txt
fastapi
firebase-admin
firebase-functions
python-dotenv
```

**5. Deploy:**
```bash
firebase deploy --only functions
```

**6. Set environment variables:**
```bash
firebase functions:config:set firebase.credentials="$(cat service-account.json)"
```

### Deploy to Firebase App Engine

**1. Create `app.yaml`:**
```yaml
runtime: python39

env_variables:
  FIREBASE_CREDENTIALS: "firebase-credentials-json-here"

entrypoint: uvicorn main:app --host 0.0.0.0 --port 8080
```

**2. Deploy:**
```bash
gcloud app deploy
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These provide interactive API documentation automatically generated by FastAPI.

## Data Flow

```
QR Scan → Mobile App → POST /postdata → Firestore
                                          ├─ stored_data1 (raw data)
                                          ├─ stored_data2 (counters)
                                          └─ scan_events (timestamps)

Dashboard → GET /analytics/completion-rates → Calculate based on
                                              scan_events timestamps
```

## Support

For issues or questions:
1. Check the API documentation at `http://localhost:8000/docs`
2. Review logs in Vercel dashboard (for deployment issues)
3. Check Firebase Console for database/auth issues

## Future Work

<details>
<summary><strong>Code Structure Refactoring</strong></summary>

As the codebase grows beyond 300-400 lines, refactoring into a modular structure improves maintainability, testability, and scalability.

### Recommended Project Structure

```
backend-treed/
├── app/
│   ├── __init__.py           # Makes it a package
│   ├── main.py               # FastAPI app initialization, includes routers
│   ├── config.py             # Configuration and constants
│   ├── dependencies.py       # Shared dependencies (auth middleware)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic models for request/response
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── public.py         # Public endpoints (/gettime, /postdata)
│   │   ├── analytics.py      # Analytics endpoints
│   │   └── admin.py          # Admin endpoints (/migrate, etc.)
│   │
│   └── services/
│       ├── __init__.py
│       ├── firebase.py       # Firebase initialization and operations
│       └── analytics.py      # Analytics calculation logic
│
├── tests/
│   ├── __init__.py
│   ├── test_public.py
│   ├── test_analytics.py
│   └── test_auth.py
│
├── requirements.txt
├── vercel.json
├── .env
└── README.md
```

### Benefits of Modular Structure

**1. Separation of Concerns**
- Configuration separate from business logic
- Routes grouped by functionality
- Services handle complex business logic

**2. Testability**
- Easy to mock individual components
- Test routes independently
- Test business logic without FastAPI overhead

**3. Scalability**
- Easy to add new endpoints without touching existing code
- Multiple developers can work on different files
- Reduces merge conflicts

**4. Maintainability**
- Find code faster (know exactly where to look)
- Easier to understand what each file does
- Clearer responsibilities

**5. Reusability**
- Services can be imported and used in multiple routes
- Configuration can be shared across the application
- Dependencies can be reused

</details>
<details>
<summary><strong>Containerization</strong></summary>

Running the API in Docker containers provides consistency across development, staging, and production environments. This section builds upon the **Code Structure Refactoring** approach, using the modular `app/` directory structure.

### Directory Structure with Docker

```
backend-treed/
├── app/                    # Modular application structure (from refactoring)
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── models/
│   ├── routers/
│   └── services/
├── tests/
├── Dockerfile              # Production-ready Docker image
├── docker-compose.yml      # Local development setup
├── .dockerignore          # Files to exclude from Docker build
├── requirements.txt
└── .env
```

### Sample Dockerfile (Multi-stage Build)

```dockerfile
# Dockerfile
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (modular structure)
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/gettime')"

# Run application (note: app.main:app for modular structure)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tree-d-backend
    ports:
      - "8000:8000"
    environment:
      - FIREBASE_CREDENTIALS=${FIREBASE_CREDENTIALS}
    env_file:
      - .env
    volumes:
      # Mount entire app directory for hot reload during development
      - ./app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/gettime"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  default:
    name: tree-d-network
```

### .dockerignore File

```
# .dockerignore
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build

# Virtual environments
venv/
env/
ENV/

# IDEs
.idea/
.vscode/
*.swp

# Version control
.git
.gitignore

# Environment files (will be passed as env vars)
.env

# Documentation
*.md
README.md
CLAUDE.md

# CI/CD
.github/
terraform/

# Testing
.pytest_cache/
.coverage
htmlcov/

# macOS
.DS_Store
```

### Docker Commands

#### Build the Docker Image

```bash
# Build production image
docker build -t tree-d-backend:latest .

# Build with specific tag
docker build -t tree-d-backend:v1.0.0 .
```

#### Run Container Directly

```bash
# Run container with environment variables
docker run -d \
  --name tree-d-backend \
  -p 8000:8000 \
  -e FIREBASE_CREDENTIALS="${FIREBASE_CREDENTIALS}" \
  tree-d-backend:latest

# View logs
docker logs -f tree-d-backend

# Stop container
docker stop tree-d-backend

# Remove container
docker rm tree-d-backend
```

#### Using Docker Compose (Recommended for Local Development)

```bash
# Start services
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Rebuild and start
docker-compose up --build

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

#### Development Workflow with Hot Reload

```bash
# Start with hot reload enabled
docker-compose up

# Make changes to app/ files - the server will automatically reload
# View logs to see reload messages
docker-compose logs -f api
```

### Multi-stage Production Build (Optimized)

For production, use a multi-stage build to minimize image size:

```dockerfile
# Dockerfile.prod
# Stage 1: Builder
FROM python:3.9-slim as builder

WORKDIR /app

# Install dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.9-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (modular structure)
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/gettime')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Build and run production image:

```bash
docker build -f Dockerfile.prod -t tree-d-backend:prod .
docker run -d -p 8000:8000 --name tree-d-backend-prod tree-d-backend:prod
```

### Deployment with Docker

#### Deploy to Cloud Run (Google Cloud)

```bash
# Build for Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/tree-d-backend

# Deploy to Cloud Run
gcloud run deploy tree-d-backend \
  --image gcr.io/PROJECT_ID/tree-d-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FIREBASE_CREDENTIALS="${FIREBASE_CREDENTIALS}"
```

### Benefits of Containerization

- **Consistency**: Same environment across development, testing, and production
- **Isolation**: Dependencies are contained within the Docker image
- **Portability**: Run anywhere Docker is supported (local, cloud, on-premise)
- **Scalability**: Easy to scale horizontally with container orchestration (Kubernetes, ECS)
- **CI/CD Integration**: Seamless integration with automated pipelines
- **Resource Efficiency**: Lightweight compared to virtual machines
- **Version Control**: Tag images for easy rollback and version management
- **Security**: Run as non-root user, minimal attack surface

### Docker Best Practices

1. **Use multi-stage builds** to reduce final image size
2. **Run as non-root user** for security
3. **Use .dockerignore** to exclude unnecessary files
4. **Pin Python version** (e.g., `python:3.9-slim` not `python:latest`)
5. **Use health checks** to ensure container is running properly
6. **Layer caching** - copy requirements.txt before source code
7. **Environment variables** for configuration (never hardcode secrets)
8. **Keep images small** - use slim/alpine base images where possible

</details>

<details>
<summary><strong>Infrastructure as Code (IaC) with Terraform and CI/CD and Github actions</strong></summary>

This section builds upon both the **Code Structure Refactoring** and **Containerization with Docker** approaches. It assumes you have a modular codebase packaged in Docker containers, ready for automated deployment across multiple environments.

To implement automated infrastructure provisioning and deployment pipelines, consider the following enhanced directory structure:

```
backend-treed/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Run tests and linting on PR
│       ├── deploy-dev.yml            # Deploy to dev environment
│       ├── deploy-staging.yml        # Deploy to staging environment
│       ├── deploy-prod.yml           # Deploy to production (manual trigger)
│       └── terraform-plan.yml        # Terraform plan on PR
│
├── terraform/
│   ├── main.tf                       # Main Terraform configuration (single source)
│   ├── variables.tf                  # Variable definitions
│   ├── outputs.tf                    # Output values
│   ├── backend.tf                    # Terraform state backend config
│   │
│   └── modules/
│       ├── api/                      # FastAPI app module
│       │   ├── main.tf              # Vercel/Cloud Run config
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── firebase/                 # Firebase resources
│       │   ├── main.tf              # Firestore, Auth config
│       │   ├── variables.tf
│       │   └── outputs.tf
│       └── monitoring/               # Logging, alerts
│           ├── main.tf
│           ├── variables.tf
│           └── outputs.tf
│
├── scripts/
│   ├── deploy.sh                     # Deployment helper script
│   ├── setup-env.sh                  # Environment setup automation
│   └── run-tests.sh                  # Test execution script
│
├── tests/
│   ├── __init__.py
│   ├── test_main.py                  # Unit tests
│   ├── test_analytics.py             # Analytics endpoint tests
│   └── test_auth.py                  # Authentication tests
│
├── .env.example                      # Template for environment variables
├── .gitignore
├── main.py
├── requirements.txt
├── requirements-dev.txt              # Dev dependencies (pytest, black, etc.)
├── vercel.json
├── CLAUDE.md
└── README.md
```

#### Implementation Roadmap

**Phase 1: Testing Infrastructure**
- [ ] Add `pytest` with test coverage reporting
- [ ] Create unit tests for all endpoints
- [ ] Add integration tests with Firebase emulator
- [ ] Set up pre-commit hooks for code quality

**Phase 2: CI/CD Pipeline**
- [ ] Create GitHub Actions workflow for automated testing
- [ ] Add code linting (black, flake8, mypy)
- [ ] Implement automated security scanning
- [ ] Set up branch protection rules

**Phase 3: GitHub Environments & Terraform Infrastructure**
- [ ] Set up GitHub Environments (dev/staging/production) at `repo → Settings → Environments`
- [ ] Configure environment-specific variables and secrets in GitHub
- [ ] Define Terraform modules for:
  - Vercel projects (or GCP Cloud Run)
  - Firebase projects and Firestore indexes
  - Monitoring and alerting (Cloud Monitoring/Datadog)
- [ ] Set up Terraform Cloud or S3 backend for state management
- [ ] Configure deployment protection rules (require approvals for production)

**Phase 4: Deployment Automation**
- [ ] Implement blue-green deployment strategy
- [ ] Add automatic rollback on failure
- [ ] Create deployment approval gates for production
- [ ] Set up deployment notifications (Slack/Discord)

### GitHub Environments Setup

**GitHub Environments are FREE for all repositories** (public and private). They allow you to:
- Store environment-specific variables and secrets
- Set deployment protection rules (approvals, wait timers)
- Restrict which branches can deploy to which environments

#### Setting Up GitHub Environments

1. **Navigate to your repository on GitHub**
   - Go to `Settings → Environments`
   - Click "New environment"

2. **Create three environments:**
   - `development`
   - `staging`
   - `production`

3. **Configure each environment:**

   **For `development`:**
   - No protection rules needed
   - Add secrets:
     - `FIREBASE_CREDENTIALS` - Dev Firebase credentials
     - `VERCEL_TOKEN` - Vercel API token
     - `VERCEL_PROJECT_ID` - Dev project ID
   - Add variables:
     - `ENVIRONMENT` = `dev`

   **For `staging`:**
   - Optional: Add reviewers for approval
   - Add secrets:
     - `FIREBASE_CREDENTIALS` - Staging Firebase credentials
     - `VERCEL_TOKEN` - Vercel API token
     - `VERCEL_PROJECT_ID` - Staging project ID
   - Add variables:
     - `ENVIRONMENT` = `staging`

   **For `production`:**
   - ✅ **Required reviewers** (at least 1 team member)
   - ✅ **Wait timer** (optional, e.g., 5 minutes)
   - ✅ **Deployment branches** → Only `main` branch
   - Add secrets:
     - `FIREBASE_CREDENTIALS` - Production Firebase credentials
     - `VERCEL_TOKEN` - Vercel API token
     - `VERCEL_PROJECT_ID` - Production project ID
   - Add variables:
     - `ENVIRONMENT` = `production`

### Sample GitHub Actions Workflows

#### Workflow 1: Deploy to Production (with environment)

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov=. --cov-report=xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    environment: production  # 👈 Links to GitHub Environment

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'

      # If using Terraform
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2

      - name: Terraform Apply
        working-directory: ./terraform
        run: |
          terraform init
          terraform apply -auto-approve \
            -var="environment=${{ vars.ENVIRONMENT }}" \
            -var="firebase_credentials=${{ secrets.FIREBASE_CREDENTIALS }}" \
            -var="vercel_token=${{ secrets.VERCEL_TOKEN }}"
```

#### Workflow 2: Deploy to Dev (automatic)

```yaml
# .github/workflows/deploy-dev.yml
name: Deploy to Development

on:
  push:
    branches: [develop]
  pull_request:
    branches: [develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: development  # 👈 Links to dev environment

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Vercel (Dev)
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          # No --prod flag = preview deployment
```

### Sample Terraform Configuration

```hcl
# terraform/modules/api/main.tf
resource "vercel_project" "api" {
  name      = "tree-d-backend-${var.environment}"
  framework = "python"

  environment = [
    {
      key    = "FIREBASE_CREDENTIALS"
      value  = var.firebase_credentials
      target = ["production"]
    }
  ]
}

resource "vercel_deployment" "api" {
  project_id = vercel_project.api.id
  ref        = var.git_branch
  production = var.environment == "prod"
}
```

### Benefits of This Approach

- **Reproducibility**: Infrastructure defined as code
- **Multi-environment**: Easy dev/staging/prod separation
- **Automation**: Reduce manual deployment errors
- **Rollback**: Quick recovery from failed deployments
- **Auditability**: All changes tracked in git history
- **Security**: Secrets managed via GitHub Secrets/Terraform Cloud

</details>
