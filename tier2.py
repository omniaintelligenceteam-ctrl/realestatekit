"""
Tier 2 — Listing Kit bundle.

Produces everything in Tier 1 (landing page + 3-aspect video + Facebook caption)
PLUS:
  - 3 print PDFs (brochure, leave-behind, postcard)
  - 4 social images (FB feed, IG feed, IG story, Reels cover)
  - 4 caption files (FB, IG, sphere SMS, FB first-comment)
  - Email blast (HTML + plain + 3 subjects + 2 preview texts)
  - Open-house talking points
  - Suggested 7-day social schedule
  - Kit Dashboard at <slug>-kit.netlify.app

Internally calls kit-dashboard/render_dashboard.py which orchestrates
print/render_pdfs.py + social/render_social_images.py + email/render_email.py.

Usage:
    python tier2.py --listing listing.json --slug <slug> --out ~/Downloads/<slug>-kit/
    python tier2.py --listing listing.json --slug <slug> --out <out> --deploy
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

SKILL_ROOT = Path(__file__).resolve().parent
ORCHESTRATOR = SKILL_ROOT / "kit-dashboard" / "render_dashboard.py"


def main():
    parser = argparse.ArgumentParser(description="Tier 2 — Listing Kit bundle")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug")
    parser.add_argument("--slug", required=True, help="URL slug")
    parser.add_argument("--out", required=True, help="Output directory (becomes the kit root)")
    parser.add_argument("--deploy", action="store_true", help="Auto-deploy to Netlify")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    print(f"=== Tier 2 — Listing Kit ===")
    print(f"  Slug: {args.slug}")
    print(f"  Output: {args.out}")

    cmd = [
        sys.executable, str(ORCHESTRATOR),
        "--listing", args.listing,
        "--slug", args.slug,
        "--out", args.out,
    ]
    if args.agent:
        cmd += ["--agent", args.agent]
    if args.base_url:
        cmd += ["--base-url", args.base_url]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"Kit render failed (exit {result.returncode})")

    if args.deploy:
        print(f"\n  TODO: Netlify deploy of {args.out} → <slug>-kit.netlify.app")
        print(f"        (zip the directory and POST to /api/v1/sites/<id>/deploys)")
    else:
        print(f"\n  Skipping deploy (no --deploy flag)")


if __name__ == "__main__":
    main()
