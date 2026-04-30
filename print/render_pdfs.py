"""
Print Kit Renderer — produces brochure / one-sheet / postcard PDFs for a listing.

Usage:
    python render_pdfs.py \
      --listing path/to/listing.json \
      --agent kim-smith \
      --slug 148-pheasant-run-paducah-ky \
      --out C:/Users/.../Downloads/148-pheasant-run-paducah-ky-kit/

Inputs:
  --listing : JSON file with extracted Zillow listing data + photos + narrative.
              See example schema in `_listing_example.json`.
  --agent   : Brand-profile slug (matches `agents/<slug>.json`). Default: _default.
  --slug    : URL/folder slug for this listing (e.g. "148-pheasant-run-paducah-ky").
              Used to build the listing_url + output paths.
  --out     : Output directory. PDFs written into <out>/print/.
  --base-url: Optional. Base URL the QR code points to. Defaults to
              https://<slug>-kit.netlify.app (per-listing) or
              https://<slug>.<custom_domain> (monthly white-label).

Outputs (in <out>/print/):
  - brochure-8page.pdf
  - leave-behind-1sheet.pdf
  - postcard-just-listed.pdf
  - qr.png  (debug — the QR code as a standalone PNG)
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows so progress messages with unicode (e.g. "→") don't crash cp1252 console
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

import qrcode
from playwright.async_api import async_playwright

# Local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand_profile import load_brand_profile, render_template

PRINT_DIR = Path(__file__).resolve().parent
TEMPLATES = {
    "brochure": PRINT_DIR / "brochure.html",
    "one-sheet": PRINT_DIR / "one-sheet.html",
    "postcard": PRINT_DIR / "postcard.html",
}
OUTPUT_NAMES = {
    "brochure": "brochure-8page.pdf",
    "one-sheet": "leave-behind-1sheet.pdf",
    "postcard": "postcard-just-listed.pdf",
}
PAGE_FORMATS = {
    "brochure": {"width": "8.5in", "height": "11in"},
    "one-sheet": {"width": "8.5in", "height": "11in"},
    "postcard": {"width": "6in", "height": "4.25in"},
}


def fmt_price(p):
    if p is None:
        return ""
    try:
        return f"${int(p):,}"
    except (TypeError, ValueError):
        return str(p)


def fmt_int(n):
    if n is None or n == "":
        return ""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


def short_int(n):
    """Compact form: 4500 → '4,500'; preserves whole number look."""
    if n is None or n == "":
        return "—"
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


def lot_short(listing):
    """Returns a tuple (value_str, unit_label) for the stats strip."""
    acres = listing.get("lot_area_value")
    units = (listing.get("lot_area_units") or "").lower()
    if acres and units in ("acres", "acre"):
        try:
            v = float(acres)
            if v >= 10:
                return f"{v:.0f}", "Acres"
            else:
                return f"{v:.2f}".rstrip("0").rstrip("."), "Acres"
        except (TypeError, ValueError):
            pass
    sqft = listing.get("lot_size")
    if sqft:
        try:
            return f"{int(sqft):,}", "Sq Ft Lot"
        except (TypeError, ValueError):
            pass
    return "—", "Lot"


def lot_full(listing):
    """Long form for spec sheets, e.g. '0.42 acres (18,295 sq ft)'."""
    acres = listing.get("lot_area_value")
    units = (listing.get("lot_area_units") or "").lower()
    sqft = listing.get("lot_size")
    parts = []
    if acres and units in ("acres", "acre"):
        try:
            v = float(acres)
            parts.append(f"{v:.2f}".rstrip("0").rstrip(".") + " acres")
        except (TypeError, ValueError):
            pass
    if sqft:
        try:
            parts.append(f"{int(sqft):,} sq ft")
        except (TypeError, ValueError):
            pass
    return " · ".join(parts) if parts else "—"


def build_qr(url: str, out_path: Path) -> str:
    """Generate a QR code PNG. Returns file:// URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)
    return out_path.resolve().as_uri()


def derive_listing_url(slug: str, brand: dict) -> str:
    """Compute the public URL the QR code points at."""
    if brand.get("is_white_label") and brand.get("custom_domain"):
        return f"https://{slug}.{brand['custom_domain']}"
    return f"https://{slug}-kit.netlify.app"


def short_brand(brand: dict) -> str:
    """Top-bar brand name fallback when no logo image exists."""
    return brand.get("brokerage") or brand.get("agent_name") or "LISTING KIT"


def coerce_listing(raw: dict, brand: dict, listing_url: str) -> dict:
    """Normalize a listing JSON dict into the variables our templates expect."""
    street = raw.get("street_address", "")
    city = raw.get("city", "")
    state = raw.get("state", "")
    zipcode = raw.get("zipcode", "")
    full_address = (
        f"{street}, {city}, {state} {zipcode}".strip(", ")
        if street
        else f"{city}, {state}".strip(", ")
    )

    photos = raw.get("photos", []) or []

    def photo_at(idx, fallback_idx=0):
        if idx < len(photos):
            return photos[idx]
        if fallback_idx < len(photos):
            return photos[fallback_idx]
        return ""

    lot_v, lot_u = lot_short(raw)

    short = (street or "").upper()

    # Trim "STREET" / "ROAD" / etc from the topbar short brand if no logo
    return {
        # Address
        "street_address": street,
        "city": city,
        "state": state,
        "zipcode": zipcode,
        "full_address": full_address,
        # Price
        "price_formatted": raw.get("price_formatted") or fmt_price(raw.get("price")),
        # Stats
        "bedrooms": raw.get("bedrooms", "—"),
        "bathrooms": raw.get("bathrooms", "—"),
        "sqft_short": short_int(raw.get("sqft")),
        "sqft_formatted": fmt_int(raw.get("sqft")),
        "lot_short": lot_v,
        "lot_unit": lot_u,
        "lot_size_formatted": lot_full(raw),
        "year_built": raw.get("year_built", "—"),
        "garage_spaces": raw.get("garage_spaces", "—"),
        "mls_id": raw.get("mls_id", "—"),
        "home_type": raw.get("home_type", "Single Family"),
        # Photos
        "hero_photo_url": photo_at(0),
        "strip_photo_1": photo_at(1, 0),
        "strip_photo_2": photo_at(2, 0),
        "strip_photo_3": photo_at(3, 0),
        "photo_lede": photo_at(0),
        "photo_public": photo_at(2, 0),
        "photo_signature": photo_at(4, 0),
        "photo_private": photo_at(6, 0),
        # Brochure narrative blocks
        "lede_headline": raw.get("lede_headline", ""),
        "lede_paragraph": raw.get("lede_paragraph", ""),
        "public_headline": raw.get("public_headline", "The public spaces"),
        "public_paragraph": raw.get("public_paragraph", ""),
        "public_pt_1": raw.get("public_pt_1"),
        "public_pt_2": raw.get("public_pt_2"),
        "public_pt_3": raw.get("public_pt_3"),
        "public_pt_4": raw.get("public_pt_4"),
        "signature_headline": raw.get("signature_headline", ""),
        "signature_paragraph": raw.get("signature_paragraph", ""),
        "signature_pt_1": raw.get("signature_pt_1"),
        "signature_pt_2": raw.get("signature_pt_2"),
        "signature_pt_3": raw.get("signature_pt_3"),
        "signature_pt_4": raw.get("signature_pt_4"),
        "private_headline": raw.get("private_headline", "A private retreat"),
        "private_paragraph": raw.get("private_paragraph", ""),
        "private_pt_1": raw.get("private_pt_1"),
        "private_pt_2": raw.get("private_pt_2"),
        "private_pt_3": raw.get("private_pt_3"),
        "pullquote_text": raw.get("pullquote_text", ""),
        "description_short": raw.get("description_short", raw.get("description", "")),
        # Spec sheet
        "feat_1_label": raw.get("feat_1_label"),
        "feat_1_value": raw.get("feat_1_value"),
        "feat_2_label": raw.get("feat_2_label"),
        "feat_2_value": raw.get("feat_2_value"),
        "feat_3_label": raw.get("feat_3_label"),
        "feat_3_value": raw.get("feat_3_value"),
        "feat_4_label": raw.get("feat_4_label"),
        "feat_4_value": raw.get("feat_4_value"),
        "feat_5_label": raw.get("feat_5_label"),
        "feat_5_value": raw.get("feat_5_value"),
        "feat_6_label": raw.get("feat_6_label"),
        "feat_6_value": raw.get("feat_6_value"),
        # Highlights for one-sheet
        "highlight_1": raw.get("highlight_1"),
        "highlight_2": raw.get("highlight_2"),
        "highlight_3": raw.get("highlight_3"),
        "highlight_4": raw.get("highlight_4"),
        "highlight_5": raw.get("highlight_5"),
        "highlight_6": raw.get("highlight_6"),
        # Neighborhood
        "nb_1_label": raw.get("nb_1_label"),
        "nb_1_value": raw.get("nb_1_value"),
        "nb_2_label": raw.get("nb_2_label"),
        "nb_2_value": raw.get("nb_2_value"),
        "nb_3_label": raw.get("nb_3_label"),
        "nb_3_value": raw.get("nb_3_value"),
        "nb_4_label": raw.get("nb_4_label"),
        "nb_4_value": raw.get("nb_4_value"),
        "nb_5_label": raw.get("nb_5_label"),
        "nb_5_value": raw.get("nb_5_value"),
        # Brand fallbacks
        "short_brand": short or short_brand(brand),
        "brokerage_or_default": brand.get("brokerage") or "Listing Kit",
        # Listing URL (the live landing page)
        "listing_url": listing_url,
    }


async def render_pdf(html_path: Path, pdf_path: Path, page_size: dict, browser):
    """Render a single HTML file to a PDF via Playwright."""
    page = await browser.new_page()
    try:
        # Load via file:// URL so the @page CSS rules apply correctly
        await page.goto(html_path.as_uri(), wait_until="networkidle", timeout=60000)
        # Wait for web fonts (Google Fonts) to finish loading
        await page.evaluate("document.fonts.ready")
        await page.pdf(
            path=str(pdf_path),
            width=page_size["width"],
            height=page_size["height"],
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            prefer_css_page_size=True,
        )
    finally:
        await page.close()


async def main_async(args):
    out_dir = Path(args.out).resolve()
    print_out = out_dir / "print"
    work_dir = out_dir / ".work"
    print_out.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load brand profile
    brand = load_brand_profile(args.agent)
    print(f"Brand profile: {brand.get('agent_slug')!r} (tier={brand.get('tier')!r})")

    # 2. Load listing
    with open(args.listing, "r", encoding="utf-8") as f:
        listing_raw = json.load(f)

    # 3. Resolve listing URL + generate QR
    listing_url = args.base_url or derive_listing_url(args.slug, brand)
    qr_path = work_dir / "qr.png"
    qr_url = build_qr(listing_url, qr_path)
    print(f"QR target: {listing_url}")
    print(f"QR PNG:    {qr_path}")

    listing = coerce_listing(listing_raw, brand, listing_url)
    listing["qr_url"] = qr_url

    # Also copy the QR into the output dir for debug
    debug_qr = print_out / "qr.png"
    debug_qr.write_bytes(qr_path.read_bytes())

    # 4. Render each template → write rendered HTML to .work/, then PDF to print/
    rendered_paths = []
    for key, tpl_path in TEMPLATES.items():
        rendered_html = render_template(str(tpl_path), brand, listing)
        rendered_path = work_dir / f"{key}.rendered.html"
        rendered_path.write_text(rendered_html, encoding="utf-8")
        rendered_paths.append((key, rendered_path))

    # 5. Run Playwright once, render all 3 PDFs in sequence
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            for key, rendered_path in rendered_paths:
                pdf_path = print_out / OUTPUT_NAMES[key]
                print(f"Rendering {key} → {pdf_path.name} ...")
                await render_pdf(
                    rendered_path,
                    pdf_path,
                    PAGE_FORMATS[key],
                    browser,
                )
                size_kb = pdf_path.stat().st_size // 1024
                print(f"  OK: {pdf_path.name} ({size_kb} KB)")
        finally:
            await browser.close()

    print("\n=== Print kit complete ===")
    print(f"Output dir: {print_out}")
    print(f"  · {OUTPUT_NAMES['brochure']}")
    print(f"  · {OUTPUT_NAMES['one-sheet']}")
    print(f"  · {OUTPUT_NAMES['postcard']}")
    print(f"  · qr.png (debug)")


def main():
    parser = argparse.ArgumentParser(description="Render Listing Kit print PDFs")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug (default: _default)")
    parser.add_argument("--slug", required=True, help="URL/folder slug for this listing")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--base-url", default=None, help="Override the QR target URL")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
