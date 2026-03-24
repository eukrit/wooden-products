# CLAUDE.md

## Project Identity
- Project: [PROJECT_NAME]
- Owner: Eukrit / GO Corporation Co., Ltd.
- Notion Dashboard: https://www.notion.so/gocorp/Coding-Project-Dashboard-Claude-32c82cea8bb080f1bbd7f26770ae9e80
- GitHub Repo: [GITHUB_REPO_URL]
- GCP Project ID: [GCP_PROJECT_ID]
- Cloud Run Service: [SERVICE_NAME]

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
