# CodeHealer Complete System Architecture Summary

## 🎯 What is CodeHealer?

An autonomous AI agent that:
- Monitors GitHub repositories for code changes
- Detects bugs and security vulnerabilities
- Searches team Slack history for proven solutions
- Auto-fixes issues and creates pull requests
- Learns from every fix to prevent repeated mistakes

---

## 🏗️ System Architecture Overview

```
GitHub Push
    ↓
API Gateway (HTTPS endpoint)
    ↓
Lambda Function (Python code)
    ↓
┌─────────────────────────────────────┐
│  Decision Tree (Priority Order)     │
│  1. Search Slack (team solutions)   │
│  2. Search OpenSearch (past fixes)  │
│  3. Call SageMaker (AI analysis)    │
└─────────────────────────────────────┘
    ↓
Create PR + Notify Slack + Log to DynamoDB
```

---

## 📦 Components & Their Roles

### **1. API Gateway** - The Front Door
**What:** AWS REST API endpoint that receives GitHub webhooks  
**Created by:** Terraform  
**Purpose:** Secure HTTPS URL for GitHub to call

**Features:**
- Webhook endpoint: `https://xxx.amazonaws.com/prod/webhook`
- Request validation (signature verification)
- Rate limiting (50 req/sec, 100 burst)
- AWS WAF protection (DDoS, geographic filtering)
- CloudWatch logging and alarms
- Custom domain support (optional)

**Cost:** ~$5/month with WAF, ~$0.50 without

---

### **2. Lambda Function** - The Brain
**What:** Python code that processes webhooks  
**Created by:** Terraform (infrastructure) + You (Python code)  
**Purpose:** Orchestrates the entire fix workflow

**What it does:**
1. Receives webhook from API Gateway
2. Verifies GitHub signature (security)
3. Validates event (push to develop branch only)
4. Searches for solutions (Slack → OpenSearch → SageMaker)
5. Creates GitHub pull request with fix
6. Posts notification to Slack
7. Logs everything to DynamoDB
8. Stores fix in OpenSearch for future use

**Python Files:**
- `src/lambda_handler.py` - Main entry point
- `src/utils/config.py` - Configuration management
- `src/utils/logger.py` - JSON logging
- `src/integrations/slack_client.py` - Slack API
- `src/integrations/github_client.py` - GitHub API
- `src/integrations/sagemaker_client.py` - Model inference
- `src/agent/analyzer.py` - Core analysis logic

**Cost:** ~$2-5/month (500 invocations)

---

### **3. SageMaker** - The AI Model Server
**What:** Hosts Llama 3.1 NIM and Embedding NIM models  
**Created by:** Terraform  
**Purpose:** Runs AI inference to analyze code

**Two Endpoints:**

**A. Llama 3.1 NIM Endpoint**
- Analyzes code for bugs and vulnerabilities
- Generates fix suggestions
- Provides confidence scores
- Input: Code snippet + prompt
- Output: Issues found + suggested fixes

**B. Embedding NIM Endpoint**
- Converts code to vector embeddings (768 numbers)
- Enables semantic similarity search
- Powers the RAG system
- Input: Code snippet
- Output: Vector [0.234, 0.891, ...]

**How It Works:**
1. You don't train the model (use pre-trained NVIDIA NIM)
2. Terraform creates endpoints pointing to the model
3. Lambda calls endpoints via `boto3`
4. SageMaker returns predictions

**Connection:**
- **Terraform:** Creates the endpoint infrastructure
- **Python:** Calls the endpoint at runtime
- **Link:** Environment variable `SAGEMAKER_LLAMA_ENDPOINT`

**Cost:** ~$35-50/month (serverless inference)

---

### **4. OpenSearch** - The Memory (Vector Database)
**What:** Stores past fixes as searchable vectors  
**Created by:** Terraform  
**Purpose:** Fast retrieval of similar past fixes (RAG)

**How It Works:**

**Storing Fixes:**
```
Fix applied: SQL injection → parameterized query
    ↓
Convert to vector: [0.234, 0.891, 0.456, ...] (768 numbers)
    ↓
Store in OpenSearch with metadata
```

**Searching Fixes:**
```
New bug detected: SQL injection in payment.py
    ↓
Convert to vector: [0.245, 0.885, 0.461, ...]
    ↓
Search OpenSearch: "Find similar vectors"
    ↓
Match found: 95% similarity to previous fix!
    ↓
Use the same fix (0.1 seconds vs 30 seconds with AI)
```

**What Gets Stored:**
- Original buggy code
- Fixed code
- Issue type (SQL_INJECTION, XSS, etc.)
- Severity (CRITICAL, HIGH, MEDIUM, LOW)
- File path and language
- Vector embedding (for similarity search)
- Timestamp and confidence score

**Benefits:**
- 300x faster than SageMaker (0.1s vs 30s)
- 80x cheaper ($0.001 vs $0.08 per query)
- Learns from every fix
- 70% of fixes found in OpenSearch after 100 fixes

**Cost:** ~$15-25/month (t3.small.search)

---

### **5. DynamoDB** - The Audit Trail
**What:** NoSQL database storing every action  
**Created by:** Terraform  
**Purpose:** Compliance, metrics, debugging

**What Gets Logged:**
```json
{
  "fix_id": "fix-2024-01-20-abc123",
  "timestamp": "2024-01-20T10:30:45Z",
  "repository": "your-org/api-service",
  "file_path": "src/auth.py",
  "issue_type": "SQL_INJECTION",
  "severity": "CRITICAL",
  "confidence_score": 94,
  "source": "slack",
  "pr_url": "github.com/your-org/api/pull/456",
  "fix_applied": true,
  "user": "dev@company.com",
  "execution_time_ms": 2340
}
```

**Use Cases:**
- **Compliance:** "Show all fixes from last month"
- **Metrics:** "How many SQL injections prevented?"
- **Debugging:** "Why did this fix fail?"
- **Cost Tracking:** "How much did we spend on fixes?"
- **Analytics:** "Which files have most issues?"

**Cost:** ~$1-2/month (on-demand pricing)

---

### **6. IAM** - The Security Guard
**What:** AWS Identity and Access Management  
**Created by:** Terraform  
**Purpose:** Controls who can do what (permissions)

**Without IAM:**
```
Lambda: "I want to call SageMaker"
AWS: ❌ "Access Denied"

Lambda: "I want to read Secrets"
AWS: ❌ "Access Denied"

Everything fails!
```

**With IAM Roles:**

**Lambda Execution Role:**
```
Permissions:
✅ Invoke SageMaker endpoints
✅ Read Secrets Manager (GitHub token, Slack token)
✅ Write to CloudWatch Logs
✅ Write to DynamoDB
✅ Search OpenSearch
✅ Call GitHub API
✅ Call Slack API

Cannot:
❌ Delete S3 buckets
❌ Terminate instances
❌ Access other accounts
```

**SageMaker Execution Role:**
```
Permissions:
✅ Read model from S3
✅ Write logs to CloudWatch
```

**API Gateway Role:**
```
Permissions:
✅ Invoke Lambda function
✅ Write access logs
```

**Security Principle:** Least Privilege (only what's needed)

**Cost:** Free

---

### **7. Secrets Manager** - The Vault
**What:** Secure storage for API keys and tokens  
**Created by:** Terraform  
**Purpose:** Never hardcode credentials

**What Gets Stored:**
- GitHub Personal Access Token
- Slack Bot Token
- GitHub Webhook Secret
- OpenSearch credentials (optional)

**How Lambda Accesses:**
```python
import boto3

secrets = boto3.client('secretsmanager')
response = secrets.get_secret_value(SecretId='codehealer/github-token')
github_token = response['SecretString']
```

**Benefits:**
- Automatic rotation
- Audit trail (who accessed when)
- Encryption at rest
- No secrets in code or environment variables

**Cost:** ~$1/month (3 secrets)

---

### **8. CloudWatch** - The Monitor
**What:** AWS logging and monitoring service  
**Created by:** Terraform  
**Purpose:** Logs, metrics, alarms

**What It Monitors:**
- API Gateway access logs (all webhook requests)
- Lambda execution logs (Python print statements)
- SageMaker endpoint metrics (latency, errors)
- OpenSearch cluster health

**Alarms Created:**
- API Gateway 5XX errors (>10 in 5 min)
- API Gateway 4XX errors (>20 in 5 min)
- API Gateway latency (>5 seconds)
- Lambda errors and throttling

**Cost:** ~$2-5/month (logs + metrics)

---

## 🔗 How Everything Connects

### **The Complete Flow:**

```
1. Developer pushes code to GitHub (develop branch)
    ↓
2. GitHub webhook → API Gateway
   (Terraform created this endpoint)
    ↓
3. API Gateway validates request
   (Checks signature, rate limits)
    ↓
4. API Gateway → Lambda
   (IAM permission allows this)
    ↓
5. Lambda reads secrets from Secrets Manager
   (IAM permission allows this)
   Gets: GitHub token, Slack token
    ↓
6. Lambda searches Slack for similar issues
   (First priority: team solutions)
   ├─ Found? → Use that solution (90% confidence)
   └─ Not found? → Continue to step 7
    ↓
7. Lambda searches OpenSearch
   (IAM permission allows this)
   Embedding NIM converts code to vector
   Search for similar past fixes
   ├─ Found? → Use that fix (85% confidence)
   └─ Not found? → Continue to step 8
    ↓
8. Lambda calls SageMaker Llama endpoint
   (IAM permission allows this)
   Sends: Code snippet + context
   Receives: Analysis + fix suggestion
    ↓
9. Lambda evaluates confidence score
   ├─ ≥85% → Auto-create PR
   ├─ 60-84% → Create draft PR + notify senior dev
   └─ <60% → Just notify senior dev (manual review)
    ↓
10. Lambda creates GitHub PR
    (Uses GitHub token from Secrets Manager)
     ↓
11. Lambda posts to Slack
    (Uses Slack token from Secrets Manager)
    "✅ Fixed SQL injection in auth.py - PR #456"
     ↓
12. Lambda writes to DynamoDB
    (IAM permission allows this)
    Logs: timestamp, repo, file, issue, fix, confidence
     ↓
13. Lambda stores fix in OpenSearch
    (IAM permission allows this)
    For future similarity search
     ↓
14. Lambda returns 200 OK to API Gateway
     ↓
15. API Gateway returns response to GitHub
     ↓
Done! (Usually completes in 5-45 seconds)
```

---

## 🔄 Terraform vs Python

### **What Terraform Does (Infrastructure):**
- Creates API Gateway endpoint
- Creates Lambda function (uploads Python .zip)
- Creates SageMaker endpoints
- Creates OpenSearch domain
- Creates DynamoDB table
- Creates IAM roles and policies
- Creates CloudWatch log groups and alarms
- Creates Secrets Manager secrets

**Runs:** On your PC during deployment  
**Result:** Infrastructure exists in AWS

### **What Python Does (Business Logic):**
- Receives webhook events
- Verifies signatures
- Searches Slack
- Calls SageMaker
- Searches OpenSearch
- Creates PRs
- Posts to Slack
- Logs to DynamoDB

**Runs:** Inside AWS Lambda when webhook arrives  
**Result:** Code gets analyzed and fixed

### **How They Connect:**
1. You write Python code locally
2. Package as `lambda_package.zip`
3. Terraform uploads zip to Lambda
4. Lambda runs your Python when triggered
5. Terraform passes configuration via environment variables

---

## 💰 Cost Breakdown (Monthly)

### **Development Environment:**
| Service | Cost |
|---------|------|
| API Gateway | $0.50 |
| Lambda | $2 |
| SageMaker (serverless) | $5 |
| OpenSearch (t3.small) | $15 |
| DynamoDB | $1 |
| CloudWatch | $2 |
| Secrets Manager | $1 |
| **Total** | **~$26.50/month** |

### **Production Environment:**
| Service | Cost |
|---------|------|
| API Gateway + WAF | $5 |
| Lambda | $10 |
| SageMaker (serverless) | $50 |
| OpenSearch (r6g.large) | $150 |
| DynamoDB | $2 |
| CloudWatch | $5 |
| Secrets Manager | $1 |
| **Total** | **~$223/month** |

### **Hackathon Testing (15 days):**
- Days 1-12: LocalStack (FREE)
- Days 13-15: AWS deployment (3 hours total)
- **Total Cost: ~$5** 🎉

---

## 🎯 Decision Tree Algorithm

### **Priority System:**

```
Issue Detected
    ↓
Priority 1: Search Slack
    ├─ Found? → 90% confidence → Auto-fix
    └─ Not found ↓
    
Priority 2: Search OpenSearch (Vector DB)
    ├─ Found? → 85% confidence → Auto-fix
    └─ Not found ↓
    
Priority 3: Call SageMaker (AI)
    ├─ Confidence ≥85% → Auto-fix
    ├─ Confidence 60-84% → Draft PR + Notify
    └─ Confidence <60% → Escalate to senior dev
```

### **Confidence Thresholds:**
- **≥85%:** Full automation (create PR, merge ready)
- **60-84%:** Semi-automation (draft PR, request review)
- **<60%:** Manual review (notify senior, no PR)

---

## 📊 What Each Service Stores

### **OpenSearch (Vector Database):**
```
Stores: Past fixes as searchable vectors
Query: "Find code similar to this bug"
Speed: 0.1 seconds
Use: Fast retrieval, learning, RAG
```

### **DynamoDB (Audit Trail):**
```
Stores: Every action taken by CodeHealer
Query: "Show all SQL injections fixed last month"
Speed: Fast key-value lookups
Use: Compliance, metrics, debugging
```

### **Secrets Manager (Credentials):**
```
Stores: API tokens and secrets
Query: "Get GitHub token"
Speed: Fast
Use: Secure credential storage
```

### **S3 (Model Storage):**
```
Stores: SageMaker model artifacts (optional)
Query: Not directly queried
Speed: N/A
Use: SageMaker loads model from here
```

---

## 🧪 Testing Strategy

### **Without AWS (Free):**
1. **LocalStack** - Emulates AWS locally
2. **Terraform Plan** - Shows what would be created
3. **Terraform Validate** - Checks syntax
4. **Unit Tests** - Tests Python code
5. **Mocked AWS** - Uses `moto` library

### **With AWS (Cheap):**
1. Deploy for 1-2 hours only (~$1)
2. Use dev configuration (disable WAF, small instances)
3. Destroy immediately after testing
4. Use AWS Free Tier where possible

---

## 🚀 Deployment Steps

### **1. Bootstrap Terraform Backend:**
```bash
./scripts/bootstrap_terraform.sh
```
Creates S3 bucket and DynamoDB table for state management

### **2. Package Python Code:**
```bash
cd src
zip -r ../lambda_package.zip .
```

### **3. Configure Terraform:**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### **4. Deploy Infrastructure:**
```bash
terraform init
terraform plan
terraform apply
```

### **5. Configure Secrets:**
```bash
aws secretsmanager put-secret-value \
  --secret-id codehealer/github-token \
  --secret-string "ghp_xxx"
```

### **6. Configure GitHub Webhook:**
- Settings → Webhooks → Add webhook
- Use Terraform output `webhook_url`
- Set secret from Secrets Manager

### **7. Test:**
```bash
./scripts/test_webhook.sh
```

---

## 📚 File Structure Summary

```
codehealer/
├── src/                          # Python code (runs in Lambda)
│   ├── lambda_handler.py         # Main entry point ✅
│   ├── utils/
│   │   ├── config.py             # Configuration ✅
│   │   └── logger.py             # JSON logging ✅
│   ├── integrations/             # External APIs
│   │   ├── slack_client.py       # Slack ⏳
│   │   ├── github_client.py      # GitHub ⏳
│   │   └── sagemaker_client.py   # SageMaker ⏳
│   └── agent/                    # Core logic
│       └── analyzer.py           # Analysis ⏳
│
├── terraform/                    # Infrastructure (creates AWS resources)
│   ├── main.tf                   # Root config ✅
│   ├── variables.tf              # Variables ✅
│   ├── outputs.tf                # Outputs ✅
│   ├── terraform.tfvars.example  # Config template ✅
│   └── modules/
│       ├── api_gateway/          # ✅ COMPLETE
│       ├── lambda/               # ⏳ TO DO
│       ├── sagemaker/            # ⏳ TO DO
│       ├── opensearch/           # ⏳ TO DO
│       ├── dynamodb/             # ⏳ TO DO
│       └── iam/                  # ⏳ TO DO
│
├── tests/                        # Tests
│   └── unit/
│       └── test_lambda_handler.py # ✅ COMPLETE
│
├── scripts/                      # Utility scripts
│   ├── bootstrap_terraform.sh    # ✅ Backend setup
│   └── test_webhook.sh           # ✅ Webhook test
│
├── requirements.txt              # ✅ Python deps
├── .env.example                  # ✅ Config template
├── .gitignore                    # ✅ Git ignore
└── README.md                     # ✅ Main docs
```

---

## ✅ Current Progress

### **Completed (20%):**
- ✅ API Gateway Terraform module (100%)
- ✅ Main Terraform configuration
- ✅ Lambda handler (webhook processing)
- ✅ Configuration management
- ✅ JSON logging
- ✅ Unit tests for Lambda
- ✅ Bootstrap scripts
- ✅ Complete documentation

### **To Do (80%):**
- ⏳ Lambda Terraform module
- ⏳ SageMaker Terraform module
- ⏳ OpenSearch Terraform module
- ⏳ DynamoDB Terraform module
- ⏳ IAM Terraform module
- ⏳ Slack integration code
- ⏳ GitHub integration code
- ⏳ SageMaker client code
- ⏳ Agent analysis logic
- ⏳ Integration tests
- ⏳ CI/CD pipeline

---

## 🎯 Next Steps for Hackathon

### **Week 1 (Days 1-7):**
- Day 3-4: Lambda Terraform module
- Day 5-6: IAM Terraform module
- Day 7: SageMaker Terraform module (basic)

### **Week 2 (Days 8-14):**
- Day 8-9: Slack integration code
- Day 10-11: GitHub integration code
- Day 12: OpenSearch module (if time permits)
- Day 13-14: Testing and bug fixes

### **Day 15: Demo Day**
- Deploy to AWS
- Run live demo
- Present to judges

---

## 🔑 Key Takeaways

1. **Terraform** creates infrastructure, **Python** runs the logic
2. **IAM** is required for everything to work (permissions)
3. **OpenSearch** makes it smart (learning from past fixes)
4. **DynamoDB** proves it works (audit trail and metrics)
5. **SageMaker** provides the AI brain (model inference)
6. They connect via **environment variables** and **AWS APIs**
7. Can test locally with **LocalStack** (free)
8. Production costs **~$220/month**, dev costs **~$27/month**

---

## 📞 Quick Reference

**Webhook URL:** From Terraform output `webhook_url`  
**View Logs:** `aws logs tail /aws/lambda/codehealer-webhook-handler --follow`  
**Test Locally:** `./scripts/test_webhook.sh`  
**Deploy:** `terraform apply`  
**Destroy:** `terraform destroy`  
**Cost Check:** AWS Cost Explorer or `infracost`

---

**Total Architecture:** 8 AWS services working together to create an autonomous code-fixing system! 🚀
