## Fraud Detection Graphs

### Overview
Fraud Detection Graphs is an analytics and visualization project for exploring and detecting fraud patterns using graph analysis. It provides:
- Graph building and aggregation from transactional data
- Community and anomaly detection
- An interactive Gradio dashboard for investigation
- Infrastructure-as-code (Terraform) to deploy a production-ready app on AWS ECS Fargate behind an ALB with EFS persistence

### Tech Stack
- Python 3.11, NetworkX, pandas, numpy, scikit-learn, scipy
- Gradio UI for the dashboard
- Terraform for AWS (VPC, ECS Fargate, ALB, EFS, IAM, AutoScaling)
- Docker for packaging

### Repository Structure
```text
analysis/                # Graph analytics (builders, metrics, anomalies, communities)
dashboard/               # Gradio app (entry via `python -m dashboard`)
visualization/           # Plotly/PyVis helpers and components
data/                    # Data loaders and generators (sample_data allowed)
antifraude-iac/          # IaC: Dockerfile + Terraform for AWS deployment
  ├─ terraform/          # *.tf configs (no tfstate/tfvars committed)
  ├─ Dockerfile          # Image used by ECS
  ├─ build-and-push.bat  # Build & push to ECR
  └─ deploy.bat          # Orchestration helpers
scripts                  # (if added)
exports/                 # Generated artifacts (ignored by .gitignore)
requirements.txt
setup.py
.gitignore
```

### Local Development
- Create a virtual environment and install dependencies:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
- Run the dashboard locally:
```bash
python -m dashboard
```
The app defaults to port 7860.

### Deployment (AWS ECS Fargate)
- IaC lives under `antifraude-iac/terraform`.
- Build image (ECR), apply infrastructure, then update the service:
```bash
# Infrastructure changes
terraform init && terraform apply
# Application image & deploy
antifraude-iac\build-and-push.bat
antifraude-iac\deploy.bat   # or deploy-to-aws.bat
```
Key environment and networking settings are already configured via Terraform:
- `GRADIO_SERVER_NAME=0.0.0.0`, `GRADIO_SERVER_PORT=7860`
- `NO_PROXY=127.0.0.1,localhost`
- ALB Target Group health check path `/`

### Logging & Monitoring
- Application logs: CloudWatch Logs group `/ecs/<project>-<env>` with streams like `ecs/fraud-detection-app/<task-id>`
- ALB access logs: S3 bucket `<project>-<env>-alb-logs-*` under prefix `alb/`

### Data & Privacy
- `.gitignore` excludes tfstate, tfvars, exports, logs, venv, and large/temporary data.
- Do not commit secrets or real data. Use `terraform.tfvars.example` and `terraform.tfvars.minimal` for configuration templates.

### Troubleshooting
- ImportError about `HfFolder` in `huggingface_hub`: pin `huggingface_hub<1.0` (project uses `0.23.x`) with `gradio==4.44.1`.
- Gradio “localhost not accessible”: already bound to `0.0.0.0`; ensure ALB/Target Group to port 7860 and `NO_PROXY` includes `localhost`.
- Health checks: ALB path `/`; container health checks hit `http://localhost:7860/` inside the task.

### License
Add your preferred license (MIT/Apache-2.0) if applicable.

### Roadmap (examples)
- Expand anomaly scoring methods
- Add auth and multi-tenant data management
- Extend CI/CD for multi-environment promotion
