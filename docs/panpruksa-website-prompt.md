# Panpruksa Website Build — Continuation Prompt

Copy and paste everything below as a prompt in a new Claude Code session in this same project folder.

---

## PROMPT START

I need you to build the Panpruksa brand website on Webflow. Here is the full context:

### 1. Brand Identity — Panpruksa

Panpruksa is a premium wood flooring brand operated by **Nubo International Pte. Ltd.** The visual identity is inspired by Listone Giordano's luxury Italian aesthetic but adapted for the Southeast Asian market.

**Company Details (from Notion):**
- Legal name: **Nubo International Pte. Ltd.**
- Address: 20 Jalan Mutiara, Singapore 249199
- Business Registration ID: 202424115G
- Contact: contact@nubo.asia
- Key contacts:
  - Edmund Lim: +65 9191 1192 / edmund@nubo.asia
  - Eukrit Kraikosol: +66 61 491 6393 / eukrit@nubo.asia
- Website domain: panpruksa.design.webflow.com (Webflow)
- Parent distributor relationship with GO Corporation Co., Ltd. (Thailand)

### 2. Design System (based on Listone Giordano)

The full design system JSON is at: `data/parsed/listone-giordano-design-system.json`
The full product catalog JSON is at: `data/parsed/listone-giordano-products.json`
Downloaded brand assets (font, images, icons) are at: `data/images/listone-giordano/`

**Typography:**
- Logo/brand: Use a custom serif font similar to "LG Corporate" — recommend **Cormorant Garamond** or **Playfair Display** from Google Fonts as the Panpruksa wordmark font
- Body text: **Source Sans Pro** (Google Fonts), weight 300 for body, 400 for headings
- Navigation: Source Sans Pro weight 300, ~34px

**Color Palette:**
- Primary: Black (#000000) and White (#FFFFFF)
- Background: Warm gray gradient (#CBCBCB to white), similar to brushed metal effect
- Accent: Copper/bronze (#B87333) — subtle line at section transitions
- Text: Black on light backgrounds, White on dark/hero backgrounds
- Buttons: Outlined black borders, transparent background, uppercase text

**Layout Principles:**
- Asymmetric editorial grid layout
- Full-bleed hero images with text overlays
- Generous whitespace, architectural magazine feel
- Hamburger navigation (top-right), wordmark logo (top-left)
- Scroll indicator on right edge
- Sidebar icons for catalog, store locator, share

**UI Components:**
- Buttons: Outlined/bordered style, 1px solid black, uppercase, wide padding
- Link buttons: Text with arrow format ("LABEL →")
- Cards: Image with text overlay at bottom
- Carousels: Horizontal scroll with dot indicators

### 3. Website Pages to Build (NO products/solutions sections)

Build these pages on Webflow at `panpruksa.design.webflow.com`:

#### Homepage
- Hero section with full-bleed image and brand tagline
- "Be Inspired" projects carousel showing luxury interiors
- "About Panpruksa" brief intro section
- "Our Partners" / brand associations section
- Digital magazine / news teaser
- Footer with company details, social links, navigation

#### About / Brand
- Heritage story (Nubo International's journey)
- Brand philosophy: synthesis of aesthetics and ethics, nature and technology
- Technology section (multilayer wood flooring technology)
- Sustainability / environmental commitment

#### Projects
- Grid gallery of luxury residential and commercial projects
- Each project card: full-width image, project name, location, type
- Placeholder content — use the Listone Giordano project images from `data/images/listone-giordano/projects/`

#### Designers
- Feature notable designers and collaborations
- Placeholder content for now

#### Stores / Where to Buy
- Store locator map placeholder
- Contact information for Singapore and Thailand offices

#### News
- Blog/news listing page
- Placeholder articles about wood flooring, design trends

#### Contact
- Contact form (see section 4 below for Slack integration)
- Office addresses:
  - **Singapore (HQ):** 20 Jalan Mutiara, Singapore 249199 | +65 9191 1192
  - **Thailand (Distribution):** 11/2 Floor 8 Unit 8A, Sukhumvit 23, Sukhumvit Rd, Khlong Toei Nuea, Watthana, Bangkok 10110 | +66 2 124 5000
- Email: contact@nubo.asia
- Embedded Google Map for both locations

### 4. Contact Form → Slack Integration

Create a contact form on the Contact page with these fields:
- Full Name (required)
- Email (required)
- Phone (optional)
- Company/Project (optional)
- Country (dropdown: Singapore, Thailand, Malaysia, Indonesia, Vietnam, Other)
- Message (textarea, required)
- Submit button: "SEND ENQUIRY"

**Slack Integration:**
- Create a new Slack channel `#panpruksa-leads` (public channel)
- Use the Slack MCP connector to create the channel
- Set up form submission to post to `#panpruksa-leads` via one of these methods:
  1. **Webflow + Zapier/Make**: Webflow native form → webhook → Slack incoming webhook
  2. **Webflow + n8n**: Use existing n8n instance at gocorp.app.n8n.cloud to create a workflow: Webflow webhook trigger → format message → post to Slack
  3. **Direct Slack webhook**: Create a Slack incoming webhook for #panpruksa-leads and configure Webflow form to POST to it

The Slack message format should be:
```
🏠 New Panpruksa Lead
*Name:* {name}
*Email:* {email}
*Phone:* {phone}
*Company:* {company}
*Country:* {country}
*Message:* {message}
```

### 5. Webflow Implementation Notes

- Use the Webflow MCP tools to build pages
- Site slug: `panpruksa`
- Use Webflow CMS for Projects and News (so content can be updated without code)
- Implement responsive design (desktop, tablet, mobile)
- Use interactions/animations for scroll reveals and hover effects
- Optimize images for web (use WebP where possible)
- Add SEO meta tags for each page
- Add Google Analytics placeholder

### 6. DO NOT Include

- No product catalog or individual product pages
- No solutions/applications section
- No pricing or e-commerce functionality
- No user login/registration
- No downloads section (login-gated content)

### 7. Reference Files

All reference files are in this project:
- `data/parsed/listone-giordano-design-system.json` — Full design system spec
- `data/parsed/listone-giordano-products.json` — Product data for reference only
- `data/images/listone-giordano/brand/` — Heritage images and LG Corporate font
- `data/images/listone-giordano/collections/` — Collection hero images
- `data/images/listone-giordano/colors/` — Wood texture swatch images
- `data/images/listone-giordano/projects/` — Project photography for placeholders

Start by reading the design system JSON, then create the Slack channel, then build the Webflow site page by page starting with the homepage.

## PROMPT END
