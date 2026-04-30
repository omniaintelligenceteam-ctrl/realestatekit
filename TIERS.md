# 3-Tier Listing Offering

Each tier maps to a specific bundle of deliverables for a real-estate listing.
Speak the tier name + drop a Zillow URL (or address + photos + listing description),
and the kit produces exactly what that tier promises — no more, no less.

## Quick reference

| Tier | What she gets | Branding | Hosting | Build time |
|---|---|---|---|---|
| **Tier 1 — Digital** | Landing page · 3-aspect video · Facebook caption · share preview | Dual-branded (her brand + small "by getoios" footer) | `<slug>.netlify.app` | ~15 min |
| **Tier 2 — Listing Kit** | Tier 1 + print PDFs (brochure, leave-behind, postcard) + social pack (4 images + 4 captions) + email blast (HTML + plain + subjects + preview) + photo pack + open-house talking points + social schedule + Kit Dashboard | Dual-branded | `<slug>-kit.netlify.app` | ~20 min |
| **Tier 3 — Monthly Retainer** | Tier 2, **white-label**, on her own custom domain, unlimited listings/month, plus per-listing "Just Sold" follow-up mailer | Full white-label, ZERO OIOS branding | `<slug>.<her-domain>` | ~20 min/listing |

## Trigger phrases

The skill auto-routes when Wes types any of these:

- `Tier 1 — <address> + photos + listing info` → Digital bundle
- `Tier 2 — <address> + photos + listing info` → Listing Kit bundle
- `Tier 3 — <address> + photos + listing info` (requires `as <agent-slug>` profile) → White-label retainer bundle
- Plain Zillow URL: `clone this Zillow listing: <URL>` → defaults to Tier 1
- `<URL> with full kit` → Tier 2
- `<URL> as kim-smith with full kit` → Tier 3 (white-label)

## Tier 1 — Digital ($149/listing target price)

**One-line promise:** A premium landing page she can share + a 3-aspect cinematic video she can post.

**Deliverables:**
- `<slug>.html` — single-file editorial landing page (Italiana / Cormorant / Inter, Hyper-Agent style)
- `<slug>-hero.mp4` (1920×1080) — for the landing page hero
- `<slug>-hero-sq.mp4` (1080×1080) — for Facebook / Instagram feed
- `<slug>-hero-vt.mp4` (1080×1920) — for Reels / Stories
- `facebook-caption.txt` — OIOS-playbook-screened post body (paste-ready)
- `facebook-first-comment.txt` — URL line for first comment (clean post pattern)
- Open Graph + Twitter card meta tags baked into the HTML
- Optional Netlify deploy at `<slug>.netlify.app`

**Run command:** `python tier1.py --listing listing.json --slug <slug>` (defaults to no deploy)
**With deploy:** `python tier1.py --listing listing.json --slug <slug> --deploy`

## Tier 2 — Listing Kit ($299/listing target price)

**One-line promise:** Everything for the listing's marketing in one private dashboard URL she opens on her phone.

**Deliverables (Tier 1 + everything below):**
- `print/brochure-8page.pdf` — 8-page editorial booklet (US Letter)
- `print/leave-behind-1sheet.pdf` — 8.5×11 front+back leave-behind, with QR
- `print/postcard-just-listed.pdf` — USPS 4.25×6 mailer
- `social/fb-feed-1080.png`, `ig-feed-1080.png`, `ig-story-1080x1920.png`, `reels-cover-1080x1920.png`
- `social/instagram-caption.txt` — visual-first + 20 geo-scoped hashtags
- `social/sphere-sms.txt` — ≤160-char text blast
- `email/email-blast.html` — inline-styled, paste into Mailchimp / Constant Contact
- `email/email-blast.txt` — plain-text fallback
- `email/email-subject-lines.txt` — 3 options
- `email/email-preview-text.txt` — 2 options
- `extras/open-house-talking-points.txt` — 7 specific things to mention
- `extras/social-schedule.txt` — D1 FB+IG · D2 Reel · D4 Email · D7 SMS cadence
- `index.html` — Kit Dashboard (the URL she opens on her phone, copy/download buttons)
- Hosted at `<slug>-kit.netlify.app`

**Run command:** `python tier2.py --listing listing.json --slug <slug> --deploy`

## Tier 3 — Monthly Retainer (custom monthly pricing per agent)

**One-line promise:** Everything in Tier 2, white-labeled, on her own domain, unlimited listings, plus follow-up mailers.

**Deliverables (Tier 2 + below):**
- All assets render with **ZERO OIOS branding** anywhere — footer tagline blank, OG titles prefixed with HER brokerage, QR codes target her domain
- Deploys to `<slug>.<her-custom-domain>` (e.g. `148-pheasant-run.listings.smithcorealty.com`)
- `extras/just-sold-postcard.pdf` — same template, different copy (NEW — Tier 3 only)
- Optional: per-agent personal landing page at root of her domain (her bio, brokerage, all active listings rolled up)

**Run command:** `python tier3.py --listing listing.json --agent kim-smith --slug <slug> --deploy`

Requires a `agents/<agent-slug>.json` brand profile with:
- `tier: "monthly"`
- `custom_domain: "listings.smithcorealty.com"` (she owns this domain)
- `logo_path`, `headshot_path`, `primary_color`, `accent_color` filled in
- `phone`, `email`, `license_number` filled in

**One-time setup per agent (~30 min):**
1. She owns/registers a domain (e.g. `smithcorealty.com`).
2. She adds CNAME record: `*.listings.smithcorealty.com → <netlify-load-balancer>`.
3. We add the wildcard domain to her Netlify site config.
4. Netlify auto-provisions SSL via Let's Encrypt.
5. From then on, every listing deploys to `<slug>.listings.smithcorealty.com` with zero OIOS branding.

## Tier comparison matrix (the upsell story)

| Asset | Tier 1 | Tier 2 | Tier 3 |
|---|:-:|:-:|:-:|
| Landing page | ✅ | ✅ | ✅ |
| 3-aspect video | ✅ | ✅ | ✅ |
| Facebook caption | ✅ | ✅ | ✅ |
| Print PDFs (brochure / leave-behind / postcard) | ❌ | ✅ | ✅ |
| Social images (FB/IG/Story/Reels) | ❌ | ✅ | ✅ |
| Social captions (IG/SMS) | ❌ | ✅ | ✅ |
| Email blast (HTML/txt/subjects/preview) | ❌ | ✅ | ✅ |
| Open-house talking points | ❌ | ✅ | ✅ |
| Suggested 7-day post schedule | ❌ | ✅ | ✅ |
| Photo pack (zip of full-res selects) | ❌ | ✅ | ✅ |
| Kit Dashboard (private URL) | ❌ | ✅ | ✅ |
| White-label (zero OIOS branding) | ❌ | ❌ | ✅ |
| Custom domain (her own URL) | ❌ | ❌ | ✅ |
| "Just Sold" follow-up mailer | ❌ | ❌ | ✅ |
| Unlimited listings/mo | ❌ | ❌ | ✅ |
| Personal agent landing page | ❌ | ❌ | ✅ |

## Why this gates correctly

- **Tier 1 is the entry point** — cheap, fast, gets her hooked on the quality.
- **Tier 2 unlocks the binder** — the leave-behind in the binder + the email blast + the dashboard URL she opens on her phone. This is the real value drop.
- **Tier 3 is the lock-in** — once she's white-labeled on her own domain, leaving us means giving up her brand infrastructure. That's the retainer thesis.

The dashboard URL itself is also the ad — agents who see her listings click through, see "Listing Kit by getoios.com" in the footer (Tier 1/2 only), and ask her who built it.
