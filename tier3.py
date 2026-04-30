"""
Tier 3 — Monthly Retainer bundle (white-label).

Everything in Tier 2 PLUS:
  - ZERO OIOS branding anywhere (footer tagline blank, OG titles prefixed with HER brokerage)
  - Deploys to <slug>.<her-custom-domain> instead of <slug>-kit.netlify.app
  - "Just Sold" follow-up postcard (NEW)
  - Personal agent landing page at root of her domain (TODO)
  - Unlimited listings (pricing model — not deliverable difference)

Requires a `agents/<agent-slug>.json` brand profile with:
  - tier: "monthly"
  - custom_domain set
  - logo_path, headshot_path, colors, phone, email, license_number filled in

Usage:
    python tier3.py --listing listing.json --agent kim-smith --slug <slug> --out <out> --deploy
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
sys.path.insert(0, str(SKILL_ROOT / "print"))
from brand_profile import load_brand_profile  # noqa: E402

ORCHESTRATOR = SKILL_ROOT / "kit-dashboard" / "render_dashboard.py"


def main():
    parser = argparse.ArgumentParser(description="Tier 3 — Monthly Retainer (white-label)")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", required=True, help="Brand profile slug (REQUIRED for Tier 3)")
    parser.add_argument("--slug", required=True, help="URL slug")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--deploy", action="store_true", help="Auto-deploy to her custom domain")
    args = parser.parse_args()

    # Validate the brand profile is actually configured for white-label
    brand = load_brand_profile(args.agent)
    if brand.get("tier") != "monthly":
        raise SystemExit(
            f"Tier 3 requires brand profile with tier='monthly'.\n"
            f"  Profile: {args.agent!r}\n"
            f"  Current tier: {brand.get('tier')!r}\n"
            f"  Edit agents/{args.agent}.json and set tier='monthly' + custom_domain"
        )
    if not brand.get("custom_domain"):
        raise SystemExit(
            f"Tier 3 requires a custom_domain in the brand profile.\n"
            f"  Profile: {args.agent!r}\n"
            f"  Edit agents/{args.agent}.json and set custom_domain (e.g. 'listings.smithcorealty.com')"
        )

    print(f"=== Tier 3 — Monthly Retainer (white-label) ===")
    print(f"  Agent: {brand.get('agent_name')!r} @ {brand.get('brokerage')!r}")
    print(f"  Custom domain: {brand['custom_domain']}")
    print(f"  Slug: {args.slug}")
    print(f"  Deploy target: https://{args.slug}.{brand['custom_domain']}")

    cmd = [
        sys.executable, str(ORCHESTRATOR),
        "--listing", args.listing,
        "--agent", args.agent,
        "--slug", args.slug,
        "--out", args.out,
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"Kit render failed (exit {result.returncode})")

    # TODO: Generate "Just Sold" postcard variant (Tier 3 only)
    print(f"\n  TODO: Just-sold postcard (Tier 3 only — same template, different copy)")

    if args.deploy:
        print(f"\n  TODO: Deploy {args.out} → https://{args.slug}.{brand['custom_domain']}")
    else:
        print(f"\n  Skipping deploy (no --deploy flag)")


if __name__ == "__main__":
    main()
