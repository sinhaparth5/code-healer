# CodeHealer Project Structure

Complete folder organization for CI/CD pipeline failure auto-remediation system.

## ?? Directory Tree

```
codehealer/
³
ÃÄÄ .github/
³   ÀÄÄ workflows/
³       ÃÄÄ ci.yml                      # Run tests on PR
³       ÃÄÄ deploy-dev.yml              # Deploy to dev environment
³       ÀÄÄ deploy-prod.yml             # Deploy to production
³
ÃÄÄ src/                                # Python Lambda code
³   ÃÄÄ __init__.py
³   ÃÄÄ lambda_handler.py               # Main webhook entry point
³   ³
³   ÃÄÄ agent/                          # Core analysis logic
³   ³   ÃÄÄ __init__.py
³   ³   ÃÄÄ analyzer.py                 # Failure classification
³   ³   ÃÄÄ confidence_scorer.py        # Confidence calculation
³   ³   ÀÄÄ decision_engine.py          # Auto-fix vs escalate
³   ³
³   ÃÄÄ integrations/                   # External platform APIs
³   ³   ÃÄÄ __init__.py
³   ³   ÃÄÄ github_client.py            # GitHub Actions API
³   ³   ÃÄÄ argocd_client.py            # ArgoCD API
³   ³   ÃÄÄ kubernetes_client.py        # K8s API
³   ³   ÃÄÄ slack_client.py             # Slack search + notify
³   ³   ÀÄÄ sagemaker_client.py         # SageMaker inference
³   ³
³   ÃÄÄ resolvers/                      # Remediation actions
³   ³   ÃÄÄ __init__.py
³   ³   ÃÄÄ config_fixer.py             # YAML/JSON fixes
³   ³   ÃÄÄ credential_refresher.py     # Token rotation
³   ³   ÃÄÄ resource_scaler.py          # K8s resource updates
³   ³   ÀÄÄ retry_handler.py            # Exponential backoff
³   ³
³   ÀÄÄ utils/                          # Utilities
³       ÃÄÄ __init__.py
³       ÃÄÄ config.py                   # Environment config
³       ÃÄÄ logger.py                   # JSON logging
³       ÃÄÄ embeddings.py               # Vector generation
³       ÀÄÄ prompts.py                  # LLM prompt templates
³
ÃÄÄ terraform/                          # Infrastructure as Code
³   ÃÄÄ main.tf                         # Root module
³   ÃÄÄ variables.tf                    # Input variables
³   ÃÄÄ outputs.tf                      # Output values
³   ÃÄÄ backend.tf                      # S3 state backend
³   ÃÄÄ terraform.tfvars.example        # Config template
³   ÃÄÄ README.md                       # Deployment guide
³   ³
³   ÃÄÄ environments/                   # Environment-specific
³   ³   ÃÄÄ dev.tfvars
³   ³   ÃÄÄ staging.tfvars
³   ³   ÀÄÄ prod.tfvars
³   ³
³   ÀÄÄ modules/                        # Reusable modules
³       ÃÄÄ api_gateway/                # Webhook endpoint
³       ³   ÃÄÄ main.tf
³       ³   ÃÄÄ variables.tf
³       ³   ÃÄÄ outputs.tf
³       ³   ÀÄÄ README.md
³       ³
³       ÃÄÄ lambda/                     # Lambda function
³       ³   ÃÄÄ main.tf
³       ³   ÃÄÄ variables.tf
³       ³   ÃÄÄ outputs.tf
³       ³   ÀÄÄ README.md
³       ³
³       ÃÄÄ sagemaker/                  # NIM endpoints
³       ³   ÃÄÄ main.tf
³       ³   ÃÄÄ variables.tf
³       ³   ÃÄÄ outputs.tf
³       ³   ÀÄÄ README.md
³       ³
³       ÃÄÄ opensearch/                 # Vector database
³       ³   ÃÄÄ main.tf
³       ³   ÃÄÄ variables.tf
³       ³   ÃÄÄ outputs.tf
³       ³   ÀÄÄ README.md
³       ³
³       ÃÄÄ dynamodb/                   # Audit trail
³       ³   ÃÄÄ main.tf
³       ³   ÃÄÄ variables.tf
³       ³   ÀÄÄ outputs.tf
³       ³
³       ÀÄÄ iam/                        # Roles and policies
³           ÃÄÄ main.tf
³           ÃÄÄ variables.tf
³           ÀÄÄ outputs.tf
³
ÃÄÄ tests/                              # Test suite
³   ÃÄÄ __init__.py
³   ³
³   ÃÄÄ unit/                           # Unit tests
³   ³   ÃÄÄ __init__.py
³   ³   ÃÄÄ test_lambda_handler.py
³   ³   ÃÄÄ test_analyzer.py
³   ³   ÃÄÄ test_github_client.py
³   ³   ÀÄÄ test_confidence_scorer.py
³   ³
³   ÃÄÄ integration/                    # Integration tests
³   ³   ÃÄÄ __init__.py
³   ³   ÃÄÄ test_end_to_end.py
³   ³   ÀÄÄ test_slack_integration.py
³   ³
³   ÀÄÄ fixtures/                       # Test data
³       ÃÄÄ github_webhook_payloads/
³       ÃÄÄ argocd_events/
³       ÀÄÄ k8s_pod_failures/
³
ÃÄÄ scripts/                            # Utility scripts
³   ÃÄÄ bootstrap_terraform.sh          # Setup S3 backend
³   ÃÄÄ deploy.sh                       # Package + deploy
³   ÃÄÄ test_webhook.sh                 # Test webhook endpoint
³   ÀÄÄ simulate_failure.sh             # Generate test failures
³
ÃÄÄ docs/                               # Documentation
³   ÃÄÄ paper.pdf                       # Technical paper (LaTeX)
³   ÃÄÄ paper.tex                       # LaTeX source
³   ÃÄÄ images/                         # Diagrams (Mermaid PNGs)
³   ³   ÃÄÄ codehealer_architecture.png
³   ³   ÀÄÄ codehealer_workflow.png
³   ³
³   ÃÄÄ guides/                         # User guides
³   ³   ÃÄÄ getting-started.md
³   ³   ÃÄÄ slack-setup.md
³   ³   ÃÄÄ github-actions-integration.md
³   ³   ÀÄÄ argocd-integration.md
³   ³
³   ÃÄÄ api/                            # API documentation
³   ³   ÃÄÄ webhook-payload.md
³   ³   ÃÄÄ remediation-actions.md
³   ³   ÀÄÄ confidence-scoring.md
³   ³
³   ÀÄÄ architecture/
³       ÀÄÄ SYSTEM_ARCHITECTURE_SUMMARY.md
³
ÃÄÄ deployment/                         # Deployment artifacts
³   ÃÄÄ lambda_package.zip              # Generated Lambda zip
³   ÀÄÄ lambda_layers/                  # Python dependencies
³       ÀÄÄ requirements/
³
ÃÄÄ config/                             # Configuration files
³   ÃÄÄ failure_patterns.yaml           # Known failure patterns
³   ÃÄÄ remediation_rules.yaml          # Fix strategies
³   ÀÄÄ slack_channels.yaml             # Channels to search
³
ÃÄÄ examples/                           # Example configurations
³   ÃÄÄ github-workflow-failures/
³   ³   ÃÄÄ expired-token.yml
³   ³   ÃÄÄ image-pull-error.yml
³   ³   ÀÄÄ resource-limit.yml
³   ³
³   ÀÄÄ argocd-failures/
³       ÃÄÄ manifest-error.yml
³       ÀÄÄ sync-timeout.yml
³
ÃÄÄ .github/                            # GitHub specific
³   ÃÄÄ ISSUE_TEMPLATE/
³   ÃÄÄ PULL_REQUEST_TEMPLATE.md
³   ÀÄÄ workflows/
³
ÃÄÄ .gitignore                          # Git ignore rules
ÃÄÄ .env.example                        # Environment template
ÃÄÄ requirements.txt                    # Python dependencies
ÃÄÄ requirements-dev.txt                # Dev dependencies
ÃÄÄ setup.py                            # Python package setup
ÃÄÄ Makefile                            # Build automation
ÃÄÄ docker-compose.yml                  # Local development
ÃÄÄ README.md                           # Main readme
ÃÄÄ CONTRIBUTING.md                     # Contribution guide
ÃÄÄ LICENSE                             # Apache 2.0
ÀÄÄ CHANGELOG.md                        # Version history
```

## ?? Key Files

### Configuration
- **`.env.example`** - Template for environment variables
- **`terraform.tfvars.example`** - Terraform configuration template
- **`config/*.yaml`** - Failure patterns and remediation rules

### Source Code
- **`src/lambda_handler.py`** - Webhook entry point (GitHub, ArgoCD, K8s)
- **`src/agent/analyzer.py`** - Failure classification logic
- **`src/integrations/*.py`** - Platform API clients
- **`src/resolvers/*.py`** - Remediation action implementations

### Infrastructure
- **`terraform/main.tf`** - Root infrastructure definition
- **`terraform/modules/`** - Reusable Terraform modules
- **`scripts/bootstrap_terraform.sh`** - One-time backend setup

### Documentation
- **`docs/paper.pdf`** - Complete 45-page technical paper
- **`docs/guides/`** - Step-by-step integration guides
- **`README.md`** - Quick start and overview

## ?? File Purposes

### `lambda_handler.py`
Main entry point for webhook events. Routes to appropriate failure analyzer based on source (GitHub Actions, ArgoCD, Kubernetes).

### `agent/analyzer.py`
Classifies failures into categories (CONFIG, AUTH, RESOURCE, DEPENDENCY) and determines fixability.

### `integrations/github_client.py`
Handles GitHub Actions API:
- Fetch workflow logs
- Re-trigger failed runs
- Create PRs with fixes
- Update repository secrets

### `integrations/argocd_client.py`
Manages ArgoCD operations:
- Get application sync status
- Update manifests
- Trigger re-sync
- Query resource health

### `integrations/kubernetes_client.py`
Kubernetes cluster operations:
- Get pod logs and events
- Update resource limits
- Restart deployments
- Scale replicas

### `resolvers/config_fixer.py`
Fixes configuration errors:
- YAML syntax corrections
- Missing field additions
- Value type fixes
- Reference corrections

### `resolvers/credential_refresher.py`
Handles authentication issues:
- Rotate expired tokens
- Update secrets in GitHub/K8s
- Trigger credential refresh workflows

### `resolvers/resource_scaler.py`
Manages resource constraints:
- Increase memory limits for OOMKilled pods
- Scale deployments
- Request quota increases

## ?? Usage Patterns

### Local Development
```bash
# Run with Docker Compose
docker-compose up

# Test locally
python -m pytest tests/

# Package for Lambda
make package
```

### Deployment
```bash
# Development
terraform apply -var-file="environments/dev.tfvars"

# Production
terraform apply -var-file="environments/prod.tfvars"
```

### Testing
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Simulate failure
./scripts/simulate_failure.sh github-actions expired-token
```

## ?? Dependencies

### Python (requirements.txt)
- `boto3` - AWS SDK
- `slack-sdk` - Slack API
- `PyGithub` - GitHub API
- `kubernetes` - K8s API
- `opensearch-py` - Vector DB
- `langchain` - LLM orchestration

### Infrastructure (Terraform)
- AWS Provider ~> 5.0
- Terraform >= 1.5.0

## ?? Secrets Management

All secrets stored in AWS Secrets Manager:
- `codehealer/github-token`
- `codehealer/slack-token`
- `codehealer/argocd-token`
- `codehealer/k8s-config`

Never commit secrets to Git!

## ?? Generated Files

These files are generated and should not be committed:
- `deployment/lambda_package.zip`
- `terraform/.terraform/`
- `terraform/*.tfstate`
- `__pycache__/`
- `.pytest_cache/`

---

**This structure supports a scalable, production-ready CI/CD failure auto-remediation system.**
