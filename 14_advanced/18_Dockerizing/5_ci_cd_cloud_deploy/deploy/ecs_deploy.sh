#!/usr/bin/env bash
# Manual ECS-on-Fargate deployment - what the deploy-ecs job automates.
# Needs: AWS CLI v2, Docker, a VPC with two subnets and a security group allowing 8000 from your ALB.
# Edit the <...> placeholders in ecs-task-definition.json first. Run from 5_ci_cd_cloud_deploy/.
set -euo pipefail
REGION=${REGION:-ap-south-1}
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
IMAGE="$REGISTRY/agent-service:$(git rev-parse --short HEAD 2>/dev/null || echo manual)"

# 1. Registry + secret (once)
aws ecr create-repository --repository-name agent-service --region "$REGION" 2>/dev/null || true
aws secretsmanager describe-secret --secret-id openai-api-key --region "$REGION" >/dev/null 2>&1 || \
  { read -rsp "OpenAI key: " KEY; echo; aws secretsmanager create-secret --name openai-api-key --secret-string "$KEY" --region "$REGION"; }

# 2. Build and push
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build -t "$IMAGE" --build-arg APP_VERSION="${IMAGE##*:}" .
docker push "$IMAGE"

# 3. Register a new task-definition revision with this image
sed "s|<filled in by the pipeline>|$IMAGE|" deploy/ecs-task-definition.json > /tmp/taskdef.json
aws ecs register-task-definition --cli-input-json file:///tmp/taskdef.json --region "$REGION" >/dev/null

# 4. Create the cluster/service once, or roll the service to the new revision
aws ecs create-cluster --cluster-name agents --region "$REGION" >/dev/null
if aws ecs describe-services --cluster agents --services agent-service --region "$REGION" \
     --query 'services[?status==`ACTIVE`]' --output text | grep -q agent-service; then
  aws ecs update-service --cluster agents --service agent-service --task-definition agent-service --region "$REGION" >/dev/null
else
  aws ecs create-service --cluster agents --service-name agent-service --task-definition agent-service \
    --desired-count 2 --launch-type FARGATE --region "$REGION" \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNETS:?set SUBNETS=subnet-a,subnet-b}],securityGroups=[${SG:?set SG=sg-...}],assignPublicIp=ENABLED}" >/dev/null
fi
aws ecs wait services-stable --cluster agents --services agent-service --region "$REGION"
echo "Rolled out $IMAGE. Logs: CloudWatch -> /ecs/agent-service"
