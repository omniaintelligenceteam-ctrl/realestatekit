---
name: zillow-clone
description: Turn a Zillow listing URL into a single-file Hyper-Agent-style marketing landing page in ~/Downloads/, optionally with a Ken-Burns + ElevenLabs narration video, print-ready PDFs (brochure / leave-behind one-sheet / Just-Listed postcard), and an auto-deployed Netlify URL. White-label per real-estate agent via brand-profile JSON. Triggers - "clone this Zillow listing", "/zillow-clone <URL>", "remake this Zillow listing", "make me a landing page for <Zillow URL>", "with narration", "with video", "with hero video", "and host it", "and deploy it", "and put it online", "with print kit", "with full kit", "with the binder package", "with the listing kit", "as <agent-slug>".
---

# Zillow Clone

Take a Zillow listing URL → produce a self-contained editorial-style HTML landing page (hero + narrative + masonry gallery + details + map + agent card) saved to `~/Downloads/<slug>.html`. Replaces paying Hyper Agent per listing.

## When to use

- "clone this Zillow listing: <URL>"
- "/zillow-clone <URL>"
- "remake this Zillow listing as a landing page"
- "make me a landing page for <Zillow URL>"
- "/zillow-clone <URL> with print kit" — produces brochure + leave-behind + postcard PDFs
- "/zillow-clone <URL> with full kit and host it" — landing page + 3-aspect video + print PDFs + Netlify deploy
- "/zillow-clone <URL> as kim-smith with full kit" — runs with a specific agent's brand profile (white-label)
- Wes drops a `zillow.com/homedetails/...` URL and asks for a marketing page

## When NOT to use

- Wes wants a Zestimate / pricing analysis → just summarize, don't build a page
- Listing isn't on Zillow (Realtor.com / agent's site / MLS direct) → ask before adapting; this skill's extraction pipeline is Zillow-specific
- He wants a multi-listing page or a city/neighborhood roundup → out of scope, draft from scratch
- Editing an already-generated landing page → just `Edit` the existing file directly

## Inputs

- **Zillow listing URL** (required, must be `zillow.com/homedetails/...`)
- **Output filename slug** (optional — default: derive from address, e.g. `116-country-club-lane-paducah-ky.html`)
- **Hero mode** (optional): `static` (default — fast, no audio) OR `video` (full Hyper-Agent-style — Ken Burns + ElevenLabs narration). Triggered by "with video", "with narration", or "with hero video" in the user request.
- **Hosting mode** (optional): `local` (default — file in Downloads only) OR `netlify` (auto-deploys to a Netlify subdomain named after the address). Triggered by "and host it", "and deploy it", "and put it online" in the user request.
- **Print kit** (optional): `off` (default) OR `on` — generates 3 print-ready PDFs (8-page editorial brochure + 8.5×11 leave-behind one-sheet + 4×6 "Just Listed" postcard) into `~/Downloads/<slug>-kit/print/`. Triggered by "with print kit", "with full kit", "with the binder package", "with the listing kit". When ON, auto-generates a QR code targeting the deployed Netlify URL (or per-listing fallback). Uses `print/render_pdfs.py` — see "Print Kit (Stage 1)" section.
- **Brand profile** (optional): agent slug like `kim-smith` matching `agents/<slug>.json`. Triggered by "as <slug>" or "for <slug>". Defaults to `_default` (per-listing tier, dual-branded with small "Listing Kit by getoios.com" footer). Monthly-tier white-label profiles deploy under the agent's custom domain with zero OIOS branding.

## Reference templates

Don't regenerate from scratch — clone structure from the most recent working file:

- `C:\Users\default.DESKTOP-ON29PVN\Downloads\116-country-club-lane-paducah-ky.html` — most recent, static-hero version
- `C:\Users\default.DESKTOP-ON29PVN\Downloads\2001-jefferson-street-paducah-ky.html` — original Hyper Agent reference (has the Veo 3.1 video)

Both use Italiana (display) / Cormorant Garamond (serif body) / Inter (sans). Palette: paper `#f5f1ea`, ink `#1f1d1a`, gold `#a07f3f`. Sections in order: topbar → hero → highlights strip → narrative → 2 feature pulls → pull quote → masonry gallery → details (2 cols) → location → inquiry/agent → footer → lightbox.

**Typography rule — Italiana only for large single-word/phrase headings.** Do NOT use Italiana for numerals, stats, or mixed text — it renders numbers inconsistently (italic "2", cursive "0") at body sizes. Correct assignments:
- `.stat-num` → `'Inter', sans-serif; font-weight: 300; letter-spacing: -0.01em` (NOT Italiana, NOT Cormorant — Inter's "1" is unambiguous; Cormorant's "1" looks like capital "I")
- `.narrative .signoff` → `'Cormorant Garamond', serif; font-weight: 500; font-style: italic` (NOT Italiana)
- Italiana is correct for: hero address, narrative h2, section headers, topbar brand, pullquote decorative quotes, footer display text.

## Mobile-first (non-negotiable)

Most recipients open these via text/email on phones. Every page must render correctly at 375×812 (iPhone 13 mini), 414×896 (iPhone 14), and 768×1024 (iPad portrait) — desktop is secondary. The 116/2001 templates already bake the following fixes; preserve them when generating new pages:

**CSS rules (already in template — do not regress):**
- Hero: `height: 100vh; height: 100svh; min-height: 560px;` — `100svh` (small viewport height) prevents iOS chrome overflow; `min-height: 560px` keeps short phones usable.
- Topbar mobile: `@media (max-width: 768px) { .topbar .brand { font-size: 16px; letter-spacing: 0.14em; } .topbar .cta { padding: 9px 14px; font-size: 11px; letter-spacing: 0.14em; } }` — without this the brand wraps to 3 lines on iPhone width.
- Hero address: NEVER use `<br>` inside `.hero-address` — let it wrap naturally. (Old template used `<br>`, which then required hiding via media query but caused word-merge bugs.)
- Feature Strip 2: use `<section class="feature-strip feature-strip--text-first">` with NO inline `style="grid-template-columns:..."`. The `--text-first` modifier handles text-left/image-right on desktop and image-first on mobile via order:-1. Inline grid override breaks the mobile column collapse.
- Form inputs: `font-size: 16px` minimum (anything smaller triggers iOS zoom-on-focus).
- Lightbox: must include prev/next buttons, photo counter, swipe gestures, and arrow-key navigation — see template's lightbox CSS + JS block.

**Topbar shrink-on-scroll JS — breakpoint-aware:**
```js
const tb = document.querySelector('.topbar');
const mq = window.matchMedia('(max-width: 768px)');
const setTbPadding = () => {
  const y = window.scrollY;
  const mobile = mq.matches;
  if (mobile) tb.style.padding = y > 80 ? '10px 22px' : '14px 22px';
  else tb.style.padding = y > 80 ? '12px 48px' : '18px 48px';
};
window.addEventListener('scroll', setTbPadding, { passive: true });
mq.addEventListener('change', setTbPadding);
```
The original Hyper Agent template had a buggy version that always set desktop padding (`12px 48px`/`18px 48px`) regardless of viewport — blew out the mobile padding on every scroll. The breakpoint-aware version above is mandatory.

**Lightbox JS — must include:**
```js
const lbPrev = document.getElementById('lbPrev');
const lbNext = document.getElementById('lbNext');
const lbCount = document.getElementById('lbCount');
const allImgs = [...document.querySelectorAll('.masonry-item img')];
let currentIdx = 0;
const showAt = (i) => {
  currentIdx = (i + allImgs.length) % allImgs.length;
  lbImg.src = allImgs[currentIdx].src;
  lbCount.textContent = `${currentIdx + 1} / ${allImgs.length}`;
};
allImgs.forEach((img, idx) => img.addEventListener('click', () => { showAt(idx); lb.classList.add('open'); }));
document.addEventListener('keydown', e => {
  if (!lb.classList.contains('open')) return;
  if (e.key === 'ArrowLeft') showAt(currentIdx - 1);
  else if (e.key === 'ArrowRight') showAt(currentIdx + 1);
  else if (e.key === 'Escape') lb.classList.remove('open');
});
let touchStartX = 0, touchStartY = 0;
lb.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; touchStartY = e.touches[0].clientY; }, { passive: true });
lb.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - touchStartX;
  const dy = e.changedTouches[0].clientY - touchStartY;
  if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
    if (dx > 0) showAt(currentIdx - 1); else showAt(currentIdx + 1);
  }
}, { passive: true });
```

## Picture polish (mandatory in template)

Zillow caps public photos at 1536px wide (`uncropped_scaled_within_1536_1152.jpg` is the max — `2048` returns 404, `o_a.jpg` is smaller). Resolution upgrade is a dead end. The win is in CSS treatment.

**Apply to all photo-bearing surfaces:**

```css
/* Masonry: lift photos off the paper background, subtle pop, premium hover */
.masonry-item {
  break-inside: avoid;
  margin-bottom: 18px;
  overflow: hidden;
  cursor: pointer;
  background: var(--paper-soft);
  box-shadow: 0 2px 10px rgba(31, 29, 26, 0.07);
  transition: box-shadow 0.4s ease, transform 0.4s ease;
}
.masonry-item img {
  width: 100%;
  display: block;
  transition: transform 0.7s ease, filter 0.4s ease;
  filter: contrast(1.04) saturate(1.06);
}
.masonry-item:hover {
  box-shadow: 0 12px 32px rgba(31, 29, 26, 0.18);
  transform: translateY(-2px);
}
.masonry-item:hover img { transform: scale(1.04); filter: contrast(1.06) saturate(1.10); }

/* Feature pulls: same subtle treatment */
.feature-img {
  background-size: cover;
  background-position: center;
  min-height: 560px;
  filter: contrast(1.04) saturate(1.06);
}

/* Hero: deeper bottom gradient for text legibility against bright photos */
.hero::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(180deg,
    rgba(0,0,0,0.38) 0%,
    rgba(0,0,0,0.12) 38%,
    rgba(0,0,0,0.25) 68%,
    rgba(0,0,0,0.72) 100%);
  pointer-events: none;
}
```

**Why these specific values:**
- `contrast(1.04) saturate(1.06)` is the threshold where photos look richer without looking processed — go higher and skin tones / wood floors get cartoonish
- `box-shadow: 0 2px 10px rgba(31, 29, 26, 0.07)` lifts photos off the paper (`#f5f1ea`) without being visible as a "shadow" — looks like depth, not a drop shadow
- Hover: `0 12px 32px / 0.18` is a meaningful lift, paired with `translateY(-2px)` for the subtle "rising" feel
- Hero gradient bottom `0.72` (was `0.55`) — needed because hero address text + price sit at the bottom over wildly varying photos; this floor of darkness keeps text legible regardless of what's behind it

## Open Graph share preview (mandatory in Step 4)

Every page must render a rich preview when texted/posted. Inject in `<head>` immediately after `<title>`:

```html
<title>{address} — {city}, {state} · ${price}</title>
<meta name="description" content="{first sentence of narrative} {beds}bd · {baths}ba · {sqft} sq ft. Listed at ${price}.">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:url" content="{final deployed URL or empty if local-only}">
<meta property="og:title" content="{address} — {city}, {state} · ${price}">
<meta property="og:description" content="{first sentence of narrative} {beds}bd · {baths}ba · {sqft} sq ft.">
<meta property="og:image" content="{hero photo Zillow CDN URL — full https://photos.zillowstatic.com/... path}">
<meta property="og:image:width" content="1536">
<meta property="og:image:height" content="1152">
<meta property="og:image:alt" content="{address} — front exterior">
<meta property="og:site_name" content="{address}">

<!-- Twitter / X -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{address} — {city}, {state} · ${price}">
<meta name="twitter:description" content="{first sentence of narrative} {beds}bd · {baths}ba · {sqft} sq ft.">
<meta name="twitter:image" content="{same hero photo URL}">
```

If hosting mode = `local`, set `og:url` to empty (preview still works on platforms that derive from page content). If hosting mode = `netlify`, set `og:url` to the eventual `https://<slug>.netlify.app/` URL — write the HTML AFTER the deploy URL is known, OR use a placeholder and patch in Step F before final upload.

**Hero — two modes:**

- **Static (default)**: `<img class="hero-still">` + CSS Ken Burns animation. No audio. Cheap and fast.
  ```css
  .hero img.hero-still {
    position: absolute; inset: 0;
    width: 100%; height: 100%;
    object-fit: cover;
    animation: kenburns 28s ease-in-out infinite alternate;
    transform-origin: 50% 55%;
  }
  @keyframes kenburns {
    0%   { transform: scale(1.00) translate(0, 0); }
    100% { transform: scale(1.08) translate(-1.2%, -1.6%); }
  }
  ```

- **Video (opt-in)**: `<video autoplay muted loop playsinline>` pointing at a 36-second 1080p MP4 generated via FFmpeg Ken Burns + xfade chain + ElevenLabs narration. Full Hyper-Agent-style cinematic intro. See "Video pipeline" section below.
  ```html
  <video id="heroVid" class="hero-video" autoplay muted loop playsinline preload="auto" poster="<hero photo URL>">
    <source src="<slug>-hero.mp4" type="video/mp4">
  </video>
  <button class="hero-mute" id="muteToggle" aria-label="Toggle audio">♪</button>
  ```
  CSS: drop the kenburns keyframes (the video has its own zoom). Mute button styling matches the original Hyper Agent template — see `2001-jefferson-street-paducah-ky.html`.

## Print Kit (Stage 1)

When print-kit mode is on, the skill produces **3 print-ready PDFs** for the binder/leave-behind/mailer use case:

| File | Format | Purpose |
|---|---|---|
| `brochure-8page.pdf` | US Letter (8.5×11), 8 pages | Editorial deep-dive: cover → lede → public spaces → signature feature → private retreat → pull quote → spec sheet → back cover with agent + QR |
| `leave-behind-1sheet.pdf` | US Letter (8.5×11), 2 pages (front+back) | The binder centerpiece: front = hero photo + price + 6 stats + QR + agent block; back = 3-photo strip + spec sheet + 2-col highlights + agent card |
| `postcard-just-listed.pdf` | 6×4.25 (USPS standard) | "Just Listed" mailer: front = hero + price + address; back = 3-photo strip + agent + QR |

**Output location:** `~/Downloads/<slug>-kit/print/` (also writes `qr.png` for debug).

**How to invoke (programmatic — agent runs this after Step 1–4 produce listing data):**

```bash
python ~/.claude/skills/zillow-clone/print/render_pdfs.py \
  --listing /tmp/<slug>-listing.json \
  --agent <agent-slug>           # or omit for default _default
  --slug <slug> \
  --out ~/Downloads/<slug>-kit \
  --base-url https://<slug>.netlify.app   # optional; auto-derived if omitted
```

**Listing JSON shape:** see `print/_listing_example.json` for the canonical schema. Required keys:
- Address: `street_address, city, state, zipcode, full_address`
- Price: `price` (int) — `price_formatted` derived if missing
- Stats: `bedrooms, bathrooms, sqft, lot_size, lot_area_value, lot_area_units, year_built, garage_spaces, mls_id, home_type`
- Photos: `photos[]` (array of URLs — Zillow CDN https:// or local file:// paths to downloaded images). Index 0 = hero. Renderer pulls strip photos from indexes 1/2/3 and brochure spread photos from indexes 0/2/4/6.
- Narrative blocks (optional but recommended for brochure): `lede_headline, lede_paragraph, public_headline, public_paragraph, public_pt_1..4, signature_headline, signature_paragraph, signature_pt_1..4, private_headline, private_paragraph, private_pt_1..3, pullquote_text, description_short`
- Spec rows: `feat_1_label/value` through `feat_6_label/value`, `nb_1_label/value` through `nb_5_label/value`
- One-sheet highlights: `highlight_1` through `highlight_6`

**Brand profile:** loaded from `~/.claude/skills/zillow-clone/agents/<slug>.json`. Schema example in `agents/_example-template.json`. Default profile (`_default.json`) is per-listing tier with dual branding. Brand profile flows everywhere: logo on cover, brand colors via CSS var override (`primary_color`, `accent_color`), agent name + headshot + license, brokerage block, custom domain (monthly tier), per-tier footer tagline.

**Tier behavior:**
- `tier: "per-listing"` — footer shows "Listing Kit by getoios.com" (or whatever's in the profile's `footer_tagline`); QR points at `<slug>-kit.netlify.app`.
- `tier: "monthly"` — full white-label. ZERO OIOS branding. QR + landing page point at `<slug>.<custom_domain>`.

**Files in `print/` directory:**
- `brand_profile.py` — loader + tiny mustache-style template renderer (`{{var}}`, `{{#var}}…{{/var}}`, `{{^var}}…{{/var}}`)
- `render_pdfs.py` — main entry point; handles QR generation, template rendering, Playwright HTML→PDF
- `brochure.html` — 8-page brochure template
- `one-sheet.html` — front+back leave-behind template
- `postcard.html` — 4×6 postcard template
- `_listing_example.json` — sample listing fixture for smoke-testing

**Dependencies (already installed):**
- `playwright` + chromium (HTML→PDF rendering, headless)
- `qrcode[pil]` + Pillow (QR PNG generation)
- Google Fonts loaded over the network at render time (Italiana, Cormorant Garamond, Inter)

**Smoke-test command:**
```bash
python ~/.claude/skills/zillow-clone/print/render_pdfs.py \
  --listing ~/.claude/skills/zillow-clone/print/_listing_example.json \
  --slug smoke-test \
  --out ~/Downloads/_listing-kit-smoketest
```
Should complete in ~15–25s and produce 3 PDFs (~2–5 MB each).

## Steps

### 1. Extract the listing data (the unlock)

Zillow blocks WebFetch / Realtor / Redfin (403). Use Playwright + `__NEXT_DATA__`:

```javascript
// 1a. Navigate
mcp__playwright__browser_navigate({ url: "<zillow URL>" })

// 1b. Save the JSON dump (worktree-relative, sandbox-allowed)
mcp__playwright__browser_evaluate({
  function: "() => document.getElementById('__NEXT_DATA__').textContent",
  filename: "zillow-next-data.json"
})
```

The saved file is **double-encoded JSON**. Parse twice:

```javascript
const fs = require('fs');
const raw = fs.readFileSync('zillow-next-data.json', 'utf8');
const first = JSON.parse(raw);
const data = (typeof first === 'string') ? JSON.parse(first) : first;

const cache = data.props.pageProps.componentProps.gdpClientCache;
const cacheObj = (typeof cache === 'string') ? JSON.parse(cache) : cache;
const property = cacheObj[Object.keys(cacheObj)[0]].property;
```

### 2. Pull from `property`

| Field | Source |
|---|---|
| Address | `streetAddress`, `city`, `state`, `zipcode` |
| Price | `price` |
| Beds / baths / sqft | `bedrooms`, `bathrooms`, `livingAreaValue` |
| Lot | `lotSize` (sqft), `lotAreaValue` (acres), `lotAreaUnits` |
| Description (verbatim) | `description` |
| MLS | `mlsid` |
| Year built / parking / fireplace / floors / appliances / construction / style / taxes | `resoFacts.{yearBuilt, parkingFeatures, garageParkingCapacity, fireplaceFeatures, flooring, appliances, constructionMaterials, architecturalStyle, taxAnnualAmount}` |
| Agent / brokerage / phone / MLS feed | `attributionInfo.{agentName, agentPhoneNumber, brokerName, mlsName}` |
| Photos (ordered, hero = index 0) | `originalPhotos[]` or `responsivePhotos[]` |

### 3. Build photo URLs

```javascript
const photoUrls = property.originalPhotos.map(ph =>
  ph.mixedSources?.jpeg?.find(x => x.width >= 1500)?.url || ph.url
);
// Format: https://photos.zillowstatic.com/fp/<32hex>-uncropped_scaled_within_1536_1152.jpg
```

`photoUrls[0]` = hero. The rest = gallery in order.

### 3.5. Vision-classify photos (quality + intent + label, in one pass)

Zillow ships listings with no captions and often 30-50+ photos of mixed quality. Without per-photo intelligence, feature pulls land on the wrong photo (the "fireplace" pull on a kitchen shot — already happened on 116) AND blurry/closet/clipboard shots end up in the gallery. This step does three jobs in one vision pass: **label**, **quality-score**, and **intent-match to the listing description**.

**Procedure:**

1. Download up to 30 photos from `originalPhotos[]` to `/c/Users/default.DESKTOP-ON29PVN/Downloads/photo-classify/<hash>.jpg`:
   ```bash
   mkdir -p /c/Users/default.DESKTOP-ON29PVN/Downloads/photo-classify
   for hash in <first 30 hashes>; do
     curl -s -o "/c/Users/default.DESKTOP-ON29PVN/Downloads/photo-classify/${hash}.jpg" \
       "https://photos.zillowstatic.com/fp/${hash}-uncropped_scaled_within_1536_1152.jpg"
   done
   ```
   30 is the cap — enough to find the strongest 10-12 from any listing, not so many you blow the vision-call budget. If `originalPhotos[]` has fewer than 30, download all available.

2. Use the `Read` tool with vision on each downloaded JPG. For each photo, return a JSON object (single object per photo, not an array):
   ```json
   {
     "hash": "abc123...",
     "label": "kitchen",
     "secondary_features": ["marble_island", "pendant_lights", "double_oven"],
     "lighting": "golden|warm|harsh|overcast|dim",
     "composition": 8,
     "clutter": 9,
     "sharpness": 9,
     "exposure": 8,
     "subject_centered": true
   }
   ```
   - **`label`** must be one of: `exterior_front, exterior_back, kitchen, living_room, bedroom, primary_bedroom, bathroom, primary_bathroom, dining_room, fireplace, garden, garage, view, pool, deck, basement, foyer, porch, hallway, laundry, office, closet, other`
   - **`secondary_features`** = free-text array of named details the photo prominently shows (used in step 4 for intent-matching to the listing description)
   - **`lighting`** = dominant light quality (`golden`/`warm` get a small bonus during selection)
   - **`composition`** 1-10 = subject centered, framing clean, not crooked
   - **`clutter`** 1-10 = staged (10) → lived-in mess (1)
   - **`sharpness`** 1-10 = no motion blur or focus issues
   - **`exposure`** 1-10 = not blown out, not muddy
   - **`subject_centered`** = is the main subject inside the central 60% of the frame (used later for square/vertical crops)

3. **Quality filter — drop the bad ones.** Keep only photos where `(composition + sharpness + exposure) / 3 >= 7`. Most listings have 5-10 shots that should never have been uploaded — closets, half-open doors, agent-with-clipboard, motion-blur. Drop them.

4. **Parse the listing description for named features.** Scan `property.description` for these intent triggers (build a list per listing — most listings will only hit a handful):
   - **Architectural:** "vaulted ceilings", "exposed beams", "coffered", "wainscoting", "crown molding", "hardwood", "original floors", "fanlight", "transom", "barrel ceiling"
   - **Kitchen:** "marble", "soapstone", "quartz", "granite", "island", "double oven", "wolf", "sub-zero", "pantry", "butler's pantry"
   - **Bath/Suite:** "primary on main", "primary suite", "claw foot", "walk-in shower", "double vanity", "soaking tub"
   - **Outdoor:** "screened porch", "wraparound porch", "covered patio", "pergola", "fire pit", "in-ground pool", "outdoor kitchen", "garden", "raised beds"
   - **View/Setting:** "river view", "lake view", "mountain view", "downtown skyline", "treeline", "private lot"
   - **Specialty:** "wine cellar", "library", "den", "sunroom", "media room", "workshop", "barn", "guest house"

   For each named feature found, run a vision check on every kept photo: `"Does this photo prominently show [feature]? yes|no|partial"` — pick the strongest `yes` match per feature. Cache result in a `feature_match: { <feature>: <hash> }` map.

5. **Build the assignment** (priority is intent → label → score):
   - **Hero** = strongest `exterior_front` (highest `(composition + sharpness + exposure)/3`, with `+1` bonus for `golden` lighting). Fall back to `exterior_back` → highest-scored kept photo overall.
   - **Feature pull #1 (outdoor)** = (a) intent-match if description leads with an outdoor feature, else (b) strongest match in priority `[garden, porch, deck, pool, view, exterior_back]`.
   - **Feature pull #2 (interior)** = (a) intent-match if description names an interior feature ("fireplace", "marble island", "vaulted ceiling", etc), else (b) strongest match in `[fireplace, primary_bedroom, living_room, kitchen]`.
   - **Gallery** = all kept photos (post-quality-filter), interleaved by category so no 4 of the same label appear in a row. Aim 12-20 in gallery.

6. If feature pull #2 image is picked by score (no intent match found), name the hash in the "things to flag" section so Wes can swap.

This step is mandatory. The 116 page initially shipped with the kitchen photo on the fireplace pull because it was picked by index — quality filter + intent matching prevents that AND drops the bad-quality shots that drag the gallery down.

### 4. Compose the HTML

Substitute into the template structure:

- **Topbar brand**: short address ("116 COUNTRY CLUB" → all-caps, drop street type)
- **Hero**: `<img>` = photoUrls[0]. Eyebrow = "A historic <city> <type>". Address split for display. Sub = "<style/era> on a <lot> — Listed at $<price>".
- **Highlights strip (6 stats)**: bedrooms · bathrooms · sqft · acres · year built · garage spaces
- **Narrative** (≤ 4 paragraphs, italic lede, signoff):
  - Voice = literary, em dashes, no realtor clichés ("must see", "won't last", "stunner", "dream home")
  - Lede = paraphrase of the listing's opening, in Wes's voice
  - Body = property's actual features, not generic
  - Signoff = "— <era> · <signature feature> · <signature feature> —"
- **Feature pull #1** (image left, text right): strongest **outdoor** feature (porch / garden / lot / view). 1 paragraph + 6 list items.
- **Feature pull #2** (text left, image right): strongest **interior** feature (fireplace / beams / floors / kitchen). 1 paragraph + 6 list items.
- **Pull quote**: a strong line from `description`, flattened from Title Case to normal sentence. Attribution: "From the listing".
- **Masonry gallery**: every photo, ordered, `loading="lazy"`. Lightbox on click.
- **Details, 2 cols**:
  - Col 1 "Property": list price, type, year built, sqft, lot, beds, baths, garage, days on market, MLS#
  - Col 2 "Recent Updates" IF the description discloses years (e.g. "New roof 2023") — else "Character & Features"
- **Location** (5–7 nearby landmarks):
  - Paducah: Country Club of Paducah, Noble Park, Downtown Paducah, LowerTown Arts District, National Quilt Museum, Riverfront/Floodwall Murals, I-24 Access
  - Other cities: research and pull 5–7 with realistic minute estimates
  - Map embed: `https://www.google.com/maps?q=<address+url+encoded>&z=15&output=embed`
- **Agent card**: agent name, brokerage, phone, MLS#, city
- **Footer**: address · "Listed by <agent> · <brokerage> · MLS <id>" · "© <year> — Marketing presentation"

### 5. Save

`Write` to `C:\Users\default.DESKTOP-ON29PVN\Downloads\<slug>.html`. Slug = address lowercased, hyphenated, with state code (e.g. `116-country-club-lane-paducah-ky.html`).

### 5b. Video pipeline — opt-in only

Skip this entire section if Wes did NOT say "with video" / "with narration" / "with hero video". Static hero is the default.

If video mode requested, run BEFORE Step 6:

#### Required: ElevenLabs API key

- Read from local credentials: `~/.claude/projects/.../memory/reference_access_credentials.md` (key is on the line `ELEVENLABS_API_KEY=...`).
- If missing, ask Wes for the key — do not proceed without it. Do not write the key into the SKILL.md or any committed file.

#### Working directory

```bash
mkdir -p "/c/Users/default.DESKTOP-ON29PVN/Downloads/<slug>-build"
cd "/c/Users/default.DESKTOP-ON29PVN/Downloads/<slug>-build"
```

All FFmpeg work happens here. Final `<slug>-hero.mp4` is copied up to `Downloads/` at the end.

#### Step A — Pick 12 photos for the sequence (story-arc, NOT listing order)

Pull from the **scored, intent-mapped pool from Step 3.5** — NOT raw `originalPhotos[]` order. The reel needs emotional pacing, not listing order. Buyers convert on rooms that matter most, in the order that builds momentum.

**Target sequence (10-12 clips, 7-act story arc):**

1. **Establishing exterior** (1-2 clips) — strongest `exterior_front` (golden-hour preferred). Stop-scroll shot.
2. **Threshold** (1 clip) — `porch` / `foyer` / front-door close-up. The "step inside" beat.
3. **Public spaces** (2-3 clips) — `living_room` → `kitchen` → optional `dining_room`. Conversation order.
4. **Signature feature** (1-2 clips) — whatever the **intent map from Step 3.5** identified as the listing's hero: `fireplace`, river view, vaulted ceiling, marble island, screened porch, etc. The room the description leads with.
5. **Private retreat** (1-2 clips) — `primary_bedroom` then `primary_bathroom`. Skip secondary bedrooms; they're filler in a 36.5s reel.
6. **Lifestyle moment** (1-2 clips) — `garden` / `deck` / `view` / `pool`. Paint the buyer LIVING here, not touring.
7. **Closing exterior** (1 clip) — `exterior_back` or `exterior_front` from a different angle, or drone if available. Bookend the open.

**Selection rules within each act:**
- Sort candidates by combined quality score from Step 3.5: `(composition + sharpness + exposure)/3 + (lighting == "golden" ? 1 : lighting == "warm" ? 0.5 : 0)`. Pick top.
- No 2 consecutive clips with the same `label`. If `primary_bedroom + bedroom` both got picked, separate with a public-space clip.
- If an act has no candidates (no `garden` photo for Lifestyle Moment), substitute next-best from sibling categories OR skip that act entirely (10 clips instead of 12).
- If the kept pool from Step 3.5 has fewer than 10 photos, fall back to all available + extend each clip to 4.0s. Warn Wes that the reel is thin.

**Download the picked 12 in story-arc order:**

```bash
n=1
for hash in <list of 12 hashes IN STORY ORDER>; do
  curl -s -o "p$(printf '%02d' $n).jpg" "https://photos.zillowstatic.com/fp/${hash}-uncropped_scaled_within_1536_1152.jpg"
  n=$((n+1))
done
```

The `pNN.jpg` index is now act-driven (`p01` = establishing exterior, `p12` = closing exterior), NOT listing-order.

Download:

```bash
n=1
for hash in <list of 12 hashes>; do
  curl -s -o "p$(printf '%02d' $n).jpg" "https://photos.zillowstatic.com/fp/${hash}-uncropped_scaled_within_1536_1152.jpg"
  n=$((n+1))
done
```

#### Step B — Generate narration script

Write a 75-85 word script tuned for ~35s at ElevenLabs Lily's slow pace (~140wpm). Voice rules:
- Literary, em dashes, no realtor clichés
- 3-4 short sentences, structured: location → era → interior → exterior → close
- End with "Listed at <flat price>" — say "four ninety-nine" not "four hundred ninety-nine thousand nine hundred"

Sample (116 Country Club, ~78 words, ~33s):

```
Tucked into the desirable West End of Paducah — a cottage from 1913. Three owners across more than a century. Hardwood floors, exposed wooden beams, a fireplace that means it. Outside, a well-tended English garden, mature and private — the kind of yard that takes a hundred years to settle into a place. A screened porch wraps around it. Four bedrooms, three baths, on just under an acre. 116 Country Club Lane. Listed at four ninety-nine.
```

Save to `script.txt`.

#### Step C — Generate narration MP3 via ElevenLabs

Default voice: **George — Warm Captivating Storyteller** (`JBFqnCBsd6RMkjVDRZzb`). Premade voice, male, warm and calm. Free tier compatible — confirmed working 2026-04-30.

**⚠️ Adeline (`5l5f8iK3YPeGga21rQIX`) requires a paid ElevenLabs plan.** Returns HTTP 402 "Free users cannot use library voices via the API" on free tier. Do not attempt unless account is on Starter or higher.

Other premade voices (free tier compatible — verify via `GET /v1/voices`):
- **George — Warm Storyteller** (`JBFqnCBsd6RMkjVDRZzb`) — male, calm ← DEFAULT
- **Sarah** (`EXAVITQu4vr4xnSDxMaL`) — female, mature, reassuring
- **Laura** (`FGY2WhTYpPnrIDTdsKH5`) — female, enthusiastic

Model: `eleven_turbo_v2_5` (free-tier compatible — `eleven_multilingual_v2` returns 403 on free tier).

```python
import urllib.request, json, os
api_key = os.environ['ELEVENLABS_API_KEY']  # Or read from credentials file
voice_id = 'pFZP5JQG7iQjIQuC4Bku'
script = open('script.txt').read().strip()
body = json.dumps({
  "text": script,
  "model_id": "eleven_turbo_v2_5",
  "voice_settings": {
    "stability": 0.5, "similarity_boost": 0.75,
    "style": 0.4, "use_speaker_boost": True
  }
}).encode()
req = urllib.request.Request(
  f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
  data=body,
  headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
  method="POST"
)
with urllib.request.urlopen(req, timeout=60) as r:
  open('narration.mp3', 'wb').write(r.read())
```

Verify with `ffprobe -v error -show_entries format=duration narration.mp3` — expect 30-36s.

#### Step D — Render 12 Ken Burns clips × 3 aspect ratios

Each clip: 3.5s, 24fps, slow zoom from 1.00 → 1.06. Three aspect outputs in a single FFmpeg invocation per clip (one decode, three encodes — the `split` filter shares the input):

- **16:9** (1920×1080) → `c${i}.mp4` — landing-page hero
- **1:1** (1080×1080) → `c${i}-sq.mp4` — Facebook feed default
- **9:16** (1080×1920) → `c${i}-vt.mp4` — Reels / Stories

Critical params (unchanged from previous version):
- `-loop 1 -framerate 24 -t 3.5 -i pXX.jpg` — input is the still, looped at exactly 24fps for 3.5s
- `zoompan=z='1.0+0.06*on/84':d=1:fps=24` — `d=1` is the trick. Without it, zoompan outputs 84 frames per input frame and clips run 308s.
- `-t 3.5` AGAIN on each output to clamp duration
- Pre-scale 1.33× the final dimensions per aspect, then crop, so zoompan has room to zoom into without showing image edges

```bash
for i in $(seq -f "%02g" 1 12); do
  ffmpeg -y -loop 1 -framerate 24 -t 3.5 -i "p${i}.jpg" \
    -filter_complex "
      [0:v]split=3[s1][s2][s3];
      [s1]scale=2048:1152:force_original_aspect_ratio=increase:flags=lanczos,crop=2048:1152,zoompan=z='1.0+0.06*on/84':d=1:s=1920x1080:fps=24,eq=contrast=1.05:saturation=1.08,unsharp=5:5:0.6:5:5:0.0[v1];
      [s2]scale=1440:1440:force_original_aspect_ratio=increase:flags=lanczos,crop=1440:1440,zoompan=z='1.0+0.06*on/84':d=1:s=1080x1080:fps=24,eq=contrast=1.05:saturation=1.08,unsharp=5:5:0.6:5:5:0.0[v2];
      [s3]scale=1440:2560:force_original_aspect_ratio=increase:flags=lanczos,crop=1440:2560,zoompan=z='1.0+0.06*on/84':d=1:s=1080x1920:fps=24,eq=contrast=1.05:saturation=1.08,unsharp=5:5:0.6:5:5:0.0[v3]
    " \
    -map "[v1]" -t 3.5 -c:v libx264 -pix_fmt yuv420p -r 24 -preset slow -crf 18 "c${i}.mp4" \
    -map "[v2]" -t 3.5 -c:v libx264 -pix_fmt yuv420p -r 24 -preset slow -crf 18 "c${i}-sq.mp4" \
    -map "[v3]" -t 3.5 -c:v libx264 -pix_fmt yuv420p -r 24 -preset slow -crf 18 "c${i}-vt.mp4"
done
```

**Why these specific values (don't drift them):**
- `scale=...:flags=lanczos` — Zillow caps at 1536 wide. Pre-scaling 1.33× the final dimensions per aspect gives zoompan room to zoom in without showing edges. `lanczos` is the sharpest filter; `bilinear` (default) creates softness.
- `zoompan z='1.0+0.06*on/84'` — zoom from 1.00 to 1.06 over 84 frames (3.5s × 24fps). Keep the range small (0.06, NOT 0.10): bigger zoom magnifies compression artifacts and softens the image.
- `eq=contrast=1.05:saturation=1.08` — bake the same color treatment into the video that the gallery CSS applies to stills, for consistency. Don't go higher; wood floors and skin tones get cartoonish past these values.
- `unsharp=5:5:0.6` — gentle 5×5 sharpening kernel at 0.6 amount. Compensates for the residual upscale softness.
- `-preset slow -crf 18` — `slow` preset is 2-3× slower to encode but produces visibly cleaner output at the same bitrate. CRF 18 is a noticeable jump from CRF 22 (the previous default) — file size goes up ~50% but quality is visibly sharper.
- `split=3` — one decode, three encodes: avoids reading the JPG three times. The 1:1 and 9:16 encodes are faster than 16:9 because they're smaller pixel counts.

**Crop behavior per aspect:**
- **1:1** crops 240px from left + right of the source after upscaling — the central 60% of the photo becomes the square frame. Step 3.5's `subject_centered=true` photos survive cleanly; `false` photos may need manual review.
- **9:16** crops ~990px from left + right after upscaling — only the central ~30% survives. Subject MUST be centered for vertical to work. If `subject_centered=false`, prefer that photo only for 16:9 cuts.

Run in background — takes ~7-9 minutes for 12 clips × 3 aspects. Verify with `ffprobe` — each clip should be 3.5s; 16:9 ≈ 6-8MB, 1:1 ≈ 3-4MB, 9:16 ≈ 3-4MB.

#### Step E — xfade chain + audio mix + burn-in captions (3 aspect ratios)

xfade math is unchanged: total = N × clip_dur − (N−1) × fade_dur = 12 × 3.5 − 11 × 0.5 = 36.5s.

Each xfade offset = `i × (clip_dur − fade_dur)` = `i × 3.0` for clip pairs (0,1), (1,2), ..., (10,11).

**Music bed:** A royalty-free Pixabay piano track is cached at `~/.claude/skills/zillow-clone/assets/music-bed-piano.mp3` (256kbps stereo, ~2:30 long). Mix at 18% volume under narration with fade-in 0–1.5s and fade-out 34.5–36.5s for a clean cinematic feel.

**Three aspect ratios in this step.** The xfade chain is identical except for which clip files we read from (suffix `-sq`, `-vt`, or none for 16:9). No burned-in captions — the HTML overlay on the landing page and the Facebook post caption handle all messaging.

Use the Python assembly script pattern (avoids bash escaping issues on Windows). Example `assemble.py`:

```python
import subprocess, os, sys

BUILD = r"C:\Users\default.DESKTOP-ON29PVN\Downloads\<slug>-build"
MUSIC = r"C\:/Users/default.DESKTOP-ON29PVN/.claude/skills/zillow-clone/assets/music-bed-piano.mp3"
NARR = os.path.join(BUILD, "narration.mp3")
N = 12; CLIP_DUR = 3.5; FADE_DUR = 0.5; TOTAL = N * CLIP_DUR - (N-1) * FADE_DUR  # 36.5s

def build_xfade():
    parts = ["[0:v][1:v]xfade=transition=fade:duration=0.5:offset=3.0[vx1]"]
    for i in range(2, N):
        off = i * (CLIP_DUR - FADE_DUR)
        parts.append(f"[vx{i-1}][{i}:v]xfade=transition=fade:duration={FADE_DUR}:offset={off}[vx{i}]")
    return ";".join(parts)

VARIANTS = [("", "hero.mp4"), ("-sq", "hero-sq.mp4"), ("-vt", "hero-vt.mp4")]

for suffix, outname in VARIANTS:
    inputs = []
    for i in range(1, N+1):
        inputs += ["-i", os.path.join(BUILD, f"c{i:02d}{suffix}.mp4")]
    inputs += ["-i", NARR, "-i", MUSIC]
    xfade = build_xfade()
    audio = (f"[{N}:a]apad,atrim=0:{TOTAL},asetpts=PTS-STARTPTS,volume=1.0[narr];"
             f"[{N+1}:a]volume=0.18,atrim=0:{TOTAL},afade=t=in:st=0:d=1.5,afade=t=out:st=34.5:d=2.0[mus];"
             f"[narr][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    fc = f"{xfade};[vx{N-1}]copy[vfinal];{audio}"
    cmd = (["ffmpeg", "-y"] + inputs +
           ["-filter_complex", fc, "-map", "[vfinal]", "-map", "[a]",
            "-t", str(TOTAL), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "slow", "-crf", "19", "-r", "24",
            "-maxrate", "6500k", "-bufsize", "13000k",
            "-c:a", "aac", "-b:a", "192k", os.path.join(BUILD, outname)])
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"{'OK' if r.returncode == 0 else 'FAILED'}: {outname}")
```

**Note on MUSIC path:** Escape the Windows drive letter colon: `C\:/Users/...` — FFmpeg's filter option parser treats `:` as a delimiter. This only matters inside filter_complex strings, but the Python approach passes it as a `-i` argument so it's fine unescaped there. Only matters if you ever use `amovie=` or similar inline.

```bash
# Legacy bash reference (xfade chain only, no captions):
for variant in "::hero.mp4" "-sq:hero-sq.mp4" "-vt:hero-vt.mp4"; do
  IFS=':' read -r suffix out <<< "$variant"
  ffmpeg -y \
    -i "c01${suffix}.mp4" -i "c02${suffix}.mp4" -i "c03${suffix}.mp4" -i "c04${suffix}.mp4" \
    -i "c05${suffix}.mp4" -i "c06${suffix}.mp4" -i "c07${suffix}.mp4" -i "c08${suffix}.mp4" \
    -i "c09${suffix}.mp4" -i "c10${suffix}.mp4" -i "c11${suffix}.mp4" -i "c12${suffix}.mp4" \
    -i narration.mp3 \
    -i "$MUSIC" \
    -filter_complex "$(build_xfade);[vx11]copy[vfinal];[12:a]apad,atrim=0:36.5,asetpts=PTS-STARTPTS,volume=1.0[narr];[13:a]volume=0.18,atrim=0:36.5,afade=t=in:st=0:d=1.5,afade=t=out:st=34.5:d=2.0[mus];[narr][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]" \
    -map "[vfinal]" -map "[a]" \
    -t 36.5 \
    -c:v libx264 -pix_fmt yuv420p -preset slow -crf 19 -r 24 -maxrate 6500k -bufsize 13000k \
    -c:a aac -b:a 192k \
    "$out"
done
```

Outputs:
- `hero.mp4` (16:9, 1920×1080, ~26MB, 5.6 Mbps) — landing page
- `hero-sq.mp4` (1:1, 1080×1080, ~14MB, 3.0 Mbps) — Facebook feed default
- `hero-vt.mp4` (9:16, 1080×1920, ~14MB, 3.0 Mbps) — Reels / Stories

Critical: `amix=...:normalize=0` — without `normalize=0`, FFmpeg auto-divides by N=2 inputs and you lose half your narration volume. `apad` extends narration with silence to cover the full 36.5s; `atrim` clamps to exactly 36.5s.

Total render time: ~6-9 minutes for all three variants (1:1 and 9:16 encode faster because they're smaller pixel counts than 16:9).

**If re-mixing music or re-applying captions to an existing hero MP4** (audio swap or caption swap only — no re-render):

```bash
# Audio swap (music bed only, no caption change):
ffmpeg -y -i hero.mp4 -i "$MUSIC" \
  -filter_complex "[0:a]volume=1.0[narr];[1:a]volume=0.18,atrim=0:36.5,afade=t=in:st=0:d=1.5,afade=t=out:st=34.5:d=2.0[mus];[narr][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -t 36.5 hero-with-music.mp4

# Caption swap (re-encodes video — captions are baked into pixels, can't be -c:v copy):
CAPTIONS=$(build_drawtext 42 "h-180")
ffmpeg -y -i hero.mp4 -vf "$CAPTIONS" -c:v libx264 -preset slow -crf 19 -c:a copy hero-captioned.mp4
```

**Common bugs to avoid:**
- xfade offset bug: using `clip_dur + (i-1) × (clip_dur − fade_dur)` collapses the chain. Correct formula is `i × (clip_dur − fade_dur)`.
- zoompan `d=84` (instead of `d=1`) makes clips 88× too long.
- Forgetting `-t 36.5` on output → audio padding runs forever.
- Drawtext `enable` clause: comma in `between(t,X,Y)` must be escaped as `\,` inside filter_complex string. The `build_drawtext` function above handles it.
- Apostrophes in phrase text: `'` must become `'\''` for drawtext to parse. Use the bash substitution shown above, OR avoid apostrophes in the phrase array (rewrite "Paducah's" → "Paducah" if escaping breaks).

#### Step F — Move to Downloads + update HTML

```bash
cp hero.mp4 "/c/Users/default.DESKTOP-ON29PVN/Downloads/<slug>-hero.mp4"
```

Then update the HTML hero section:
- Replace `<img class="hero-still" src="..." alt="...">` with the `<video>` block (see Hero asset substitutions section above)
- Add the `.hero-mute` button styles in CSS
- Replace the Ken Burns CSS rule with `.hero video.hero-video { ...object-fit: cover... }` (no animation — video has its own zoom)
- Add the mute toggle JS at the top of the existing `<script>` block

Source of truth for the HTML wiring: `116-country-club-lane-paducah-ky.html` (the recent video version).

### 5c. Auto-deploy to Netlify — opt-in only

Skip this entire section if Wes did NOT say "and host it" / "and deploy it" / "and put it online". Default is local-only.

If hosting requested, run BEFORE Step 6:

#### Required: Netlify Personal Access Token

- Read from local credentials: `~/.claude/projects/.../memory/reference_access_credentials.md` (key is on the line `NETLIFY_API_TOKEN=nfp_...` — but stored as the bullet "Netlify (Personal Access Token)").
- If missing, send Wes to https://app.netlify.com/user/applications#personal-access-tokens to generate one. Token must start with `nfp_`.

#### Step A — Build deploy folder

Netlify needs `index.html` (not `<slug>.html`) for the URL to be `https://<sitename>.netlify.app/` instead of `https://<sitename>.netlify.app/<slug>.html`. Build a clean folder with renamed files:

```bash
DEPLOY_DIR="/c/Users/default.DESKTOP-ON29PVN/Downloads/<slug>-listing-page"
mkdir -p "$DEPLOY_DIR"
cp "/c/Users/default.DESKTOP-ON29PVN/Downloads/<slug>.html" "$DEPLOY_DIR/index.html"
# If video mode is on:
cp "/c/Users/default.DESKTOP-ON29PVN/Downloads/<slug>-hero.mp4" "$DEPLOY_DIR/<slug>-hero.mp4"
```

The HTML's `<source src="<slug>-hero.mp4">` is a relative path — Netlify resolves it correctly because both files sit at the deploy root.

#### Step B — Zip the folder

`/tmp/` doesn't reliably exist on Windows git-bash. Use an absolute Windows path under Downloads:

```bash
cd "$DEPLOY_DIR"
python -c "
import zipfile, os
zip_path = 'C:/Users/default.DESKTOP-ON29PVN/Downloads/<slug>-site.zip'
if os.path.exists(zip_path): os.remove(zip_path)
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
  for f in os.listdir('.'):
    if os.path.isfile(f):
      z.write(f, f)
"
```

#### Step C — Create the Netlify site

Site name = address slug (same one used for the HTML filename, e.g. `116-country-club-lane-paducah-ky`). Site names are globally unique on Netlify — if taken, fall back to `<slug>-<random4>`.

```bash
SITE_RESP=$(curl -s -X POST "https://api.netlify.com/api/v1/sites" \
  -H "Authorization: Bearer $NETLIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"<slug>\"}")
SITE_ID=$(echo "$SITE_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('id'))")
SITE_URL=$(echo "$SITE_RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('ssl_url'))")
```

If `SITE_ID` is `None`, the name was taken — retry with a `-<random4>` suffix.

#### Step D — Deploy the zip

`Bash` shell redirection of curl output to absolute Windows paths is flaky — capture the response inline via `RESP=$(curl ...)`. Do NOT use `> /c/...` for curl output.

```bash
RESP=$(curl -s -X POST "https://api.netlify.com/api/v1/sites/$SITE_ID/deploys" \
  -H "Authorization: Bearer $NETLIFY_TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary "@C:/Users/default.DESKTOP-ON29PVN/Downloads/<slug>-site.zip")
DEPLOY_ID=$(echo "$RESP" | python -c "import json,sys; print(json.load(sys.stdin).get('id'))")
```

#### Step E — Poll until state=ready

```bash
until STATUS=$(curl -s "https://api.netlify.com/api/v1/sites/$SITE_ID/deploys/$DEPLOY_ID" \
  -H "Authorization: Bearer $NETLIFY_TOKEN" | python -c "import json,sys; print(json.load(sys.stdin).get('state'))"); \
  [ "$STATUS" = "ready" ]; do
  sleep 3
done
```

Typical time: 5-15 seconds. Possible states along the way: `uploading`, `uploaded`, `processing`, `prepared`, `ready`. If stuck on `error` after 30s, check `error_message` in the deploy object.

#### Step F — Verify

```bash
curl -s -o /dev/null -w "Site: %{http_code}\n" "$SITE_URL"
curl -s -o /dev/null -w "Video: %{http_code}, %{size_download}B\n" "$SITE_URL/<slug>-hero.mp4"  # if video mode
```

Both must return 200.

**Common bugs to avoid:**
- Forgetting to rename HTML to `index.html` → URL becomes `https://x.netlify.app/<slug>.html` (ugly, recipient must paste full path)
- Putting the zip in `/tmp/` on Windows git-bash → file is created somewhere unfindable
- Using `>` redirection for curl response with absolute Windows path → empty file
- Site name with capitals or underscores → Netlify rejects (lowercase + hyphens only)
- Editing the HTML's `<source src="">` to absolute file path → breaks on Netlify

### 6. Verify (mandatory — desktop AND mobile)

```bash
# 6a. Local server in Downloads
cd "/c/Users/default.DESKTOP-ON29PVN/Downloads" && python -m http.server 8765 --bind 127.0.0.1 > /tmp/zclone.log 2>&1 &
```

Then in Playwright:
1. `browser_navigate` → `http://127.0.0.1:8765/<filename>`
2. **Desktop pass:** `browser_resize` 1440×900
3. `browser_evaluate` to confirm hero loaded:
   - **Static mode**: check `document.querySelector('.hero-still')?.complete && naturalWidth > 0`
   - **Video mode**: check `document.getElementById('heroVid')` for `readyState === 4`, `paused === false`, `duration ≈ 36.5`, `videoWidth === 1920`. Also confirm mute button is visible (`muteBtnVisible: true`).
4. Force gallery lazy → eager, wait 2s, re-evaluate to confirm `loaded === total`, `broken === 0`.
5. `browser_take_screenshot` of hero, gallery, location.
6. **Mobile pass:** `browser_resize` 375×812. Then `browser_evaluate` to verify:
   - `getComputedStyle(document.querySelector('.topbar')).padding` is `14px 22px` (not `48px` sides)
   - `getComputedStyle(document.querySelector('.form-card input')).fontSize` is `16px` (not 15px — iOS zoom kill)
   - `getComputedStyle(document.querySelectorAll('.feature-strip-inner')[1]).gridTemplateColumns` shows ONE column at this width (not the inline `1fr 1.2fr` override)
   - `!!document.getElementById('lbPrev')` and `!!document.getElementById('lbNext')` are both `true`
   - `document.documentElement.scrollWidth - document.documentElement.clientWidth === 0` (no horizontal scroll)
7. Scroll trigger: `window.scrollTo(0, 200)` then re-check topbar padding stays `10px 22px` or `14px 22px` (NOT `12px 48px` — that's the desktop bug).
8. `browser_take_screenshot` of mobile hero, mobile feature strip 2 (must show full-width image, not 76px sliver), mobile inquiry form.
9. **Tablet pass:** `browser_resize` 768×1024 → screenshot.
10. `browser_close`, kill the python server, `start ""` the file in default browser.

**Mobile audit fail conditions (must fix before reporting done):**
- Topbar padding `12px 48px` after scroll on 375 viewport → topbar JS not breakpoint-aware
- Feature Strip 2 image width < 200px on 375 viewport → inline `style="grid-template-columns:..."` not removed
- Form input font-size < 16px → iOS will zoom on focus
- Hero address shows merged words like "ClubLane" → `<br>` was hidden but no space replaced it; remove the `<br>` from source instead
- Lightbox prev/next buttons missing → mobile users can't navigate gallery

### 7. Facebook caption (mandatory when video mode is on OR hosting mode is `netlify`)

Listings get distributed mostly on Facebook. Default the post-caption work to the skill, not Wes hand-writing it. Apply the OIOS Facebook Photo-Post Caption Playbook (queryable via LightRAG: `query_text("Facebook caption playbook anti-AI-slop")`).

Output goes into the chat alongside the MP4 path(s) so Wes copy-pastes when posting.

**Banned vocab — auto-reject in the prompt that drafts the caption:**
- Em-dashes (use periods, hyphens, or line breaks instead)
- "nestled / stunning / exquisite / must-see / hidden gem / dream home / boasts / true gem / entertainer's dream"
- "Just listed!" / "Exciting news" / "Happy Monday" / "We are thrilled" / generic broadcast openers
- Press-release vocabulary: "however / moreover / furthermore / in conclusion / ultimately"
- Hashtag stacks of 5+
- More than 1 exclamation per 150 chars (3+ is a hard kill)
- Three-part rhetorical lists with colons ("You need X. You want Y. You deserve Z.")

**Required human-voice markers:**
- Semicolons (read HUMAN in 2026, inverted from 2022 norms)
- Oddly specific numbers ($580,000 not "around $580K"; "thirty-four years" not "decades")
- Regional / local vocabulary (city or neighborhood by name)
- Sensory detail (light, sound, smell, texture)
- Fragments and incomplete thoughts (real people don't write in complete sentences)
- 1-3 local / niche hashtags at end (NOT 5+, NOT generic #realestate)

**Pattern selection — pick ONE based on the listing's strongest single fact:**

| Strongest fact | Pattern | Example skeleton |
|---|---|---|
| Long ownership (>20 years) | **Local proof** | "Lived in by the same family for thirty-four years; the screened porch still works." |
| Quirky owner detail / prep-day moment | **Open loop** | "The owner left a note in the kitchen drawer. We found it during prep day. Couldn't have written a better tagline if we tried." |
| Lifestyle-driven (porch, view, garden) | **Scene-in-progress** | "Walked the property at 7am. South-facing kitchen catches the morning light by 7:12. Coffee belongs here." |
| Surprising stat (price/sqft, year built, days) | **Specific stat** | "$179 a square foot in Paducah's West End. Built in 1913. Three owners since." |

**Length zones:**
- Short punchy: ≤ 100 characters (best for visual-driven posts where the photo or video does the work)
- Medium-long: 350-600 characters (only when the hook earns the See More)
- AVOID 100-350 dead zone — middle posts get neither short-attention nor expand-curiosity engagement

**First-line scroll-stop test:** the first 90-125 characters truncate before "See more" on mobile. If the first line doesn't earn the click, regenerate.

**Screening checklist before delivering (8 questions, all must pass):**
1. Zero em-dashes? ✓
2. Zero banned-vocab words? ✓
3. ≤ 1 exclamation per 150 chars? ✓
4. ≥ 1 oddly-specific number OR sensory detail? ✓
5. Length zone is ≤ 100 OR 350-600 (not the dead zone)? ✓
6. First line passes the scroll-stop test? ✓
7. Pattern matches listing's strongest fact (local proof / open loop / scene-in-progress / specific stat)? ✓
8. Hashtags ≤ 3, local / niche only? ✓

**First-comment CTA** (separate line — Facebook playbook says drop the URL in the first comment, not the post):

```
Full virtual tour and photos: <deployed URL or .netlify.app fallback>
```

This keeps the caption clean and doesn't trigger Facebook's link-demotion algorithm.

### 8. Report

In chat:
- Markdown link to the file
- Markdown link(s) to MP4(s) if video mode (16:9, 1:1, 9:16)
- One-paragraph verification summary: hero loaded ✓, gallery N/N loaded ✓, mobile ✓, agent + map ✓
- Facebook caption block (if Step 7 ran)
- "Things to flag" section — only if anything was inferred (see Hard rules)

## Output shape

```
File: [<slug>.html](Downloads/<slug>.html)
Live URL (if hosted): https://<slug>.netlify.app
Hero MP4 (if video mode):
  - 16:9 [<slug>-hero.mp4](Downloads/<slug>-hero.mp4)
  - 1:1  [<slug>-hero-sq.mp4](Downloads/<slug>-hero-sq.mp4)
  - 9:16 [<slug>-hero-vt.mp4](Downloads/<slug>-hero-vt.mp4)

Verification:
- Hero: 1536×<h>, loaded (or video: 1920×1080, 36.5s, captions ✓, autoplay, mute btn ✓)
- Gallery: <N>/<N> photos, 0 broken (kept <kept>/<total> after Step 3.5 quality filter)
- Mobile (375×812): layout holds
- Agent: <name> / <brokerage> / <phone>
- Map pin: <address>
- Live site: HTTP 200, hero video HTTP 200 (if hosted)

== Facebook caption (post body) ==
<caption text — pattern: <local-proof|open-loop|scene-in-progress|specific-stat>>

== First comment (URL drop) ==
Full virtual tour and photos: <URL>

Things to flag (only if applicable):
- <feature pull #2 image is index N — swap hash if mismatch>
- <no update years disclosed → used Character & Features column>
- <kept <kept>/<total> photos after quality filter — gallery may look thin if kept < 10>
- <Netlify name collision → deployed under <slug>-<rand> instead>
```

## Hard rules

- **Mobile-first is non-negotiable.** Most recipients open these via text/email on phones. Every page must pass the Step 6 mobile audit (no horizontal scroll, topbar padding correct, form inputs ≥ 16px, feature strip 2 full-width, lightbox prev/next + swipe present). The 116/2001 templates already bake the fixes; preserve them.
- **OG meta tags are mandatory.** Every page must include `og:title`, `og:description`, `og:image`, `og:image:width/height`, `og:url`, `twitter:card=summary_large_image`. Without these, the URL renders as plain text in iMessage / LinkedIn / WhatsApp instead of a rich preview card.
- **Vision-classify, quality-score, AND intent-map photos before assigning feature pulls.** Step 3.5 returns JSON per photo (label + composition/sharpness/exposure scores + secondary_features). Drop photos averaging <7. Match named features in the listing description to actual photos. Skipping classification ships pages with the kitchen photo on the fireplace pull (already happened on 116). Skipping the quality filter ships gallery sections full of blurry hallway shots and half-open closets.
- **Video output is THREE aspect ratios when video mode is on.** 16:9 (`<slug>-hero.mp4`, landing page), 1:1 (`<slug>-hero-sq.mp4`, Facebook feed), 9:16 (`<slug>-hero-vt.mp4`, Reels/Stories). Single 16:9 letterboxes to ~60% screen real estate on Facebook feed and is dead-on-arrival for muted-default scrolling. Step 5b/D and 5b/E handle this.
- **Facebook caption is auto-generated, not hand-written.** When video mode OR Netlify hosting is on, Step 7 returns a playbook-screened Facebook caption block (post body + first-comment URL) alongside the MP4. Apply the OIOS Facebook Photo-Post Caption Playbook: banned vocab list, required human-voice markers, pattern selection (local proof / open loop / scene-in-progress / specific stat), length zones (≤100 OR 350-600), 8-question screening checklist. All 8 must pass before delivery.
- **Never fabricate update years.** If the listing description doesn't say "new roof 2023" or similar, the right-hand details column is "Character & Features", not "Recent Updates". No invented dates, no invented HVAC ages.
- **Never invent agent contact info.** If `attributionInfo` is missing a field, leave it blank or omit the row. Don't guess phone numbers.
- **Don't fabricate captions.** Zillow photos arrive without captions. If you assign a photo to a feature pull and the index is a guess, name the hash in the "things to flag" section so Wes can swap.
- **Single self-contained file.** No CSS files, no JS modules, no asset folder. Inline everything. The page must work opened from a `file://` URL with no build step.
- **Hero defaults to static.** Only build the video when Wes asks ("with video", "with narration", etc.). Video adds 2-3 minutes of build time + ElevenLabs API spend. Hyper Agent's "video" is FFmpeg-stitched photo Ken Burns + narration + music — NOT Veo (proven by Lavf61 encoder tag in the reference file).
- **Don't commit or push.** Wes reviews the file and ships manually. This skill produces a deliverable, not a deploy.
- **Don't write to memory unless something genuinely surprising surfaces.** This is a routine pipeline now; only memory-write if Zillow's data shape changes or the extraction pattern breaks.
- **Photos < 10 → warn before generating.** A thin gallery looks worse than no gallery.
- **Print kit, when on, produces ALL THREE PDFs — never just one.** `brochure-8page.pdf` + `leave-behind-1sheet.pdf` + `postcard-just-listed.pdf`, in `~/Downloads/<slug>-kit/print/`. The kit is a unit; partial deliveries break the agent's binder/leave-behind/mailer workflow.
- **Brand profile is the source of truth for white-label.** Logo, colors, agent contact, brokerage block, custom domain, footer tagline — all flow from `agents/<slug>.json` via `brand_profile.py`. Never hardcode an agent's name/colors into a template. Templates use `{{var}}` substitution only.
- **Per-listing tier always carries a small `getoios.com` footer line; monthly tier carries ZERO OIOS branding.** The `tier` field in the brand profile gates this. When `tier: "monthly"`, all OIOS-attribution surfaces (footer tagline, share preview title prefix, kit dashboard "powered by" line) must be empty/blank — or the white-label promise to the agent breaks.
- **QR codes always point at the live deployed URL.** When `tier: "monthly"`, target the agent's `<slug>.<custom_domain>`. Otherwise target `<slug>-kit.netlify.app` (or `<slug>.netlify.app` if hosting mode is on but kit isn't). Never QR a `file://` or local path — those don't resolve when scanned.
- **Print fonts are the same as the landing page** — Italiana (display headlines/address only), Cormorant Garamond (body), Inter (numerals + uppercase eyebrows). Same typography rule applies in print: Italiana NEVER for stat numbers (use Inter weight 300); Cormorant italic for signoffs.

## Things to flag, never fabricate

- No update years in description → "Character & Features" column, not "Recent Updates"
- Feature-pull image picked by index (no Zillow captions) → name the hash for easy swap
- City unknown → research landmarks before populating location list, don't generic them
- Lot size in sqft only (no acres) → show sqft, drop the acres stat from the highlights strip
- Agent phone missing from `attributionInfo` → omit the phone row, don't fill in `(000) 000-0000`

## Acceptance criteria

- Pipeline runs end-to-end in a single turn from a fresh Zillow URL
- Hero, all photos, agent, address, price match the listing exactly
- Verification screenshots prove desktop + mobile render
- File opens in default browser without errors
- "Things to flag" section is honest about anything inferred
