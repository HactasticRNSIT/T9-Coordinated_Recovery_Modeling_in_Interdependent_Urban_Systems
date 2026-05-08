# Deployment Plan

## Environments

| Environment | Purpose | Infrastructure |
|---|---|---|
| **Local Dev** | Development and testing | Docker Compose on developer machine |
| **Staging** | Integration testing, demo | AWS ECS / GCP Cloud Run (single instance) |
| **Production** | Live deployment | AWS ECS / GCP Cloud Run (auto-scaled) |

---

## Local Development

```bash
# Prerequisites: Docker Desktop, Git

# 1. Clone and configure
git clone https://github.com/your-org/urbansync-ai.git
cd urbansync-ai
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# 2. Start all services
docker-compose up --build

# 3. Run database migrations
docker-compose exec backend alembic upgrade head

# 4. Seed synthetic data
docker-compose exec backend python ml_pipeline/data_generation/synthetic_city.py

# 5. Train ML models (optional — pre-trained artifacts included)
docker-compose exec backend python ml_pipeline/training/train_gnn.py
docker-compose exec backend python ml_pipeline/training/train_lstm.py
docker-compose exec backend python ml_pipeline/training/train_xgboost.py

# Services:
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
# pgAdmin:   http://localhost:5050
```

---

## Cloud Deployment (AWS ECS)

### Architecture

```
Internet
    │
    ▼
AWS ALB (Application Load Balancer)
    │
    ├──► ECS Service: Frontend (Next.js)    — 1–3 tasks
    ├──► ECS Service: Backend (FastAPI)     — 2–4 tasks
    └──► ECS Service: Celery Worker         — 1–2 tasks
         │
         ├──► RDS PostgreSQL + PostGIS      — db.t3.medium
         ├──► ElastiCache Redis             — cache.t3.micro
         └──► S3 Bucket (ML artifacts)
```

### Deployment Steps

```bash
# 1. Build and push Docker images to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

docker build -t urbansync-backend ./backend
docker tag urbansync-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/urbansync-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/urbansync-backend:latest

docker build -t urbansync-frontend ./frontend
docker tag urbansync-frontend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/urbansync-frontend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/urbansync-frontend:latest

# 2. Deploy with Terraform
cd infrastructure/terraform
terraform init
terraform plan -var-file=staging.tfvars
terraform apply -var-file=staging.tfvars

# 3. Run migrations on RDS
aws ecs run-task --cluster urbansync --task-definition urbansync-migrate --launch-type FARGATE
```

### Environment Variables (Production)

Stored in AWS Secrets Manager, injected at runtime:

```
DATABASE_URL          = postgresql://user:pass@rds-endpoint:5432/urbansync
REDIS_URL             = redis://elasticache-endpoint:6379/0
SECRET_KEY            = <generated-256-bit-key>
ENVIRONMENT           = production
ML_MODELS_PATH        = s3://urbansync-artifacts/models/
```

---

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy UrbanSync AI

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run backend tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest tests/ -v --tb=short
      - name: Run frontend type check
        run: |
          cd frontend
          npm ci
          npm run type-check

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Build and push images
        run: |
          # Build backend
          docker build -t urbansync-backend ./backend
          docker push <ecr-url>/urbansync-backend:${{ github.sha }}
          # Build frontend
          docker build -t urbansync-frontend ./frontend
          docker push <ecr-url>/urbansync-frontend:${{ github.sha }}
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster urbansync --service backend --force-new-deployment
          aws ecs update-service --cluster urbansync --service frontend --force-new-deployment
```

---

## Monitoring

| Tool | Purpose | Metrics |
|---|---|---|
| AWS CloudWatch | Infrastructure metrics | CPU, memory, request count, error rate |
| FastAPI middleware | Application metrics | Request latency, endpoint hit rate |
| Sentry | Error tracking | Exceptions, stack traces |
| Uptime Robot | Availability monitoring | HTTP health check every 5 minutes |

### Key Alerts

- API error rate > 5% → PagerDuty alert
- API p95 latency > 2s → Slack notification
- Database CPU > 80% → Auto-scale trigger
- ML model prediction error spike → Email alert

---

## Scaling Considerations

| Component | Scaling Strategy |
|---|---|
| FastAPI backend | Horizontal: ECS auto-scaling on CPU > 70% |
| Celery workers | Horizontal: scale on queue depth > 10 tasks |
| PostgreSQL | Vertical: upgrade instance; read replicas for analytics |
| Redis | Cluster mode for high availability |
| ML inference | Cache predictions in Redis (TTL: 5 minutes) |
| WebSocket | Redis pub/sub handles multi-instance broadcasting |

---

## Disaster Recovery

| Scenario | RTO | RPO | Solution |
|---|---|---|---|
| Container crash | < 1 min | 0 | ECS auto-restart |
| AZ failure | < 5 min | 0 | Multi-AZ ECS + RDS |
| Database corruption | < 30 min | < 1 hour | RDS automated backups (daily) |
| Region failure | < 2 hours | < 24 hours | Manual failover to secondary region |
