#!/usr/bin/env bash
# Manual Cloud Run deployment - the same steps the GitHub Actions job runs.
# Needs: gcloud CLI, a GCP project with billing, Docker. Run from 5_ci_cd_cloud_deploy/.
set -euo pipefail
PROJECT=${PROJECT:?set PROJECT=<your-gcp-project-id>}
REGION=${REGION:-asia-south1}                       # Mumbai
REPO=agents
IMAGE="$REGION-docker.pkg.dev/$PROJECT/$REPO/agent-service:$(git rev-parse --short HEAD 2>/dev/null || echo manual)"

gcloud config set project "$PROJECT"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# 1. A private image registry (once)
gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION" 2>/dev/null || true
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# 2. The API key goes into Secret Manager, never into the image or the command line history
gcloud secrets describe openai-api-key >/dev/null 2>&1 || \
  { read -rsp "OpenAI key: " KEY; echo; printf '%s' "$KEY" | gcloud secrets create openai-api-key --data-file=-; }

# 3. Build and push
docker build -t "$IMAGE" --build-arg APP_VERSION="${IMAGE##*:}" .
docker push "$IMAGE"

# 4. Deploy: autoscaling 0..5 instances, 20 concurrent requests each, secret injected at start
gcloud run deploy agent-service --image "$IMAGE" --region "$REGION" \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --min-instances 0 --max-instances 5 --concurrency 20 --cpu 1 --memory 512Mi \
  --allow-unauthenticated
URL=$(gcloud run services describe agent-service --region "$REGION" --format 'value(status.url)')
curl -s "$URL/version"; echo
echo "Logs:    gcloud run services logs read agent-service --region $REGION --limit 20"
echo "Metrics: Cloud Console -> Cloud Run -> agent-service -> Metrics (requests, latency, instances)"
echo "Delete:  gcloud run services delete agent-service --region $REGION"
