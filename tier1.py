"""
Tier 1 — Digital bundle.

Produces:
  - <slug>.html — editorial landing page (rendered via landing_page/render_landing_page.py)
  - <slug>-hero.mp4, <slug>-hero-sq.mp4, <slug>-hero-vt.mp4 — 3-aspect video
    (rendered via video/render_video.py if --photos passed)
  - facebook-caption.txt + facebook-first-comment.txt
  - Optional Netlify deploy at <slug>.netlify.app

Usage:
    python tier1.py --listing listing.json --slug 148-pheasant-run-paducah-ky --out ~/Downloads/<slug>/
    python tier1.py --listing listing.json --slug <slug> --out <out> --deploy
    python tier1.py --listing listing.json --slug <slug> --out <out> --photos p1.jpg p2.jpg ...
"""

import argparse
import json
import subprocess
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

LANDING_RENDERER = SKILL_ROOT / "landing_page" / "render_landing_page.py"
VIDEO_RENDERER = SKILL_ROOT / "video" / "render_video.py"
NETLIFY_DEPLOY = SKILL_ROOT / "deploy" / "netlify_deploy.py"


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


def run_step(label: str, cmd: list):
    print(f"\n--- {label} ---")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"{label} failed (exit {result.returncode})")


def main():
    parser = argparse.ArgumentParser(description="Tier 1 — Digital bundle")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug")
    parser.add_argument("--slug", required=True, help="URL slug")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--deploy", action="store_true", help="Auto-deploy to Netlify")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--photos", nargs="*", help="Optional: photo paths to render the 3-aspect video")
    parser.add_argument("--narration-text", default=None, help="Optional narration script for the video")
    parser.add_argument("--skip-narration", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    brand = load_brand_profile(args.agent)
    print(f"=== Tier 1 — Digital ===")
    print(f"  Brand: {brand.get('agent_slug')!r} (tier={brand.get('tier')!r})")
    print(f"  Output: {out_dir}")

    with open(args.listing, "r", encoding="utf-8") as f:
        listing_raw = json.load(f)

    listing_url = args.base_url or derive_listing_url(args.slug, brand)

    # 1. Landing page HTML — anchored substitution on 148 reference
    cmd = [
        sys.executable, str(LANDING_RENDERER),
        "--listing", args.listing,
        "--slug", args.slug,
        "--out", str(out_dir),
    ]
    if args.agent:
        cmd += ["--agent", args.agent]
    if args.base_url:
        cmd += ["--base-url", args.base_url]
    run_step("Landing page", cmd)

    # 2. Facebook caption + first-comment (deterministic)
    print(f"\n--- Facebook caption ---")
    write_facebook_caption(out_dir, listing_raw, brand, listing_url)

    # 3. Video — only if --photos provided
    if args.photos:
        video_out = out_dir / "video"
        cmd = [
            sys.executable, str(VIDEO_RENDERER),
            "--photos", *args.photos,
            "--slug", args.slug,
            "--out", str(video_out),
        ]
        if args.narration_text:
            cmd += ["--narration-text", args.narration_text]
        if args.skip_narration:
            cmd += ["--skip-narration"]
        run_step("3-aspect video", cmd)
    else:
        print(f"\n--- Video: skipped (no --photos provided) ---")

    # 4. Deploy to Netlify
    if args.deploy:
        cmd = [
            sys.executable, str(NETLIFY_DEPLOY),
            "--dir", str(out_dir),
            "--slug", args.slug,
            "--tier", brand.get("tier", "per-listing"),
        ]
        run_step("Netlify deploy", cmd)
    else:
        print(f"\n--- Deploy: skipped (no --deploy flag) ---")

    print(f"\n=== Tier 1 complete ===")
    print(f"  Output: {out_dir}")
    print(f"  Landing target: {listing_url}")


if __name__ == "__main__":
    main()
