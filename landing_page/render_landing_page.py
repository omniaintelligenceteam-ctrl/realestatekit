"""
Landing-page renderer — generates a Hyper-Agent-style HTML landing page for a
listing by doing anchored substitutions on the 148 reference HTML.

Approach:
  The 148 HTML is ~3000 lines of inline CSS + content. Rather than maintain a
  duplicated `template.html` (which would drift from the references), this
  renderer reads the 148 reference at runtime and substitutes ONLY the
  listing-specific strings — anchored by enough context to be unambiguous.

  This means: the reference 148 HTML IS the template. To improve the styling,
  edit `examples/148-pheasant-run-paducah-ky.html` directly — the next render
  picks it up.

Usage:
    python landing_page/render_landing_page.py \
      --listing path/to/listing.json \
      --agent kim-smith \
      --slug 148-pheasant-run-paducah-ky \
      --out ~/Downloads/<slug>/

Output: <out>/<slug>.html

Limitations (Phase 1):
  - Brand-profile colors / logo NOT injected yet (the 148 HTML uses hardcoded
    palette values). For white-label (Tier 3), the rendered page falls back to
    the OIOS palette. CSS variable injection is the next iteration.
  - Photo replacement assumes Zillow CDN URL pattern; if listing.photos uses
    a different host, the substitution may miss some images.
  - The narrative paragraphs need to be replaced with Claude-generated copy
    matching the listing — for now, the script outputs a working page with
    the 148 content as a starting point and flags the spots that need rewriting.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "print"))
from brand_profile import load_brand_profile  # noqa: E402

REFERENCE_HTML = SKILL_ROOT / "examples" / "148-pheasant-run-paducah-ky.html"


def fmt_price(p):
    if p is None:
        return ""
    try:
        return f"${int(p):,}"
    except (TypeError, ValueError):
        return str(p)


def derive_listing_url(slug: str, brand: dict) -> str:
    if brand.get("is_white_label") and brand.get("custom_domain"):
        return f"https://{slug}.{brand['custom_domain']}"
    return f"https://{slug}.netlify.app"


# Hardcoded values from the 148 reference that need replacement
# Anchor on enough surrounding text to be unique; use word-boundary or tag context.
REF_ADDRESS = "148 Pheasant Run"
REF_CITY = "Paducah"
REF_STATE = "KY"
REF_ZIP = "42001"
REF_PRICE = "$580,000"


def substitute_html(html: str, listing: dict, brand: dict, listing_url: str, slug: str) -> str:
    """Run anchored replacements on the 148 reference HTML.

    Strategy: replace longest, most-contextual strings first to avoid clashes.
    """
    out = html

    # 1. Title + OG meta — these have full strings we can anchor on
    full_addr_148 = f"{REF_ADDRESS}, {REF_CITY}, {REF_STATE} {REF_ZIP}"
    full_addr_new = f"{listing['street_address']}, {listing['city']}, {listing['state']} {listing['zipcode']}"
    out = out.replace(full_addr_148, full_addr_new)

    # 2. Title bar combining address + price
    title_148 = f"{REF_ADDRESS}, {REF_CITY}, {REF_STATE} {REF_ZIP} — {REF_PRICE}"
    title_new = f"{listing['street_address']}, {listing['city']}, {listing['state']} {listing['zipcode']} — {listing['price_formatted']}"
    out = out.replace(title_148, title_new)

    # 3. Hero / topbar / footer address pieces — replace remaining occurrences of
    # 148-specific strings
    out = out.replace(REF_ADDRESS, listing["street_address"])
    out = out.replace(f"{REF_CITY}, {REF_STATE} {REF_ZIP}", f"{listing['city']}, {listing['state']} {listing['zipcode']}")
    out = out.replace(f"{REF_CITY}, {REF_STATE}", f"{listing['city']}, {listing['state']}")
    out = out.replace(REF_PRICE, listing["price_formatted"])

    # 4. Stats — these can collide with random "4" or "3" in CSS, so anchor on context
    # Highlights strip stat-num divs
    if listing.get("bedrooms"):
        out = re.sub(
            r'(<div class="stat-num">)4(</div>\s*<div class="stat-label">Bedrooms)',
            f"\\g<1>{listing['bedrooms']}\\g<2>",
            out,
        )
    if listing.get("bathrooms"):
        out = re.sub(
            r'(<div class="stat-num">)3\.5(</div>\s*<div class="stat-label">Bathrooms)',
            f"\\g<1>{listing['bathrooms']}\\g<2>",
            out,
        )
        out = re.sub(
            r'(<div class="stat-num">)3(</div>\s*<div class="stat-label">Bathrooms)',
            f"\\g<1>{listing['bathrooms']}\\g<2>",
            out,
        )
    if listing.get("sqft"):
        sqft_str = f"{int(listing['sqft']):,}"
        out = re.sub(
            r'(<div class="stat-num">)3,?450(</div>\s*<div class="stat-label">Sq Ft)',
            f"\\g<1>{sqft_str}\\g<2>",
            out,
        )
    if listing.get("year_built"):
        out = re.sub(
            r'(<div class="stat-num">)1992(</div>\s*<div class="stat-label">Year Built)',
            f"\\g<1>{listing['year_built']}\\g<2>",
            out,
        )

    # 5. OG image — replace the hero photo URL anchored on og:image
    if listing.get("photos") and listing["photos"]:
        hero_url = listing["photos"][0]
        out = re.sub(
            r'(<meta property="og:image" content=")[^"]+(")',
            f"\\g<1>{hero_url}\\g<2>",
            out,
            count=1,
        )
        # Also replace hero img src — anchor on class="hero-still" or first <img class="hero
        out = re.sub(
            r'(<img[^>]*class="hero-[a-z-]*"[^>]*src=")[^"]+(")',
            f"\\g<1>{hero_url}\\g<2>",
            out,
            count=1,
        )

    # 6. OG URL — point at the new deployed landing page URL
    out = re.sub(
        r'(<meta property="og:url" content=")[^"]*(")',
        f"\\g<1>{listing_url}\\g<2>",
        out,
        count=1,
    )

    # 7. Replace all gallery photo URLs (rest of listing.photos) wholesale
    # The 148 reference uses Zillow CDN URLs — we substitute by index where possible.
    # If we have photos[1..N], replace the matching index in the masonry gallery.
    # This is best-effort: count masonry-item img srcs and rotate listing.photos through them.
    if listing.get("photos") and len(listing["photos"]) > 1:
        masonry_imgs = re.findall(
            r'(<div class="masonry-item">\s*<img[^>]*src=")([^"]+)(")',
            out,
        )
        new_photos = listing["photos"][1:]  # skip hero (already done)
        if masonry_imgs and new_photos:
            # Replace each masonry img src with photos[i % len(new_photos)]
            i = 0
            def repl(m):
                nonlocal i
                new_url = new_photos[i % len(new_photos)]
                i += 1
                return f"{m.group(1)}{new_url}{m.group(3)}"
            out = re.sub(
                r'(<div class="masonry-item">\s*<img[^>]*src=")([^"]+)(")',
                repl,
                out,
            )

    # 8. Agent card — replace agent name, phone, email, brokerage, license
    agent_name = brand.get("agent_name") or ""
    if agent_name:
        # The 148 HTML uses a specific agent — anchor on the agent-card div if present
        out = re.sub(
            r'(<div class="agent-name[^"]*">)[^<]+(</div>)',
            f"\\g<1>{agent_name}\\g<2>",
            out,
        )
    if brand.get("phone"):
        out = re.sub(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", brand["phone"], out, count=1)
    if brand.get("brokerage"):
        # Replace the brokerage line — anchor on broker-name or similar class
        out = re.sub(
            r'(<div class="broker-name[^"]*">)[^<]+(</div>)',
            f"\\g<1>{brand['brokerage']}\\g<2>",
            out,
        )

    # 9. Map embed — Google Maps q= parameter
    encoded_addr = full_addr_new.replace(" ", "+").replace(",", "%2C")
    out = re.sub(
        r'(maps\?q=)[^&"]+(&)',
        f"\\g<1>{encoded_addr}\\g<2>",
        out,
    )

    return out


def main():
    parser = argparse.ArgumentParser(description="Render listing landing page from 148 reference")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug")
    parser.add_argument("--slug", required=True, help="URL slug")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--base-url", default=None, help="Override deployed URL")
    args = parser.parse_args()

    if not REFERENCE_HTML.exists():
        raise SystemExit(f"Reference HTML missing: {REFERENCE_HTML}")

    with open(args.listing, "r", encoding="utf-8") as f:
        listing_raw = json.load(f)

    brand = load_brand_profile(args.agent)
    listing_url = args.base_url or derive_listing_url(args.slug, brand)

    listing = {
        **listing_raw,
        "price_formatted": listing_raw.get("price_formatted") or fmt_price(listing_raw.get("price")),
    }

    print(f"Landing page renderer")
    print(f"  Reference: {REFERENCE_HTML.name}")
    print(f"  Output slug: {args.slug}")
    print(f"  Brand: {brand.get('agent_slug')!r}")

    html = REFERENCE_HTML.read_text(encoding="utf-8")
    rendered = substitute_html(html, listing, brand, listing_url, args.slug)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.slug}.html"
    out_path.write_text(rendered, encoding="utf-8")

    size_kb = out_path.stat().st_size // 1024
    print(f"\n=== Landing page complete ===")
    print(f"  {out_path} ({size_kb} KB)")
    print(f"  Open: {out_path.as_uri()}")
    print(f"\nNOTE: Narrative paragraphs + feature pulls + spec sheet still contain")
    print(f"      148-specific copy. Hand-edit those sections OR run the upstream")
    print(f"      Claude pipeline (per SKILL.md Step 4) to rewrite them per-listing.")


if __name__ == "__main__":
    main()
