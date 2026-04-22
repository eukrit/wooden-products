# wooden-products

## Project Identity
- Project: wooden-products
- Owner: Eukrit / GO Corporation Co., Ltd.
- Notion Dashboard: https://www.notion.so/gocorp/Coding-Project-Dashboard-Claude-32c82cea8bb080f1bbd7f26770ae9e80
- GitHub Repo: https://github.com/eukrit/wooden-products
- GCP Project ID: ai-agents-go
- GCP Project Number: 538978391890
- Firestore Database: products-wood (asia-southeast1)
- Cloud Storage Bucket: gs://products-wood-assets
- Region: asia-southeast1
- Service Account: claude@ai-agents-go.iam.gserviceaccount.com
- Artifact Registry: asia-southeast1-docker.pkg.dev/ai-agents-go/[PROJECT_NAME]
- Language: [node|python]

## Related Repos
- **accounting-automation** (master) — Peak API, Xero, MCP server → `eukrit/accounting-automation`
- **business-automation** (main) — ERP gateway, shared libs, dashboard → `eukrit/business-automation`
- Credential files → use `Credentials Claude Code` folder + GCP Secret Manager

## MANDATORY: After every code change
1. `git add` + `git commit` + `git push origin main`
2. Cloud Build auto-deploys to Cloud Run — verify build succeeds
3. Update `eukrit/business-automation` dashboard (`docs/index.html`) if architecture changes
4. Update `eukrit/business-automation/CHANGELOG.md` with version entry

## Credentials & Secrets

### Centralized Credentials Folder
All API credentials are stored in:
```
C:\Users\eukri\OneDrive\Documents\Claude Code\Credentials Claude Code
```
Master instructions: `Credentials Claude Code/Instructions/API Access Master Instructions.txt`

### Credential Loading Rules
1. **Local development**: Load from `.env` file (gitignored) or `credentials/` folder
2. **CI/CD (Cloud Build)**: Load from GCP Secret Manager
3. **MCP connectors**: Auth handled by the MCP platform — no local credentials needed
4. **NEVER hardcode** credentials in source code or committed files
5. **NEVER commit** `.env`, `manifest.json`, `credentials/`, `*.key`, `*.pem`, token files

### GCP Secret Manager (CI/CD)
| Secret Name | Source File | Used By |
|---|---|---|
| `peak-api-token` | Peak API Credential.txt | Peak API calls |
| `xero-client-secret` | Xero Credentials.txt | Xero OAuth refresh |
| `notion-api-key` | NOTION_API_KEY.md | Notion API |
| `slack-bot-token` | Slack OAuth.txt | Slack notifications |
| `figma-token` | Figma Token.txt | Figma API |
| `stitch-api-key` | Stitch API Key.txt | Stitch Design API |
| `n8n-webhook-key` | n8n config | n8n webhook auth |

### Credential File References
| File | Location | Purpose |
|---|---|---|
| `ai-agents-go-9b4219be8c01.json` | Credentials folder | GCP service account key |
| `client_secret_538978391890-*.json` | Credentials folder | GCP OAuth client |
| `xero_tokens.json` | Credentials folder | Xero OAuth tokens (rotating) |
| `token_oauth.json` | Credentials folder | Google OAuth token |
| `token_gmail_settings.json` | Credentials folder | Gmail OAuth token |

## Safety Rules
- NEVER commit credentials, API keys, or tokens
- NEVER auto-merge to main without test pass
- ALWAYS run verify.sh before marking build complete
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
- Runtime: [Node.js 20 | Python 3.11]
- Infrastructure: GCP Cloud Run + Cloud Build
- CI/CD: GitHub → GCP Cloud Build trigger
- Automation: n8n (gocorp.app.n8n.cloud)
- Docs: Notion

## Project-Specific Notes

### Sales Sheet Microsite Platform
- **Live URL:** https://salesheet.leka.studio/wpc-fence/
- **Code:** `website/salesheet/` (Flask + gunicorn on Cloud Run)
- **Cloud Run service:** `salesheet-leka` (asia-southeast1)
- **Lead routing:** `POST /api/quote` → Slack `#bd-new-leads` (`C07EF698Q1K`)
- **Full build playbook:** [`website/salesheet/README.md`](website/salesheet/README.md) —
  read this before building a new product sales sheet. Covers the Leka
  Design System tokens (Figma file `ER6pbDqrJ4Uo9FuldnYBfm`), page
  structure, backend contract, Slack setup, Cloud Run deploy, GoDaddy
  DNS automation, warranty-copy guardrails, and content rules.

### Firestore Database: products-wood
Collections:
- `vendors` — 45 supplier/manufacturer profiles
- `products` — 38 wood product records with specs
- `quotations` — 13 price quotations linked to vendors
- `product_images` — 26 document/image metadata records (files in Cloud Storage)
- `categories` — 11 product category taxonomy entries

### Cloud Storage: gs://products-wood-assets
Organized by vendor folder: ks-wood/, pinecross/, sci-wood/, feiyou/, china-flooring/

### Data Sources
- Slack: #supplier-artificial-wood, #supplier-ks-wood, #vendor-wood-flooring
- Gmail: KS Wood, Pinecross, MOSO, Mapei, TopFlor, Perflex correspondence
- OneDrive: Documents GO, Suppliers GO (KS Wood, Pinecross, Feiyou, etc.)

### Key Scripts
- `scripts/firestore/schema.py` — Data architecture definition
- `scripts/firestore/setup_db.py` — Database setup and category seeding
- `scripts/firestore/upload_data.py` — Bulk JSON data upload
- `scripts/firestore/upload_images.py` — Cloud Storage file upload with Firestore metadata

---

## Claude Process Standards (MANDATORY)

Full reference: `Credentials Claude Code/Instructions/Claude Process Standards.md`

0. **`goco-project-template` is READ-ONLY** — never edit, commit, or push to the `goco-project-template` folder or `eukrit/goco-project-template` repo. It exists only to be copied when scaffolding new projects. If any project's `origin` points at `goco-project-template`, STOP and remove/fix the remote before doing anything else.
1. **Always maintain a todo list** — use `TodoWrite` for any task with >1 step or that edits files; mark items done immediately.
2. **Always update a build log** — append a dated, semver entry to `BUILD_LOG.md` (or existing `CHANGELOG.md`) for every build/version: version, date (YYYY-MM-DD), summary, files changed, outcome. The log lives in **this project's own folder** — never in `business-automation/`.
3. **Plan in batches; run them as one chained autonomous pass** — group todos into batches, surface the plan once, then execute every batch back-to-back in a single run. No turn-taking between todos or batches. Run long work with `run_in_background: true`; parallelize independent tool calls. Only stop for true blockers: destructive/unauthorized actions, missing credentials, genuine ambiguity, unrecoverable external errors, or explicit user confirmation request.
4. **Always update `build-summary.html` at THIS project's root** for every build/version (template: `Credentials Claude Code/Instructions/build-summary.template.html`). Per-project — DO NOT write into `business-automation/`. Touch the workspace dashboard at `business-automation/docs/index.html` only for cross-project / architecture changes.
5. **Always commit and push — verify repo mapping first** — run `git remote -v` and confirm the remote repo name matches the local folder name (per the Code Sync Rules in the root `CLAUDE.md`). If mismatch (especially `goco-project-template`), STOP and ask the user. Never push to the wrong repo.
