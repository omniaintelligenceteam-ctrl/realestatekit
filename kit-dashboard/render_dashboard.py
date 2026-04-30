"""
Listing Kit Master Orchestrator — runs every renderer (print + social + email),
writes deterministic copy placeholders (captions / talking points / SMS / schedule),
fills the Kit Dashboard index.html, and reports completion.

This is the single command Wes/agent runs after Step 1 (Zillow extraction) produces a
listing.json. Outputs a complete `<slug>-kit/` directory ready for Netlify deploy:

  <out>/
    index.html                    ← Kit Dashboard (open this in a browser)
    print/                        ← brochure / one-sheet / postcard PDFs
    social/                       ← 4 social images + caption .txt files
    email/                        ← email-blast.html, .txt, subject lines, preview text
    extras/                       ← talking points, social schedule, sphere SMS
    photos/                       ← (caller drops a selected-pack.zip here)
    video/                        ← (caller drops hero.mp4 / hero-sq.mp4 / hero-vt.mp4 here)

Caption / talking-points / SMS placeholder files are written with the listing data
already filled in (deterministic best-guess) — the agent at runtime can replace any
of them with Claude-generated brand-voice copy by editing the .txt file in place.

Usage:
    python render_dashboard.py \
      --listing path/to/listing.json \
      --agent kim-smith \
      --slug 148-pheasant-run-paducah-ky \
      --out C:/Users/.../Downloads/148-pheasant-run-paducah-ky-kit/
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "print"))
from brand_profile import load_brand_profile, render_template  # noqa: E402

DASHBOARD_TEMPLATE = Path(__file__).resolve().parent / "index.html"

PRINT_RENDERER = SKILL_ROOT / "print" / "render_pdfs.py"
SOCIAL_RENDERER = SKILL_ROOT / "social" / "render_social_images.py"
EMAIL_RENDERER = SKILL_ROOT / "email" / "render_email.py"


def fmt_price(p):
    if p is None:
        return ""
    try:
        return f"${int(p):,}"
    except (TypeError, ValueError):
        return str(p)


def short_brand_or(brand: dict) -> str:
    return brand.get("brokerage") or brand.get("agent_name") or "LISTING KIT"


def derive_listing_url(slug: str, brand: dict) -> str:
    if brand.get("is_white_label") and brand.get("custom_domain"):
        return f"https://{slug}.{brand['custom_domain']}"
    return f"https://{slug}-kit.netlify.app"


def coerce(raw: dict, brand: dict, listing_url: str) -> dict:
    photos = raw.get("photos", []) or []
    return {
        "street_address": raw.get("street_address", ""),
        "city": raw.get("city", ""),
        "state": raw.get("state", ""),
        "zipcode": raw.get("zipcode", ""),
        "full_address": f"{raw.get('street_address','')}, {raw.get('city','')}, {raw.get('state','')} {raw.get('zipcode','')}".strip(", "),
        "price_formatted": raw.get("price_formatted") or fmt_price(raw.get("price")),
        "bedrooms": raw.get("bedrooms", "—"),
        "bathrooms": raw.get("bathrooms", "—"),
        "sqft_formatted": f"{int(raw['sqft']):,}" if raw.get("sqft") else "—",
        "year_built": raw.get("year_built", "—"),
        "hero_photo_url": photos[0] if photos else "",
        "listing_url": listing_url,
        "brokerage_or_default": short_brand_or(brand),
    }


def write_caption_placeholders(extras_dir: Path, social_dir: Path, raw: dict, listing: dict, brand: dict):
    """Write deterministic best-guess caption/SMS files. Agent can replace at runtime."""
    street = listing["street_address"]
    city = listing["city"]
    state = listing["state"]
    price = listing["price_formatted"]
    beds = listing["bedrooms"]
    baths = listing["bathrooms"]
    sqft = listing["sqft_formatted"]
    year = listing["year_built"]
    url = listing["listing_url"]

    # Facebook caption — long-form, OIOS-playbook compatible (default per-listing footer)
    fb = f"""Just listed: {street}, {city}.

{beds} bed, {baths} bath, {sqft} sq ft. Built {year}. Listed at {price}.

{raw.get('lede_paragraph', '').strip()}

Tour, photos, video walkthrough — full link in the first comment.
"""
    (social_dir / "facebook-caption.txt").write_text(fb, encoding="utf-8")

    # First-comment line (per OIOS FB playbook — clean post, URL goes in comment)
    (social_dir / "facebook-first-comment.txt").write_text(
        f"Full virtual tour, photos, and video: {url}\n",
        encoding="utf-8",
    )

    # Instagram caption + hashtag bank (geo-scoped)
    city_tag = "".join(c for c in city.lower() if c.isalnum())
    state_tag = state.lower()
    ig = f"""{street} — {city}, {state}.

{beds} bed · {baths} bath · {sqft} sq ft · built {year}.
Listed at {price}.

Walk the property at {url}

—
#{city_tag}realestate #{state_tag}homes #justlisted #realestate
#{city_tag}homes #homesforsale #realtor #dreamhome #houseinspo
#newlisting #propertyforsale #{city_tag}living #openhouse
#movingsoon #househunting #realestateagent #firsttimehomebuyer
#{state_tag}realestate #{city_tag}{state_tag} #welcomehome
"""
    (social_dir / "instagram-caption.txt").write_text(ig, encoding="utf-8")

    # SMS sphere blast — ≤160 chars, no emojis, no special chars
    sphere = f"New listing: {street}, {city}. {beds}bd/{baths}ba, {sqft} sqft. {price}. Tour + photos: {url}"
    if len(sphere) > 160:
        # Trim to fit
        head = f"New listing in {city}: {street}. {price}. "
        tail = f"Tour: {url}"
        sphere = (head + tail)[:160]
    (social_dir / "sphere-sms.txt").write_text(sphere + "\n", encoding="utf-8")

    # Talking points placeholder — list the listing's named features as bullet starts
    talking = [
        "OPEN HOUSE TALKING POINTS",
        f"{street} — {city}, {state}",
        "=" * 60,
        "",
        "7 specific things to mention as buyers walk through.",
        "Replace these with details specific to the home — anything",
        "the listing description hints at that's worth pointing out.",
        "",
    ]
    pts = []
    for key in ("public_paragraph", "signature_paragraph", "private_paragraph"):
        if raw.get(key):
            pts.append(raw[key])
    for key in ("public_pt_1", "public_pt_2", "signature_pt_1", "signature_pt_2",
                "signature_pt_3", "private_pt_1", "private_pt_2"):
        if raw.get(key):
            pts.append(raw[key])

    talking.append("1. Approach + curb appeal")
    talking.append("   The drive up sets the first impression. Mention the street, the lot, the front of the home.")
    talking.append("")
    if len(pts) > 0:
        talking.append("2. " + (raw.get("public_headline") or "The public spaces"))
        talking.append("   " + (raw.get("public_paragraph") or pts[0])[:200])
        talking.append("")
    if len(pts) > 1:
        talking.append("3. " + (raw.get("signature_headline") or "Signature feature"))
        talking.append("   " + (raw.get("signature_paragraph") or pts[1])[:200])
        talking.append("")
    if len(pts) > 2:
        talking.append("4. " + (raw.get("private_headline") or "Primary suite"))
        talking.append("   " + (raw.get("private_paragraph") or pts[2])[:200])
        talking.append("")
    talking.append("5. Outdoor / lifestyle moment")
    talking.append("   The deck, porch, garden, view — whatever earns time outside.")
    talking.append("")
    talking.append("6. Recent updates the seller has made")
    talking.append("   New roof, HVAC, paint, appliances. Specific years if disclosed.")
    talking.append("")
    talking.append("7. Neighborhood highlights")
    talking.append("   Schools, parks, downtown, commute. What makes the address worth living at.")
    talking.append("")
    talking.append("=" * 60)
    talking.append("(Replace with Claude-generated, listing-specific points if needed)")

    (extras_dir / "open-house-talking-points.txt").write_text("\n".join(talking), encoding="utf-8")

    # Suggested social schedule
    today = datetime.now().date()
    fmt_date = lambda d: d.strftime("%A, %B %d")
    schedule = f"""SUGGESTED 7-DAY POST CADENCE
{street}, {city}, {state}
{"=" * 60}

Day 1 — {fmt_date(today)}
  · Facebook: paste facebook-caption.txt + photo (fb-feed-1080.png)
  · Facebook: drop the first-comment URL (facebook-first-comment.txt)
  · Instagram: paste instagram-caption.txt + photo (ig-feed-1080.png)

Day 2 — {fmt_date(today + timedelta(days=1))}
  · Reels: post hero-vt.mp4 with reels-cover-1080x1920.png as cover
  · Instagram Story: ig-story-1080x1920.png with link sticker → {url}

Day 4 — {fmt_date(today + timedelta(days=3))}
  · Email blast: paste email-blast.html into Mailchimp / Constant Contact
  · Subject line: see email-subject-lines.txt
  · Preview text: see email-preview-text.txt

Day 7 — {fmt_date(today + timedelta(days=6))}
  · Sphere SMS: paste sphere-sms.txt to your texting tool
  · Refresh open house posts (FB + IG) before the weekend

{"=" * 60}
All assets live at: {url.replace('https://', '')}-kit (this dashboard)
"""
    (extras_dir / "social-schedule.txt").write_text(schedule, encoding="utf-8")


def run_subrenderer(label: str, cmd: list):
    """Run a sub-renderer script, surface its output."""
    print(f"\n--- {label} ---")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        print(result.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(f"{label} failed (exit {result.returncode})")


def main():
    parser = argparse.ArgumentParser(description="Render the complete Listing Kit")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug")
    parser.add_argument("--slug", required=True, help="URL slug for this listing")
    parser.add_argument("--out", required=True, help="Output directory (becomes the kit root)")
    parser.add_argument("--base-url", default=None, help="Override the deployed landing-page URL")
    parser.add_argument("--skip-print", action="store_true", help="Skip print PDFs (faster dev iteration)")
    parser.add_argument("--skip-social", action="store_true", help="Skip social images")
    parser.add_argument("--skip-email", action="store_true", help="Skip email blast")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Make sure subdirectories exist
    for sub in ("print", "social", "email", "extras", "photos", "video"):
        (out_dir / sub).mkdir(exist_ok=True)

    # Load brand + listing
    brand = load_brand_profile(args.agent)
    print(f"Listing Kit Renderer")
    print(f"  Brand profile: {brand.get('agent_slug')!r} (tier={brand.get('tier')!r})")
    print(f"  Output: {out_dir}")

    with open(args.listing, "r", encoding="utf-8") as f:
        listing_raw = json.load(f)

    listing_url = args.base_url or derive_listing_url(args.slug, brand)
    listing = coerce(listing_raw, brand, listing_url)
    print(f"  Listing URL: {listing_url}")

    # Run sub-renderers
    py = sys.executable
    if not args.skip_print:
        run_subrenderer("Print PDFs", [
            py, str(PRINT_RENDERER),
            "--listing", args.listing,
            "--slug", args.slug,
            "--out", str(out_dir),
            *(["--agent", args.agent] if args.agent else []),
            *(["--base-url", args.base_url] if args.base_url else []),
        ])

    if not args.skip_social:
        run_subrenderer("Social images", [
            py, str(SOCIAL_RENDERER),
            "--listing", args.listing,
            "--out", str(out_dir),
            *(["--agent", args.agent] if args.agent else []),
        ])

    if not args.skip_email:
        run_subrenderer("Email blast", [
            py, str(EMAIL_RENDERER),
            "--listing", args.listing,
            "--slug", args.slug,
            "--out", str(out_dir),
            *(["--agent", args.agent] if args.agent else []),
            *(["--base-url", args.base_url] if args.base_url else []),
        ])

    # Write deterministic copy placeholders
    print("\n--- Captions / SMS / talking points / schedule ---")
    write_caption_placeholders(
        out_dir / "extras",
        out_dir / "social",
        listing_raw,
        listing,
        brand,
    )
    print("  OK: facebook-caption.txt + facebook-first-comment.txt")
    print("  OK: instagram-caption.txt")
    print("  OK: sphere-sms.txt")
    print("  OK: open-house-talking-points.txt")
    print("  OK: social-schedule.txt")

    # Render Kit Dashboard index
    print("\n--- Kit Dashboard ---")
    html = render_template(str(DASHBOARD_TEMPLATE), brand, listing)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  OK: index.html ({len(html.encode('utf-8')) // 1024} KB)")

    print(f"\n=== Listing Kit complete ===")
    print(f"Open in browser: {(out_dir / 'index.html').resolve().as_uri()}")
    print(f"Deploy this folder to: <slug>-kit.netlify.app (or her custom domain on monthly tier)")


if __name__ == "__main__":
    main()
