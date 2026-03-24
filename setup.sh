#!/bin/bash
# setup.sh — Bootstrap a new project from the GO Corporation template
# Usage: ./setup.sh <project-name> [github-org]

set -e

PROJECT_NAME="${1:?Usage: ./setup.sh <project-name> [github-org]}"
GITHUB_ORG="${2:-eukrit}"
CREDENTIALS_SOURCE="${CREDENTIALS_FOLDER:-$HOME/OneDrive/Documents/Claude Code/Credentials Claude Code}"

echo "=== GO Corporation Project Setup ==="
echo "Project: $PROJECT_NAME"
echo "GitHub:  $GITHUB_ORG/$PROJECT_NAME"
echo ""

# Update CLAUDE.md
sed -i "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" CLAUDE.md
sed -i "s|\[GITHUB_REPO_URL\]|https://github.com/$GITHUB_ORG/$PROJECT_NAME|g" CLAUDE.md
sed -i "s/\[GCP_PROJECT_ID\]/ai-agents-go/g" CLAUDE.md
sed -i "s/\[SERVICE_NAME\]/$PROJECT_NAME/g" CLAUDE.md

# Update manifest.example.json
sed -i "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" manifest.example.json
sed -i "s/\[SERVICE_NAME\]/$PROJECT_NAME/g" manifest.example.json

# Update cloudbuild.yaml
sed -i "s/your-service-name/$PROJECT_NAME/g" cloudbuild.yaml

# Update package.json
sed -i "s/goco-project-template/$PROJECT_NAME/g" package.json

# Update README
sed -i "s/goco-project-template/$PROJECT_NAME/g" README.md

# Update Summary.html
sed -i "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" docs/Summary.html

# =============================================
# CREDENTIAL SETUP
# =============================================
echo "--- Setting up credentials ---"

# Create manifest.json from example
cp manifest.example.json manifest.json
echo "[INFO] Created manifest.json — edit with your actual credentials"

# Create .env from template
if [ -f ".env.example" ]; then
  cp .env.example .env
  echo "[INFO] Created .env from .env.example"
else
  cat > .env << 'ENVEOF'
# GO Corporation — Local Development Environment
# Copy values from: Credentials Claude Code/Instructions/API Access Master Instructions.txt
# NEVER commit this file.

# GCP
GCP_PROJECT_ID=ai-agents-go
GCP_REGION=asia-southeast1
GOOGLE_APPLICATION_CREDENTIALS=./credentials/ai-agents-go-4c81b70995db.json

# Peak Accounting
PEAK_CONNECT_ID=
PEAK_CONNECT_KEY=
PEAK_APP_CODE=G3OA4AAA20
PEAK_USER_TOKEN=

# Xero
XERO_CLIENT_ID=
XERO_CLIENT_SECRET=
XERO_TENANT_ID=48470554-28f9-46b0-b9d2-4bbf42b4edf8

# Notion
NOTION_API_KEY=

# Slack
SLACK_BOT_TOKEN=
SLACK_WEBHOOK_URL=

# Figma
FIGMA_TOKEN=

# n8n
N8N_WEBHOOK_KEY=
N8N_BASE_URL=https://gocorp.app.n8n.cloud

# Cloud Run (set after first deploy)
CLOUD_RUN_URL=
ENVEOF
  echo "[INFO] Created .env template — fill in values from Credentials folder"
fi

# Link or copy credential files for local development
echo ""
echo "--- Linking credential files ---"
mkdir -p credentials

if [ -d "$CREDENTIALS_SOURCE" ]; then
  # Symlink key credential files (Windows: copy instead of symlink)
  for FILE in "ai-agents-go-4c81b70995db.json" \
              "client_secret_538978391890-2ol1mrglnelng580ldvj5fi4tkrliqhf.apps.googleusercontent.com.json" \
              "xero_tokens.json" \
              "token_oauth.json" \
              "token_gmail_settings.json"; do
    if [ -f "$CREDENTIALS_SOURCE/$FILE" ]; then
      cp "$CREDENTIALS_SOURCE/$FILE" "credentials/$FILE"
      echo "[INFO] Copied $FILE to credentials/"
    else
      echo "[WARN] $FILE not found in $CREDENTIALS_SOURCE"
    fi
  done
  echo "[INFO] Credential files linked from centralized folder"
else
  echo "[WARN] Credentials source not found: $CREDENTIALS_SOURCE"
  echo "[INFO] Manually copy needed credential files to credentials/"
fi

# Verify .gitignore blocks credentials
echo ""
if grep -q "credentials/" .gitignore 2>/dev/null; then
  echo "[OK] .gitignore blocks credentials/ folder"
else
  echo "[WARN] Adding credentials/ to .gitignore"
  echo "credentials/" >> .gitignore
fi

# Initialize git
if [ ! -d ".git" ]; then
  git init
  git add -A
  git commit -m "chore: bootstrap $PROJECT_NAME from template"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Credential files in credentials/ (gitignored):"
ls -la credentials/ 2>/dev/null || echo "  (empty — copy files manually)"
echo ""
echo "Next steps:"
echo "  1. Fill in .env with values from Credentials Claude Code folder"
echo "  2. Verify credentials/ has the needed JSON files"
echo "  3. Replace src/index.js with your service code"
echo "  4. Run: ./verify.sh"
echo "  5. Push: git remote add origin https://github.com/$GITHUB_ORG/$PROJECT_NAME.git && git push -u origin main"
