# goco-project-template

GO Corporation — Cloud Run project template with CI/CD, AI evaluation loop, and structured development workflow.

## Quick Start

### From Template
```bash
gh repo clone eukrit/goco-project-template my-new-project -- --template
cd my-new-project
chmod +x setup.sh verify.sh
./setup.sh my-new-project eukrit
```

### Manual Setup
```bash
git clone https://github.com/eukrit/goco-project-template.git my-new-project
cd my-new-project
chmod +x setup.sh verify.sh
./setup.sh my-new-project eukrit
```

## Project Structure
```
project-root/
├── manifest.json          # LOCAL ONLY — gitignored
├── manifest.example.json  # Committed template
├── CLAUDE.md              # Claude Code session instructions
├── CHANGELOG.md           # Auto-updated each build
├── cloudbuild.yaml        # GCP Cloud Build config
├── verify.sh              # Post-build verification script
├── Dockerfile             # Cloud Run container
├── package.json           # Node.js dependencies
├── src/
│   └── index.js           # Cloud Run app skeleton
├── docs/
│   ├── Summary.html       # Executive summary (auto-generated)
│   ├── DeploymentPlan.md  # Task backlog + AI improvements
│   └── BuildPlans/
│       └── BuildPlan_v1.0.0.md
└── .github/
    └── PULL_REQUEST_TEMPLATE/
        └── pull_request_template.md
```

## Development Workflow

1. **Plan** — Create Build Plan in Notion, get approval
2. **Develop** — Work on `dev/feature-name` branch with conventional commits
3. **Verify** — Run `./verify.sh` locally
4. **Push** — Push to GitHub → Cloud Build runs tests
5. **AI Eval** — Claude reviews verify-report.json, scores the build
6. **Merge** — PR to `main` → Cloud Build deploys to Cloud Run
7. **Sign-off** — Human reviews and approves

## Branch Strategy
- `main` — production, auto-deploys via Cloud Build
- `dev/feature-name` — development, build + test only

## Commit Convention
```
feat(scope): description    # new feature
fix(scope): description     # bug fix
docs(scope): description    # documentation
chore(scope): description   # config/infra
test(scope): description    # tests
```

## GCP Setup
- Region: `asia-southeast1`
- Service account: `claude@ai-agents-go.iam.gserviceaccount.com`
- Secrets: GCP Secret Manager (peak-api-token, n8n-webhook-key)
