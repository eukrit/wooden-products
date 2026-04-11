# WPC Fence Website — Status & Handoff Notes

## What's Built (Static HTML/CSS/JS)
All 6 pages are complete and committed. Images downloaded from Slack.

| Page | File | Status | Notes |
|---|---|---|---|
| Landing | `index.html` | Done | Hero, features, product cards, stats, gallery, CTA |
| Product Catalog | `products.html` | Done | 4 tabs (Co-Ex, Standard, Posts, Gates), color swatches, kit list |
| Configurator | `configurations.html` | Done | Interactive calculator with THB pricing, 3 config cards |
| Gallery | `gallery.html` | Done | 17 photos, 3 category filters, lightbox viewer |
| Why WPC? | `comparison.html` | Done | Comparison table, 10-yr TCO chart, eco section, warranty |
| Contact | `contact.html` | Done | Inquiry form, contact info, map placeholder |

## Assets
- `css/style.css` — Shared stylesheet (charcoal + warm wood palette)
- `js/main.js` — Nav toggle, tabs, filters, lightbox, fence calculator
- `images/` — 37 product photos from Slack #vendor-anhui-aolo-wpc

## Outstanding for Webflow Rebuild
These items need to be carried over when rebuilding in Webflow:

### Content to Migrate
1. **Product specs** — All in `PROMPT.md` and `products.html`
2. **Pricing logic** — Configurator calculator in `js/main.js` (`calculateFence()`)
3. **Color palette** — 8 colors with hex codes in CSS and products page
4. **Comparison data** — Full table in `comparison.html`
5. **SEO meta tags** — OG tags, JSON-LD structured data in each page
6. **37 product images** — In `images/` folder, all from Slack

### Features to Recreate
- Interactive fence configurator (height/length/series/gates → price estimate)
- Gallery with category filters + lightbox
- 10-year TCO bar chart
- Floating WhatsApp + LINE buttons
- Mobile-responsive nav with hamburger

### Design Specs
- **Font**: Inter (Google Fonts)
- **Colors**: Charcoal #333, Wood #8B6914, Sienna #A0522D, Green #4CAF50, Off-white #f8f6f2
- **Breakpoints**: 1024px (tablet), 768px (mobile), 480px (small mobile)

### Not Yet Done
- Thai language toggle (marked as phase 2 in brief)
- Real map embed (placeholder in contact page)
- Real phone numbers (placeholder XXX in contact)
- Form backend / submission handler
- Image optimization (originals from Slack, not compressed)
- Favicon

## Key Rules
- **NO vendor names**: Anhui Aolo, Jackson, Sentai, AL-GK, GK161 — none appear anywhere
- Everything branded as **GO Corporation Co., Ltd.**
- Pricing in THB with 35-45% markup over landed cost
