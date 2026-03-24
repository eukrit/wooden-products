# CLAUDE.md

## Project Identity
- Project: [PROJECT_NAME]
- Owner: Eukrit / GO Corporation Co., Ltd.
- Notion Dashboard: https://www.notion.so/gocorp/Coding-Project-Dashboard-Claude-32c82cea8bb080f1bbd7f26770ae9e80
- GitHub Repo: [GITHUB_REPO_URL]
- GCP Project ID: [GCP_PROJECT_ID]
- Cloud Run Service: [SERVICE_NAME]

## Credentials & Secrets

### Centralized Credentials Folder
All API credentials are stored in:
```
C:\Users\eukri\OneDrive\Documents\Claude Code\Credentials Claude Code
```
Master instructions: `Credentials Claude Code/Instructions/API Access Master Instructions.txt`

### Credential Loading Rules
1. **Local development**: Load from `.env` file (gitignored) or symlinked `credentials/` folder
2. **CI/CD (Cloud Build)**: Load from GCP Secret Manager
3. **MCP connectors**: Auth handled by the MCP platform — no local credentials needed
4. **NEVER hardcode** credentials in source code or committed files
5. **NEVER commit** `.env`, `manifest.json`, `credentials/`, `*.key`, `*.pem`, token files

### .env File Format (Local Development)
```bash
# GCP
GCP_PROJECT_ID=ai-agents-go
GCP_REGION=asia-southeast1
GOOGLE_APPLICATION_CREDENTIALS=./credentials/ai-agents-go-4c81b70995db.json

# Peak Accounting
PEAK_CONNECT_ID=gocorporation_peakapi_uat
PEAK_CONNECT_KEY=<from Peak API Credential.txt>
PEAK_APP_CODE=G3OA4AAA20
PEAK_USER_TOKEN=<from Peak API Credential.txt>

# Xero
XERO_CLIENT_ID=<from Xero Credentials.txt>
XERO_CLIENT_SECRET=<from Xero Credentials.txt>
XERO_TENANT_ID=48470554-28f9-46b0-b9d2-4bbf42b4edf8

# Notion
NOTION_API_KEY=<from NOTION_API_KEY.md>

# Slack
SLACK_BOT_TOKEN=<from Slack OAuth.txt>
SLACK_WEBHOOK_URL=<from Slack OAuth.txt>

# Figma
FIGMA_TOKEN=<from Figma Token.txt>

# n8n
N8N_WEBHOOK_KEY=<from n8n config>

# Google Ads (test-only until Basic Access approved)
GOOGLE_ADS_DEV_TOKEN=<from Google Manager Account Developer Token.txt>
GOOGLE_ADS_REFRESH_TOKEN=<generated via google_ads_auth.py>
```

### GCP Secret Manager (CI/CD)
Secrets provisioned per project:
| Secret Name | Source File | Used By |
|---|---|---|
| `peak-api-token` | Peak API Credential.txt | Peak API calls |
| `n8n-webhook-key` | n8n config | n8n webhook auth |
| `xero-client-secret` | Xero Credentials.txt | Xero OAuth refresh |
| `notion-api-key` | NOTION_API_KEY.md | Notion API |
| `slack-bot-token` | Slack OAuth.txt | Slack notifications |
| `figma-token` | Figma Token.txt | Figma API |

### Credential File References
| File | Location | Purpose |
|---|---|---|
| `ai-agents-go-4c81b70995db.json` | Credentials folder | GCP service account key |
| `client_secret_538978391890-*.json` | Credentials folder | GCP OAuth client |
| `xero_tokens.json` | Credentials folder | Xero OAuth tokens (rotating) |
| `token_oauth.json` | Credentials folder | Google OAuth token |
| `token_gmail_settings.json` | Credentials folder | Gmail OAuth token |

### MCP Connectors (No Local Credentials Needed)
- Gmail → `mcp__21a9c990` (MCP handles auth)
- Google Drive → `mcp__c1fc4002` (MCP handles auth)
- Google Calendar → `mcp__51e1705c` (MCP handles auth)
- Notion → `mcp__a83609d9` (MCP handles auth)
- Slack → `mcp__8437d5b9` (MCP handles auth)
- Figma → `mcp__000bb793` / `mcp__Figma` (MCP handles auth)
- Peak → `mcp__6a4640df` via n8n gateway (MCP handles auth)

## Manifest
- Load `manifest.json` at session start
- Never commit manifest.json (it is gitignored)
- Use manifest.example.json as the committed reference template

## Session Protocol
Follow the full Manifest Instructions at:
https://www.notion.so/gocorp/Manifest-Instructions-32c82cea8bb08054bde2cb0c59cff6e7

Shorthand checklist:
1. Load manifest → record paths
2. git fetch + diff check → resolve or escalate
3. Read Deployment Plan → identify outstanding tasks
4. Confirm Build Plan for this session
5. Execute build loop with conventional commits
6. Run verify.sh post-build
7. AI evaluation pass → update Deployment Plan
8. Update CHANGELOG.md + Summary.html
9. Human sign-off

## Safety Rules
- ALWAYS ask for human confirmation before deleting files
- NEVER commit credentials, API keys, or tokens
- NEVER auto-merge to main without test pass
- ALWAYS run verify.sh before marking build complete
- ALWAYS use ENV: references in manifest — never raw values
- ALWAYS load credentials from .env or Secret Manager — never hardcode

## Commit Convention
- feat(scope): description
- fix(scope): description
- docs(scope): description
- chore(scope): description
- test(scope): description

## Branch Strategy
- main → production (auto-deploys to GCP)
- dev/[feature] → development (build only)

## Testing
Run `./verify.sh` for full verification suite.
Minimum pass rate: 100% on critical path, 80% overall.

## Tech Stack
- Runtime: Node.js 20
- Infrastructure: GCP Cloud Run + Cloud Build
- CI/CD: GitHub → GCP Cloud Build trigger
- Automation: n8n (gocorp.app.n8n.cloud)
- Docs: Notion

## Project-Specific Notes
[Add any project-specific instructions here]
