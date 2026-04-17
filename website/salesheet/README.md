# Leka Salesheet Platform — Build Playbook

Reproducible recipe for building Leka Studio product sales microsites.
Uses the Leka Design System from Figma (`ER6pbDqrJ4Uo9FuldnYBfm`) and ships to
`salesheet.leka.studio/<product-slug>/` via Cloud Run.

**Reference implementation:** `wpc-fence/` (this repo).
**Live URL:** <https://salesheet.leka.studio/wpc-fence/>

---

## 1. Architecture at a glance

```
 Customer browser
        │
        ▼
 salesheet.leka.studio  ──CNAME──▶  ghs.googlehosted.com
        │                             (Google Cloud Run Frontend)
        ▼
 Cloud Run: salesheet-leka (asia-southeast1)
        │
        ├── Flask + gunicorn (server.py)
        │     ├── GET /, /<slug>/ → static HTML
        │     ├── GET /<slug>/images/* → lazy-cached assets
        │     ├── GET /_healthz
        │     └── POST /api/quote → validates + forwards to Slack
        │
        └── Secrets (GSM, mounted as env vars)
              ├── SLACK_BOT_TOKEN  (slack-bot-token:latest)
              └── SLACK_LEAD_CHANNEL (plain env: C07EF698Q1K = #bd-new-leads)
```

DNS records for subdomains live at **GoDaddy**. Updates are scripted via the
GoDaddy API using the key stored in GSM secret `godaddy-api`
(format `KEY:SECRET`).

---

## 2. Folder structure

```
website/salesheet/
├── Dockerfile              # python:3.12-slim + gunicorn
├── .dockerignore
├── requirements.txt        # flask, gunicorn
├── server.py               # Flask app — static + /api/quote
├── index.html              # salesheet.leka.studio/ landing (lists products)
├── README.md               # this playbook
└── <product-slug>/         # one folder per product
    ├── index.html          # the sales sheet (long-scroll web page)
    └── images/             # self-contained product photos
        └── *.{jpg,png}
```

Each `<product-slug>/` is fully self-contained: images live inside the slug
folder, HTML references them as `images/<name>`. This keeps Cloud Build
uploads fast and lets any product be yanked independently.

---

## 3. Leka Design System tokens

Pulled directly from the Figma file (`get_metadata` + `get_design_context`
via the Figma remote MCP or REST API with the `figd_…` PAT). **Do not invent
new tokens** — match what is defined in Figma.

### Colour

| Role | Token (CSS var) | Hex |
|---|---|---|
| Primary action | `--lk-purple` | `#8003FF` |
| Primary dark / text | `--lk-navy` | `#182557` |
| Primary light / surface | `--lk-cream` | `#FFF9E6` |
| Accent — depth | `--lk-magenta` | `#970260` |
| Accent — energy | `--lk-amber` | `#FFA900` |
| Accent — caution | `--lk-red-orange` | `#E54822` |
| Utility | `--lk-white` / `--lk-black` | `#FFFFFF` / `#000000` |
| Purple button BG variant | `--lk-purple-bg` | `#8000FF` |

Derived shades used for text/borders — always from navy or cream with alpha:
`--lk-navy-80`, `--lk-navy-60`, `--lk-navy-12`, `--lk-navy-06`, `--lk-cream-80`, `--lk-cream-60`.

### Typography — Manrope

Font family `Manrope` (Google Fonts, weights 200/300/400/500/600/700/800).
All sizes in px — **these exact values are in Figma**, so just reference them:

| Role | Size | Weight |
|---|---|---|
| Display | 72 | 800 |
| H1 | 48 | 800 |
| H2 | 36 | 700 |
| H3 | 28 | 700 |
| H4 | 24 | 600 |
| H5 | 20 | 600 |
| H6 | 18 | 600 |
| Body Large | 18 | 400 |
| Body | 16 | 400 |
| Body Small | 14 | 400 |
| Caption | 12 | 500 (UPPERCASE, letter-spacing 0.12em) |

Line-height ratio from Figma ≈ **1.366**. For headlines use `1.15`; for
body use `1.55 – 1.65`. Letter-spacing on big headlines `-0.01em` to `-0.02em`.

### Spacing scale

| Token | px |
|---|---|
| `--space-xs` | 4 |
| `--space-sm` | 8 |
| `--space-md` | 16 |
| `--space-lg` | 24 |
| `--space-xl` | 32 |
| `--space-2xl` | 48 |
| `--space-3xl` | 64 |
| `--space-4xl` | 96 |

### Radius scale

| Token | px |
|---|---|
| `--radius-none` | 0 |
| `--radius-sm` | 4 |
| `--radius-md` | 8 |
| `--radius-lg` | 16 |
| `--radius-xl` | 24 |
| `--radius-full` | 9999 |

**Pills everywhere.** Buttons and badges use `--radius-full`. Cards use
`--radius-lg`. Decorative surfaces use `--radius-xl`.

---

## 4. Component patterns (reusable)

Copy these from `wpc-fence/index.html` and adapt copy/content:

- `.nav` — sticky glass navigation with Leka logo left + section links + primary CTA right
- `.hero` — full-viewport hero with background image at `opacity: 0.32`, navy gradient overlay, vertical colour-blade accent at left
- `.stats` — cream strip with 4 large numeric stats
- `.manifesto` — single large-paragraph intro (22–28px Manrope 500)
- `.range-grid` + `.range-card` — 2-up product cards with image, badge, caption, spec list
- `.spec-block` + `.spec-table` — comparison table inside a cream panel with xl radius
- `.two-col` + `.feature-card` — 2×2 feature tiles with circular accent icon
- `.config-grid` + `.config-card` — 3-up configuration cards
- `.install-wrap` — diagram + numbered step cards (1–4)
- `.palette` + `.swatch` — 4-up colour swatches
- `.apps` + `.app-card` — 3-up cream panels with top accent stripe
- `.compare-table` — comparison table with navy header and winner-highlighted column
- `.warranty-grid` + `.warranty-card` — large numeric years + summary
- `.warranty-detail` — detailed ΔE + exclusions + claim process + disclaimer
- `.cta-banner` — dark section with radial purple glow
- `.footer` — dark, 4-col, ends with "Never Done Playing" tagline in amber italic

Buttons: `.btn .btn-primary`, `.btn-outline`, `.btn-navy`, `.btn-lg`.
Badges: `.badge .badge-purple|amber|red-orange|navy|cream`.

### Quote modal

Open with `data-quote-open` attribute on any CTA. Close on: click overlay,
click `.modal-close`, or press `Escape`. 13 fields, required-marked with red
asterisk. Honeypot field `.hp-field > input[name=_hp]` hidden off-screen.
Submit → `POST /api/quote` with JSON body.

### Breakpoints

- `@media (max-width: 960px)` — collapse 2/3-up grids to 1, hide nav text links
- `@media (max-width: 560px)` — full-width buttons, full-screen modal, single-column everywhere

---

## 5. Page section template

Every product sales sheet follows this section order:

1. **Nav** (sticky)
2. **Hero** — eyebrow + display headline + sub + badges + 2 CTAs
3. **Stats strip** — 4 key numbers on cream
4. **Manifesto** — one big paragraph; product in one sentence
5. **Product range** — 2-up comparison cards
6. **Spec table** — full technical data, side-by-side
7. **Material / science** — 4 feature tiles
8. **Hardware / systems** — split 2-col detail list
9. **Configurations** — 3-up product cards
10. **Installation** — diagram + 4 numbered steps
11. **Gallery** — 3 context photos
12. **Colour palette** — 4 or 8 swatches
13. **Applications** — 3-up panels
14. **Comparison vs alternatives** — horizontal table
15. **Warranty** — see section 8 below
16. **CTA banner** — open-quote-modal button
17. **Footer** — 4-col dark

---

## 6. Backend — Flask `server.py`

### Contract

| Endpoint | Verb | Response |
|---|---|---|
| `/` | GET | Landing `index.html` |
| `/<path>` or `/<path>/` | GET | Static file or `<path>/index.html` |
| `/_healthz` | GET | `ok` plain text |
| `/api/quote` | POST | JSON `{ok: true}` · 400/429/202 degraded |

### `POST /api/quote` rules

- **Required**: `name`, `email` (regex), `projectType ∈ {residential|hospitality|commercial|other}`, `length` (1–10 000 m), `series ∈ {premium|classic|undecided}`
- **Honeypot**: `_hp` field — if set, silently returns `{ok: true}` without forwarding
- **Rate limit**: 15 s per IP (in-memory; fine for single-instance / low volume)
- **Email / phone are redacted** in structured logs

### Slack forward

Bot uses `chat.postMessage` with a Block Kit payload — header + section fields
+ optional message block + context line + primary-style "Email back" action
button (pre-fills `mailto:<customer>?subject=Re:%20WPC%20Fence%20enquiry`).

If Slack fails (token missing, channel not found, network) the API returns
**HTTP 202** with `{ok: true, degraded: true, warning: "…"}` — the user still
sees a success message, details captured in Cloud Run logs for recovery.

---

## 7. Slack setup for a new lead channel

Leads from sales sheets currently go to `#bd-new-leads` (`C07EF698Q1K`).

To route to a **different** channel for a different product:

1. Find the channel ID via user-token message search:
   ```bash
   curl -s -G "https://slack.com/api/search.messages" \
     -H "Authorization: Bearer $SLACK_USER_TOKEN" \
     --data-urlencode 'query=in:#channel-name' --data-urlencode 'count=1' \
     | python -c "import json,sys; d=json.load(sys.stdin); \
       print(d['messages']['matches'][0]['channel']['id'])"
   ```
2. Redeploy Cloud Run with:
   `--set-env-vars SLACK_LEAD_CHANNEL=<CHANNEL_ID>`
3. **Invite the bot to private channels** — bot `@ai_agents` (user id
   `U0ALU8DG6AW`) cannot self-join private channels. In Slack:
   `/invite @ai_agents`

Bot token scopes required: `chat:write` and the channel must either be
public-joined or bot-invited.

---

## 8. Warranty copy — guardrails

Leka is the **distributor**, not the manufacturer. Every sales sheet's
warranty section must do four things to keep you protected from claims
(especially the sensitive ones — colour fade, "it looks different now"):

1. **Structural vs surface split** — state them separately, never as one
   bundled number. E.g. "25-year structural / 10-year surface" for Premium.
2. **Measurable fade standard** — never promise "no fade". Write:
   - Premium: ΔE ≤ 5 over 10 y (ISO 4892-2)
   - Classic: ΔE ≤ 8 over 5 y (ISO 4892-2)
   Call out that uneven fade in permanent shade / standing water is not a
   warrantable defect.
3. **Specific exclusions list** — non-certified install, post-install
   coating, submersion / salt / pool chemicals, impact / fire / vandalism,
   heat sources > 75 °C, solvent / bleach / pressure > 1500 psi,
   structural misuse. Batch-to-batch colour variation is NOT a defect.
4. **Claim process + legal disclaimer**:
   - 60-day written notice to `warranty@leka.studio`
   - Remedy = **board replacement or material credit only** (no labour,
     site access, consequential damages)
   - Warranty is **pass-through from manufacturer's published limited
     warranty current at delivery**; all other warranties (merchantability,
     fitness) disclaimed

Reuse the `.warranty-detail` CSS + markup block in `wpc-fence/index.html`
verbatim for new products — only the year numbers and ΔE thresholds change.

---

## 9. Content rules

- **No vendor/supplier names.** No "Anhui Aolo", "Jackson", "Sentai",
  factory product codes (`GK161.5-20C`, etc.) — anywhere. Every product is
  presented as a Leka-curated collection.
- **No Chinese characters** anywhere in HTML or committed images. Check
  image stickers / labels before using a photo. Grep:
  `rg '[\u4e00-\u9fff]' wpc-fence/`
- **No prices by default.** Sales sheets are specification documents.
  Pricing is handled by the quote form → BD team responds with bespoke
  quotation. Only surface pricing when a product explicitly has a list
  price that is public.
- **Generic colour codes**: `LK-01` … `LK-08` for Leka palette. Do not
  mirror supplier colour codes.

---

## 10. Cloud Run deployment

Full deploy command (from `website/salesheet/`):

```bash
gcloud run deploy salesheet-leka \
  --source . \
  --region asia-southeast1 \
  --project ai-agents-go \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --port 8080 \
  --service-account claude@ai-agents-go.iam.gserviceaccount.com \
  --set-env-vars "SLACK_LEAD_CHANNEL=C07EF698Q1K" \
  --set-secrets "SLACK_BOT_TOKEN=slack-bot-token:latest" \
  --quiet
```

Smoke test after deploy:

```bash
BASE="https://salesheet-leka-538978391890.asia-southeast1.run.app"
for p in "" "wpc-fence/" "wpc-fence/images/141.jpg" "_healthz"; do
  curl -s -o /dev/null -w "%{http_code}  $p\n" "$BASE/$p"
done
```

---

## 11. DNS — GoDaddy API via GSM

```bash
# 1. Read key from GSM
GODADDY=$(gcloud secrets versions access latest --secret=godaddy-api --project=ai-agents-go)
KEY="${GODADDY%%:*}"; SECRET="${GODADDY##*:}"

# 2. Create / upsert CNAME on leka.studio
curl -s -X PUT \
  "https://api.godaddy.com/v1/domains/leka.studio/records/CNAME/<subdomain>" \
  -H "Authorization: sso-key ${KEY}:${SECRET}" \
  -H "Content-Type: application/json" \
  -d '[{"data":"ghs.googlehosted.com","ttl":600}]'

# 3. Create Cloud Run domain mapping (goco.bz + leka.studio pre-verified)
gcloud beta run domain-mappings create \
  --service salesheet-leka \
  --domain <subdomain>.leka.studio \
  --region asia-southeast1 \
  --project ai-agents-go
```

Notes:

- DNS typically propagates to Google's public resolver within 1–2 minutes.
- Cloud Run managed SSL cert provisioning takes **15–60 minutes** after DNS
  is in place. Poll with:
  ```bash
  gcloud beta run domain-mappings describe --domain <subdomain>.leka.studio \
    --region asia-southeast1 --project ai-agents-go \
    --format="value(status.conditions[0].type,status.conditions[0].status)"
  ```
  Ready=True + live HTTPS response = done.
- During the window where `Ready=True` but edge nodes haven't got the cert,
  TLS handshake returns EOF. Wait another 3–5 min and retry.

---

## 12. Adding a new product sales sheet — step-by-step

1. **Gather assets** — product photos (verify no Chinese stickers / vendor
   codes), specs in plain language, copy draft. Save source images in
   `website/salesheet/<slug>/images/`.
2. **Copy reference** — `cp -r website/salesheet/wpc-fence
   website/salesheet/<slug>` and rewrite `index.html` section-by-section.
3. **Update landing** — add a link to the new slug in
   `website/salesheet/index.html`.
4. **Warranty** — start from the `wpc-fence` warranty block; update years,
   ΔE thresholds, and any product-specific exclusions. Never soften the
   legal-disclaimer block.
5. **Quote modal** — usually only the series / colour selects change.
   Keep the same required-field set.
6. **Preview locally** — use the Claude Preview MCP or:
   ```bash
   cd website/salesheet && python server.py
   # serves on http://localhost:8080
   ```
7. **Redeploy** — run the Cloud Run deploy command (section 10). No DNS
   changes needed.
8. **Commit & push** — `git commit` with `feat(salesheet): add <slug>
   product sheet` and push to `eukrit/wooden-products`.

---

## 13. Troubleshooting / gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Form submission returns 202 `degraded: true` | Bot not in target Slack channel | `/invite @ai_agents` in that channel |
| Logs show `slack_error: channel_not_found` | Wrong `SLACK_LEAD_CHANNEL` env var, or channel is private + bot not invited | Verify channel ID; invite bot |
| Custom-domain HTTPS returns EOF but `Ready=True` | Cert still propagating to edge | Wait 3–5 min, retry |
| `Ready=Unknown / Waiting for certificate provisioning` for > 15 min | DNS hasn't reached Google's cert-provisioning poller | Check `nslookup <host> 8.8.8.8` resolves to `ghs.googlehosted.com`; if yes, just wait (first-time provisioning can be slow) |
| Lots of `404 /<slug>/%23<anchor>` in logs | A link-check crawler is treating anchor fragments as paths | Ignore — not a real bug |
| A4 page printable export needed | Use the browser's Print → Save as PDF; the web sales sheet is not A4-optimised. For true A4 collateral use the `go-documents` repo templates instead. |
| Want to test submission without triggering Slack | Set `_hp` in the payload — honeypot path returns `{ok:true}` silently |

---

## 14. Credits

- **Figma design system**: `Leka Design System Claude`
  <https://www.figma.com/design/ER6pbDqrJ4Uo9FuldnYBfm/Leka-Design-System-Claude>
- **Brand template reference**: `eukrit/go-documents` —
  `material-submission-template.html`
- **Infrastructure**: GCP project `ai-agents-go`, region `asia-southeast1`,
  service account `claude@ai-agents-go.iam.gserviceaccount.com`
- **Secrets source of truth**: GCP Secret Manager (`godaddy-api`,
  `slack-bot-token`)
