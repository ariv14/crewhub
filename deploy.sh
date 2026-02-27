#!/bin/bash
# =============================================================================
# CrewHub — Cloud Run Deployment Script
# =============================================================================
#
# Prerequisites:
#   1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
#   2. Authenticate: gcloud auth login
#   3. Set project: gcloud config set project YOUR_PROJECT_ID
#   4. Enable APIs: gcloud services enable run.googleapis.com cloudbuild.googleapis.com
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# =============================================================================

set -euo pipefail

# Configuration — change these for your project
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="crewhub"

echo "==> Deploying ${SERVICE_NAME} to Cloud Run..."
echo "    Project: ${PROJECT_ID}"
echo "    Region:  ${REGION}"
echo ""

# Deploy directly from source (Cloud Build builds the container)
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "DATABASE_URL=${DATABASE_URL}" \
  --set-env-vars "FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}" \
  --set-env-vars "SECRET_KEY=${SECRET_KEY}" \
  --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY:-}" \
  --set-env-vars "PLATFORM_FEE_RATE=0.10" \
  --set-env-vars "DEFAULT_CREDITS_BONUS=100.0"

echo ""
echo "==> Deployment complete!"
echo ""

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format "value(status.url)")

echo "Service URL: ${SERVICE_URL}"
echo ""
echo "==> Next steps:"
echo "   1. Map custom domain: gcloud run domain-mappings create --service=${SERVICE_NAME} --domain=api.aidigitalcrew.com --region=${REGION}"
echo "   2. Add DNS CNAME: api.aidigitalcrew.com -> ghs.googlehosted.com"
echo "   3. Test: curl ${SERVICE_URL}/health"
echo ""
