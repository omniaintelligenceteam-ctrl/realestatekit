"""
Tier 1 — Digital bundle.

Produces:
  - <slug>.html (the editorial landing page)
  - <slug>-hero.mp4, <slug>-hero-sq.mp4, <slug>-hero-vt.mp4 (3-aspect video)
  - facebook-caption.txt + facebook-first-comment.txt
  - Optional Netlify deploy at <slug>.netlify.app

Usage:
    python tier1.py --listing listing.json --slug 148-pheasant-run-paducah-ky --out ~/Downloads/<slug>/
    python tier1.py --listing listing.json --slug <slug> --out <out> --deploy   # adds Netlify deploy

NOTE: As of commit #2, the **landing-page HTML and video pipeline are NOT YET
generalized** in this repo. They live in:
  - `examples/116-country-club-lane-paducah-ky.html` (reference)
  - `examples/148-pheasant-run-paducah-ky.html` (reference)
  - `examples/2001-jefferson-street-paducah-ky.html` (reference)
  - `video/assemble.py` (the actual FFmpeg orchestrator from the 148 build)

The agent currently authors the landing-page HTML inline by cloning the structure
of those reference files (per SKILL.md). This tier1.py is a placeholder that
documents the contract — the next iteration will extract a fillable template from
the references and call FFmpeg directly.

For now, this script:
  1. Copies a reference HTML to <out>/<slug>.html as a starting point
  2. Writes the Facebook caption + first-comment files (deterministic from listing)
  3. (TODO) Renders the 3-aspect video via assemble.py
  4. (TODO with --deploy) Pushes to Netlify
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

SKILL_ROOT = Path(__file__).resolve().parent
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


def write_facebook_caption(out_dir: Path, raw: dict, brand: dict, listing_url: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    street = raw.get("street_address", "")
    city = raw.get("city", "")
    price = raw.get("price_formatted") or fmt_price(raw.get("price"))
    beds = raw.get("bedrooms", "")
    baths = raw.get("bathrooms", "")
    sqft = f"{int(raw['sqft']):,}" if raw.get("sqft") else "—"
    year = raw.get("year_built", "")
    lede = (raw.get("lede_paragraph") or raw.get("description_short") or "").strip()

    fb = f"""Just listed: {street}, {city}.

{beds} bed, {baths} bath, {sqft} sq ft. Built {year}. Listed at {price}.

{lede}

Tour, photos, video walkthrough — full link in the first comment.
"""
    (out_dir / "facebook-caption.txt").write_text(fb, encoding="utf-8")
    (out_dir / "facebook-first-comment.txt").write_text(
        f"Full virtual tour, photos, and video: {listing_url}\n",
        encoding="utf-8",
    )
    print(f"  OK: facebook-caption.txt + facebook-first-comment.txt")


def main():
    parser = argparse.ArgumentParser(description="Tier 1 — Digital bundle")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug")
    parser.add_argument("--slug", required=True, help="URL slug")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--deploy", action="store_true", help="Auto-deploy to Netlify")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    brand = load_brand_profile(args.agent)
    print(f"=== Tier 1 — Digital ===")
    print(f"  Brand profile: {brand.get('agent_slug')!r} (tier={brand.get('tier')!r})")
    print(f"  Output: {out_dir}")

    with open(args.listing, "r", encoding="utf-8") as f:
        listing_raw = json.load(f)

    listing_url = args.base_url or derive_listing_url(args.slug, brand)

    # 1. Landing page HTML — currently a copy of the reference (TODO: extract template)
    if REFERENCE_HTML.exists():
        target = out_dir / f"{args.slug}.html"
        shutil.copy(REFERENCE_HTML, target)
        print(f"  OK: {target.name} (cloned from reference — agent should hand-edit per SKILL.md)")
    else:
        print(f"  SKIP: No reference HTML at {REFERENCE_HTML}")

    # 2. Facebook caption + first-comment
    write_facebook_caption(out_dir, listing_raw, brand, listing_url)

    # 3. Video — TODO
    print(f"  TODO: 3-aspect video pipeline (see video/assemble.py — currently per-listing scratch)")

    # 4. Deploy — TODO
    if args.deploy:
        print(f"  TODO: Netlify deploy → {listing_url}")
        print(f"        (zip {out_dir} and POST to /api/v1/sites/<id>/deploys)")
    else:
        print(f"  Skipping deploy (no --deploy flag)")

    print(f"\nLanding URL target: {listing_url}")


if __name__ == "__main__":
    main()
