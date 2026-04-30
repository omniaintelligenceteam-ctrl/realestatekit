"""
Brand Profile loader for the zillow-clone Listing Kit.

Reads <agent-slug>.json from ~/.claude/skills/zillow-clone/agents/, returns a dict
with all template substitution variables. Falls back to _default.json (per-listing,
dual-branded) if no slug is passed or the slug file doesn't exist.

Usage:
    from brand_profile import load_brand_profile, render_template

    bp = load_brand_profile("kim-smith")        # or None for default
    html = render_template("brochure.html", bp, listing_data)

Template variables exposed (use {{var_name}} in HTML):
    Agent: agent_name, headshot_url, phone, email, license_number
    Brokerage: brokerage, brokerage_address, brokerage_phone, brokerage_website,
               logo_url, logo_dark_url
    Colors: primary_color, accent_color, text_color, paper_color
    Social: instagram, facebook_page, linkedin
    Tier flags: is_white_label (bool), tier (str)
    Domain: deploy_domain (custom_domain if monthly, <slug>-kit.netlify.app otherwise)
    Footer: footer_tagline
"""

import json
import re
from pathlib import Path
from typing import Optional

SKILL_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = SKILL_ROOT / "agents"


def load_brand_profile(agent_slug: Optional[str] = None) -> dict:
    """Load a brand profile JSON file by slug. Falls back to _default if not found."""
    candidates = []
    if agent_slug:
        candidates.append(AGENTS_DIR / f"{agent_slug}.json")
    candidates.append(AGENTS_DIR / "_default.json")

    for path in candidates:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                profile = json.load(f)
            # Strip _comment_* keys (documentation only)
            profile = {k: v for k, v in profile.items() if not k.startswith("_comment")}
            # Compute derived flags
            profile["is_white_label"] = profile.get("tier") == "monthly"
            # Resolve relative asset paths to absolute file:// or https:// URLs
            for key in ("logo_path", "logo_dark_path", "headshot_path"):
                val = profile.get(key)
                if val and not val.startswith(("http://", "https://", "file://")):
                    abs_path = (SKILL_ROOT / val).resolve()
                    profile[key.replace("_path", "_url")] = abs_path.as_uri()
                else:
                    profile[key.replace("_path", "_url")] = val or ""
            return profile

    raise FileNotFoundError(
        f"No brand profile found for slug={agent_slug!r} and no _default.json. "
        f"Looked in: {AGENTS_DIR}"
    )


def render_template(template_path: str, brand: dict, listing: dict) -> str:
    """Tiny mustache-style template renderer.

    - {{key}} substitutes brand[key] OR listing[key] (brand wins on conflict).
    - {{#key}}...{{/key}} renders the block only when key is truthy.
    - {{^key}}...{{/key}} renders the block only when key is falsy.
    - Missing keys render as empty string (no errors), so templates are robust.

    For lists/loops, the caller should pre-render those sections in Python
    and pass the resulting HTML strings as listing[key]. Keeps the renderer simple.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    ctx = {**listing, **brand}  # brand wins on key conflict

    # Conditional blocks: {{#key}}...{{/key}}
    def truthy_block(match):
        key, body = match.group(1), match.group(2)
        return body if ctx.get(key) else ""

    tpl = re.sub(
        r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}",
        truthy_block,
        tpl,
        flags=re.DOTALL,
    )

    # Inverse blocks: {{^key}}...{{/key}}
    def falsy_block(match):
        key, body = match.group(1), match.group(2)
        return body if not ctx.get(key) else ""

    tpl = re.sub(
        r"\{\{\^(\w+)\}\}(.*?)\{\{/\1\}\}",
        falsy_block,
        tpl,
        flags=re.DOTALL,
    )

    # Simple substitution: {{key}}
    def sub_var(match):
        key = match.group(1)
        val = ctx.get(key, "")
        return str(val) if val is not None else ""

    tpl = re.sub(r"\{\{(\w+)\}\}", sub_var, tpl)

    return tpl


if __name__ == "__main__":
    # Quick smoke test: load default profile, print structure
    bp = load_brand_profile(None)
    print("Loaded default brand profile:")
    for k, v in sorted(bp.items()):
        print(f"  {k}: {v!r}")
