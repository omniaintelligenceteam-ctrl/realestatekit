"""
Email Blast Renderer — fills the Listing Kit email template + writes a plain-text
fallback + 3 subject lines + 2 preview text variants.

Subject lines and preview text are written deterministically from listing data
(no LLM call needed) — agent or Wes can swap any of them with copy-paste.

Usage:
    python render_email.py \
      --listing path/to/listing.json \
      --agent kim-smith \
      --slug 148-pheasant-run-paducah-ky \
      --out ~/Downloads/<slug>-kit/

Outputs in <out>/email/:
  - email-blast.html               (paste into Mailchimp / Constant Contact)
  - email-blast.txt                (plain-text fallback)
  - email-subject-lines.txt        (3 options)
  - email-preview-text.txt         (2 options)
"""

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Reuse brand_profile loader from print/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "print"))
from brand_profile import load_brand_profile, render_template  # noqa: E402

EMAIL_TEMPLATE = Path(__file__).resolve().parent / "blast.html"


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


def coerce(raw: dict, brand: dict, listing_url: str, slug: str) -> dict:
    photos = raw.get("photos", []) or []

    def at(i, fb=0):
        if i < len(photos):
            return photos[i]
        return photos[fb] if fb < len(photos) else ""

    return {
        "street_address": raw.get("street_address", ""),
        "city": raw.get("city", ""),
        "state": raw.get("state", ""),
        "zipcode": raw.get("zipcode", ""),
        "full_address": f"{raw.get('street_address','')}, {raw.get('city','')}, {raw.get('state','')} {raw.get('zipcode','')}".strip(", "),
        "price_formatted": raw.get("price_formatted") or fmt_price(raw.get("price")),
        "bedrooms": raw.get("bedrooms", ""),
        "bathrooms": raw.get("bathrooms", ""),
        "sqft_formatted": f"{int(raw['sqft']):,}" if raw.get("sqft") else "—",
        "year_built": raw.get("year_built", ""),
        "hero_photo_url": at(0),
        "strip_photo_1": at(1, 0),
        "strip_photo_2": at(2, 0),
        "strip_photo_3": at(3, 0),
        "lede_paragraph": raw.get("lede_paragraph") or raw.get("description_short") or raw.get("description", ""),
        "listing_url": listing_url,
        "brokerage_or_default": short_brand_or(brand),
        "preview_text": "",  # filled below
    }


def subject_lines(listing: dict, brand: dict) -> list:
    """Return 3 subject line options. Specific, no AI tells, lowercase-ish."""
    street = listing.get("street_address", "")
    city = listing.get("city", "")
    price = listing.get("price_formatted", "")
    beds = listing.get("bedrooms", "")
    baths = listing.get("bathrooms", "")
    return [
        f"new listing — {street}, {city}",
        f"{street} hits the market today ({price})",
        f"{beds} bed, {baths} bath in {city} — {price}",
    ]


def preview_texts(listing: dict, brand: dict) -> list:
    """Return 2 preview-text options (the 'before-the-fold' line under the subject)."""
    sqft = listing.get("sqft_formatted", "")
    year = listing.get("year_built", "")
    return [
        f"{sqft} sq ft · built {year} · full virtual tour inside.",
        "Photos, floor plans, neighborhood, and a video walkthrough — see it all here.",
    ]


def html_to_plaintext(listing: dict, brand: dict) -> str:
    """Build a clean plain-text version of the email — no HTML, no markup."""
    lines = []
    lines.append(short_brand_or(brand).upper())
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"A NEW LISTING IN {listing.get('city','').upper()}")
    lines.append("")
    lines.append(listing.get("street_address", ""))
    lines.append(f"{listing.get('city','')}, {listing.get('state','')} {listing.get('zipcode','')}")
    lines.append(listing.get("price_formatted", ""))
    lines.append("")
    lines.append("-" * 60)
    lines.append(f"{listing.get('bedrooms','')} bed   ·   {listing.get('bathrooms','')} bath   ·   {listing.get('sqft_formatted','')} sq ft   ·   built {listing.get('year_built','')}")
    lines.append("-" * 60)
    lines.append("")
    lines.append(listing.get("lede_paragraph", "").strip())
    lines.append("")
    lines.append(f"View the full tour: {listing.get('listing_url','')}")
    lines.append("")
    lines.append("Photos · video walkthrough · floor plans · neighborhood")
    lines.append("")
    lines.append("-" * 60)
    if brand.get("agent_name"):
        lines.append(brand["agent_name"])
    if brand.get("brokerage"):
        lines.append(brand["brokerage"])
    if brand.get("phone"):
        lines.append(brand["phone"])
    if brand.get("email"):
        lines.append(brand["email"])
    lines.append("")
    lines.append(brand.get("footer_tagline", ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Render Listing Kit email blast")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug")
    parser.add_argument("--slug", required=True, help="URL slug for this listing")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--base-url", default=None, help="Override the landing-page URL")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    email_out = out_dir / "email"
    email_out.mkdir(parents=True, exist_ok=True)

    brand = load_brand_profile(args.agent)
    print(f"Brand profile: {brand.get('agent_slug')!r} (tier={brand.get('tier')!r})")

    with open(args.listing, "r", encoding="utf-8") as f:
        listing_raw = json.load(f)

    listing_url = args.base_url or derive_listing_url(args.slug, brand)
    listing = coerce(listing_raw, brand, listing_url, args.slug)

    # Pick the 1st preview text by default for the hidden preheader div in the HTML
    previews = preview_texts(listing, brand)
    listing["preview_text"] = previews[0]

    # Render HTML
    html = render_template(str(EMAIL_TEMPLATE), brand, listing)
    html_path = email_out / "email-blast.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  OK: email-blast.html ({len(html.encode('utf-8')) // 1024} KB)")

    # Plain text
    txt_path = email_out / "email-blast.txt"
    txt_path.write_text(html_to_plaintext(listing, brand), encoding="utf-8")
    print(f"  OK: email-blast.txt")

    # Subject lines
    subs = subject_lines(listing, brand)
    (email_out / "email-subject-lines.txt").write_text(
        "EMAIL SUBJECT LINE OPTIONS\n"
        "Pick one. Specific beats clever. Lowercase-leaning works on iOS preview.\n\n"
        + "\n".join(f"{i+1}. {s}" for i, s in enumerate(subs))
        + "\n",
        encoding="utf-8",
    )
    print(f"  OK: email-subject-lines.txt ({len(subs)} options)")

    # Preview text
    (email_out / "email-preview-text.txt").write_text(
        "EMAIL PREVIEW TEXT OPTIONS (the line shown under subject in inbox preview)\n"
        "Pick one. Should add something the subject doesn't say.\n\n"
        + "\n".join(f"{i+1}. {p}" for i, p in enumerate(previews))
        + "\n",
        encoding="utf-8",
    )
    print(f"  OK: email-preview-text.txt ({len(previews)} options)")

    print(f"\n=== Email pack complete ===")
    print(f"Output dir: {email_out}")


if __name__ == "__main__":
    main()
