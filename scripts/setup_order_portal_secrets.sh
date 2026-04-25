#!/usr/bin/env bash
# Idempotent setup for GCP resources the Order Portal needs.
#
# Creates (if missing) these Secret Manager secrets on project ai-agents-go:
#   - salesheet-flask-session-key     (auto-generated random)
#   - firebase-web-api-key            (prompts for value)
#
# Grants roles to the Cloud Run service account
# claude@ai-agents-go.iam.gserviceaccount.com:
#   - roles/firebase.sdkAdminServiceAgent      (project)
#   - roles/datastore.user                     (project — products-wood db)
#   - roles/secretmanager.secretAccessor       (new secrets above)
#   - roles/secretmanager.secretAccessor       (existing Xero secrets)
#   - roles/secretmanager.secretVersionAdder   (xero-tokens — for refresh)
#
# This script is SAFE to re-run. Each operation uses describe-or-create
# and set-iam-policy-binding (additive).

set -euo pipefail

PROJECT="${PROJECT:-ai-agents-go}"
REGION="${REGION:-asia-southeast1}"
SA="claude@${PROJECT}.iam.gserviceaccount.com"

NEW_SECRETS_AUTOGEN=(
  "salesheet-flask-session-key"
)
NEW_SECRETS_PROMPT=(
  "firebase-web-api-key"
)
XERO_SECRETS_ACCESSOR=(
  "xero-client-id"
  "xero-client-secret"
  "xero-tenant-id"
  "xero-tokens"
)

echo "==> Setting project to ${PROJECT}"
gcloud config set project "${PROJECT}" --quiet

ensure_secret_exists_with_auto_value() {
  local name="$1"
  if gcloud secrets describe "${name}" >/dev/null 2>&1; then
    echo "  [skip] ${name} already exists"
    return
  fi
  echo "  [create] ${name} (auto-generating random value)"
  openssl rand -hex 32 | gcloud secrets create "${name}" \
    --replication-policy=automatic --data-file=- --quiet
}

ensure_secret_exists_prompted() {
  local name="$1"
  local prompt="$2"
  if gcloud secrets describe "${name}" >/dev/null 2>&1; then
    echo "  [skip] ${name} already exists"
    return
  fi
  echo ""
  echo "  Need ${name}."
  echo "  ${prompt}"
  read -r -s -p "  Paste value and press Enter (input hidden): " value
  echo ""
  if [[ -z "${value}" ]]; then
    echo "  [WARN] Empty value — skipping ${name}. Re-run when you have it."
    return
  fi
  printf '%s' "${value}" | gcloud secrets create "${name}" \
    --replication-policy=automatic --data-file=- --quiet
  echo "  [ok] ${name} created"
}

grant_secret_role() {
  local secret="$1"
  local role="$2"
  echo "  [iam] ${secret} -> ${SA} ${role}"
  gcloud secrets add-iam-policy-binding "${secret}" \
    --member="serviceAccount:${SA}" --role="${role}" --quiet >/dev/null
}

grant_project_role() {
  local role="$1"
  echo "  [iam] project -> ${SA} ${role}"
  gcloud projects add-iam-policy-binding "${PROJECT}" \
    --member="serviceAccount:${SA}" --role="${role}" --quiet >/dev/null
}

echo ""
echo "==> 1. Create new secrets (auto-generated)"
for s in "${NEW_SECRETS_AUTOGEN[@]}"; do
  ensure_secret_exists_with_auto_value "${s}"
done

echo ""
echo "==> 2. Create new secrets (prompt for value)"
ensure_secret_exists_prompted "firebase-web-api-key" \
  "Get this from Firebase console > Project settings > Your apps > Web app > 'apiKey' (NOT the server/admin key)."

echo ""
echo "==> 3. Grant service-account IAM on new secrets"
for s in "${NEW_SECRETS_AUTOGEN[@]}" "${NEW_SECRETS_PROMPT[@]}"; do
  if gcloud secrets describe "${s}" >/dev/null 2>&1; then
    grant_secret_role "${s}" "roles/secretmanager.secretAccessor"
  else
    echo "  [warn] ${s} doesn't exist yet — skipping IAM"
  fi
done

echo ""
echo "==> 4. Grant service-account IAM on existing Xero secrets (shared with accounting-automation)"
for s in "${XERO_SECRETS_ACCESSOR[@]}"; do
  if gcloud secrets describe "${s}" >/dev/null 2>&1; then
    grant_secret_role "${s}" "roles/secretmanager.secretAccessor"
  else
    echo "  [warn] ${s} not found — accounting-automation may not be set up yet."
    echo "         Xero features will be disabled until these exist."
  fi
done

# Special: xero-tokens needs versionAdder too, so the salesheet service can
# write refreshed tokens back (both services share this secret).
if gcloud secrets describe "xero-tokens" >/dev/null 2>&1; then
  grant_secret_role "xero-tokens" "roles/secretmanager.secretVersionAdder"
fi

echo ""
echo "==> 5. Grant project-level roles"
grant_project_role "roles/firebase.sdkAdminServiceAgent"
grant_project_role "roles/datastore.user"

echo ""
echo "==> Done."
echo ""
echo "Remaining MANUAL steps (one-time, Firebase console):"
echo "  1. https://console.firebase.google.com/project/${PROJECT}/authentication/providers"
echo "     Enable 'Email/Password' + 'Google' sign-in providers."
echo "  2. Authentication → Settings → Authorized domains → add 'salessheet.leka.studio'"
echo "  3. In Slack: /invite @ai_agents  in  #orders-wood-products  (C0AUABRBK41)"
echo ""
echo "Redeploy: push any commit on main → Cloud Build trigger runs automatically,"
echo "          or trigger manually:  gcloud builds submit --config=website/salesheet/cloudbuild.yaml ."
