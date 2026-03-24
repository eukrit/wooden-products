#!/bin/bash
# setup.sh — Bootstrap a new project from the GO Corporation template
# Usage: ./setup.sh <project-name> [github-org]

set -e

PROJECT_NAME="${1:?Usage: ./setup.sh <project-name> [github-org]}"
GITHUB_ORG="${2:-eukrit}"

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

# Create manifest.json from example
cp manifest.example.json manifest.json
echo "[INFO] Created manifest.json — edit with your actual credentials"

# Initialize git
if [ ! -d ".git" ]; then
  git init
  git add -A
  git commit -m "chore: bootstrap $PROJECT_NAME from template"
fi

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Edit manifest.json with your actual API keys"
echo "  2. Replace src/index.js with your service code"
echo "  3. Run: ./verify.sh"
echo "  4. Push: git remote add origin https://github.com/$GITHUB_ORG/$PROJECT_NAME.git && git push -u origin main"
