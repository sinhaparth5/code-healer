# CodeHealer Project Structure

Complete folder organization for CI/CD pipeline failure auto-remediation system.

## Directory Tree

```
codehealer/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                      # Run tests on PR
│       ├── deploy-dev.yml              # Deploy to dev environment
│       └── deploy-prod.yml             # Deploy to production
│
├── src/                                # Python Lambda code
│   ├── __init__.py
│   ├── lambda_handler.py               # Main webhook entry point
│   │
│   ├── agent/                          # Core analysis logic
│   │   ├── __init__.py
│   │   ├── analyzer.py                 # Failure classification
│   │   ├── confidence_scorer.py        # Confidence calculation
│   │   └── decision_engine.py          # Auto-fix vs escalate
│   │
│   ├── integrations/                   # External platform APIs
│   │   ├── __init__.py
│   │   ├── github_client.py            # GitHub Actions API
│   │   ├── argocd_client.py            # ArgoCD API
│   │   ├── kubernetes_client.py        # K8s API
│   │   ├── slack_client.py             # Slack search + notify
│   │   └── sagemaker_client.py         # SageMaker inference
│   │
│   ├── resolvers/                      # Remediation actions
│   │   ├── __init__.py
│   │   ├── config_fixer.py             # YAML/JSON fixes
│   │   ├── credential_refresher.py     # Token rotation
│   │   ├── resource_scaler.py          # K8s resource updates
│   │   └── retry_handler.py            # Exponential backoff
│   │
│   └── utils/                          # Utilities
│       ├── __init__.py
│       ├── config.py                   # Environment config
│       ├── logger.py                   # JSON logging
│       ├── embeddings.py               # Vector generation
│       └── prompts.py                  # LLM prompt templates
│
├── terraform/                          # Infrastructure as Code
│   ├── main.tf                         # Root module
│   ├── variables.tf                    # Input variables
│   ├── outputs.tf                      # Output values
│   ├── backend.tf                      # S3 state backend
│   ├── terraform.tfvars.example        # Config template
│   ├── README.md                       # Deployment guide
│   │
│   ├── environments/                   # Environment-specific
│   │   ├── dev.tfvars
│   │   ├── staging.tfvars
│   │   └── prod.tfvars
│   │
│   └── modules/                        # Reusable modules
│       ├── api_gateway/                # Webhook endpoint
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   └── README.md
│       │
│       ├── lambda/                     # Lambda function
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   └── README.md
│       │
│       ├── sagemaker/                  # NIM endpoints
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   └── README.md
│       │
│       ├── opensearch/                 # Vector database
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   └── README.md
│       │
│       ├── dynamodb/                   # Audit trail
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       │
│       └── iam/                        # Roles and policies
│           ├── main.tf
│           ├── variables.tf
│           └── outputs.tf
│
├── tests/                              # Test suite
│   ├── __init__.py
│   │
│   ├── unit/                           # Unit tests
│   │   ├── __init__.py
│   │   ├── test_lambda_handler.py
│   │   ├── test_analyzer.py
│   │   ├── test_github_client.py
│   │   └── test_confidence_scorer.py
│   │
│   ├── integration/                    # Integration tests
│   │   ├── __init__.py
│   │   ├── test_end_to_end.py
│   │   └── test_slack_integration.py
│   │
│   └── fixtures/                       # Test data
│       ├── github_webhook_payloads/
│       ├── argocd_events/
│       └── k8s_pod_failures/
│
├── scripts/                            # Utility scripts
│   ├── bootstrap_terraform.sh          # Setup S3 backend
│   ├── deploy.sh                       # Package + deploy
│   ├── test_webhook.sh                 # Test webhook endpoint
│   └── simulate_failure.sh             # Generate test failures
│
├── docs/                               # Documentation
│   ├── paper.pdf                       # Technical paper (LaTeX)
│   ├── paper.tex                       # LaTeX source
│   ├── images/                         # Diagrams (Mermaid PNGs)
│   │   ├── codehealer_architecture.png
│   │   └── codehealer_workflow.png
│   │
│   ├── guides/                         # User guides
│   │   ├── getting-started.md
│   │   ├── slack-setup.md
│   │   ├── github-actions-integration.md
│   │   └── argocd-integration.md
│   │
│   ├── api/                            # API documentation
│   │   ├── webhook-payload.md
│   │   ├── remediation-actions.md
│   │   └── confidence-scoring.md
│   │
│   └── architecture/
│       └── SYSTEM_ARCHITECTURE_SUMMARY.md
│
├── deployment/                         # Deployment artifacts
│   ├── lambda_package.zip              # Generated Lambda zip
│   └── lambda_layers/                  # Python dependencies
│       └── requirements/
│
├── config/                             # Configuration files
│   ├── failure_patterns.yaml           # Known failure patterns
│   ├── remediation_rules.yaml          # Fix strategies
│   └── slack_channels.yaml             # Channels to search
│
├── examples/                           # Example configurations
│   ├── github-workflow-failures/
│   │   ├── expired-token.yml
│   │   ├── image-pull-error.yml
│   │   └── resource-limit.yml
│   │
│   └── argocd-failures/
│       ├── manifest-error.yml
│       └── sync-timeout.yml
│
├── .github/                            # GitHub specific
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│
├── .gitignore                          # Git ignore rules
├── .env.example                        # Environment template
├── requirements.txt                    # Python dependencies
├── requirements-dev.txt                # Dev dependencies
├── setup.py                            # Python package setup
├── Makefile                            # Build automation
├── docker-compose.yml                  # Local development
├── README.md                           # Main readme
├── CONTRIBUTING.md                     # Contribution guide
├── LICENSE                             # Apache 2.0
└── CHANGELOG.md                        # Version history
```

## Key Files

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

## 🔧 File Purposes

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

## Usage Patterns

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

## Dependencies

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

## Secrets Management

All secrets stored in AWS Secrets Manager:
- `codehealer/github-token`
- `codehealer/slack-token`
- `codehealer/argocd-token`
- `codehealer/k8s-config`

Never commit secrets to Git!

##  Generated Files

These files are generated and should not be committed:
- `deployment/lambda_package.zip`
- `terraform/.terraform/`
- `terraform/*.tfstate`
- `__pycache__/`
- `.pytest_cache/`

---

**This structure supports a scalable, production-ready CI/CD failure auto-remediation system.**
