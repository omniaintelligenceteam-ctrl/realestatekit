"""
Social Image Renderer — produces 5 listing images sized for FB / IG / Reels / LinkedIn.

Uses Pillow + the Cormorant-SemiBold.ttf already bundled in assets/. Hero photo
loaded from a local file:// path or remote URL (Zillow CDN, picsum, etc).

Output PNGs in <out>/social/:
  - fb-feed-1080.png       (1080×1080 — Facebook feed square)
  - ig-feed-1080.png       (1080×1080 — Instagram feed square)
  - ig-story-1080x1920.png (1080×1920 — Instagram Story vertical)
  - reels-cover-1080x1920.png (1080×1920 — Reels cover vertical)
  - linkedin-1200x627.png  (1200×627 — LinkedIn landscape)

Usage:
    python render_social_images.py \
      --listing path/to/listing.json \
      --agent kim-smith \
      --out C:/Users/.../Downloads/<slug>-kit/

Brand profile drives the gold accent color via primary_color / accent_color.
Tier-gated: per-listing tier shows small "via getoios.com" tag in the corner;
monthly tier shows nothing.
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Force UTF-8 stdout on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import urllib.request
import urllib.parse

# Local imports — pull brand profile loader from print/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "print"))
from brand_profile import load_brand_profile  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS = SKILL_ROOT / "assets"

# Font lookup: prefer the bundled Cormorant Garamond TTF if it's a valid TrueType file
# (the assets/Cormorant-SemiBold.ttf shipped with the repo has historically been
# corrupted — actual HTML downloaded under a .ttf extension). When that's invalid,
# fall back to Windows Cambria — a classic Microsoft serif on every Windows machine
# since Vista. Looks close to Cormorant Garamond and produces print-quality overlays
# without any network dependency.
def _resolve_font_path() -> Path:
    candidates = [
        ASSETS / "Cormorant-SemiBold.ttf",
        Path("C:/Windows/Fonts/cambria.ttc"),  # Cambria — Windows built-in
        Path("C:/Windows/Fonts/georgia.ttf"),  # Georgia — fallback if Cambria missing
        Path("C:/Windows/Fonts/times.ttf"),    # Times New Roman — last resort
    ]
    for p in candidates:
        if not p.exists():
            continue
        # Probe that Pillow can actually parse it — the bundled TTF was HTML once
        try:
            ImageFont.truetype(str(p), 12)
            return p
        except (OSError, ValueError):
            continue
    raise SystemExit(
        "No usable font found. Tried: " + ", ".join(str(p) for p in candidates)
    )


FONT_PATH = _resolve_font_path()

OUTPUT_FORMATS = {
    "fb-feed-1080":          {"size": (1080, 1080), "layout": "square"},
    "ig-feed-1080":          {"size": (1080, 1080), "layout": "square"},
    "ig-story-1080x1920":    {"size": (1080, 1920), "layout": "story"},
    "reels-cover-1080x1920": {"size": (1080, 1920), "layout": "reels-cover"},
}


def load_image(src: str) -> Image.Image:
    """Load an image from a file path, file:// URL, or http(s):// URL."""
    if src.startswith(("http://", "https://")):
        with urllib.request.urlopen(src, timeout=30) as resp:
            data = resp.read()
        return Image.open(io.BytesIO(data)).convert("RGB")
    if src.startswith("file://"):
        path = urllib.parse.unquote(src[7:])
        # Strip leading slash on Windows: file:///C:/... -> C:/...
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        return Image.open(path).convert("RGB")
    return Image.open(src).convert("RGB")


def crop_to_aspect(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop the image to the target aspect ratio, then resize."""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # Source is wider — crop sides
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    elif src_ratio < target_ratio:
        # Source is taller — crop top/bottom
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 3  # bias upward — shows more of the building, less foreground
        img = img.crop((0, top, src_w, top + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def apply_filter(img: Image.Image) -> Image.Image:
    """Apply the same contrast/saturation lift used on the landing page (1.04 / 1.06)."""
    from PIL import ImageEnhance
    img = ImageEnhance.Contrast(img).enhance(1.04)
    img = ImageEnhance.Color(img).enhance(1.06)
    return img


def add_gradient_overlay(img: Image.Image, layout: str) -> Image.Image:
    """Add a darkening gradient at the bottom (or top+bottom for story) for text legibility."""
    w, h = img.size
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = gradient.load()

    if layout == "story":
        # Story: dark top + dark bottom, lighter middle
        for y in range(h):
            t_top = max(0, 1 - y / (h * 0.20))      # 0..1 over top 20%
            t_bot = max(0, (y - h * 0.65) / (h * 0.35))  # 0..1 over bottom 35%
            alpha = int(180 * t_top + 200 * t_bot)
            for x in range(w):
                px[x, y] = (0, 0, 0, alpha)
    elif layout == "reels-cover":
        # Reels: heavier bottom darkening for big "TAP TO TOUR" CTA
        for y in range(h):
            t = max(0, (y - h * 0.55) / (h * 0.45))
            alpha = int(220 * t)
            # Plus a touch of darkening at top for any header text
            if y < h * 0.15:
                alpha += int(120 * (1 - y / (h * 0.15)))
            for x in range(w):
                px[x, y] = (0, 0, 0, min(alpha, 255))
    elif layout in ("square", "landscape"):
        # Square/landscape: gradient bottom 40%
        for y in range(h):
            t = max(0, (y - h * 0.50) / (h * 0.50))
            alpha = int(195 * (t ** 1.6))
            for x in range(w):
                px[x, y] = (0, 0, 0, alpha)

    return Image.alpha_composite(img.convert("RGBA"), gradient)


def font_at(size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size_px)


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple:
    """Return (width, height) for a string at the given font."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_text_with_shadow(draw, xy, text, font, fill="#ffffff", shadow="#00000099"):
    """Draw text with a subtle drop shadow for legibility on photos."""
    x, y = xy
    # Shadow offset 2px + 4px blurred-feel approximation
    draw.text((x + 2, y + 3), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def render_square(img, listing, brand, fmt_key):
    """Square layout — FB feed / IG feed. Hero photo + price+address overlay bottom."""
    img = apply_filter(img)
    img = add_gradient_overlay(img, "square")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    accent = brand.get("accent_color", "#a07f3f")

    # Bottom-left: street + city
    street = listing.get("street_address", "")
    city = f"{listing.get('city', '')}, {listing.get('state', '')}"
    price = listing.get("price_formatted", "")

    street_font = font_at(60)
    city_font = font_at(34)
    price_font = font_at(72)

    margin = 56
    # Price right-aligned bottom
    pw, ph = text_size(draw, price, price_font)
    draw_text_with_shadow(draw, (w - margin - pw, h - margin - ph), price, price_font)

    # Address bottom-left
    sw, sh = text_size(draw, street, street_font)
    draw_text_with_shadow(draw, (margin, h - margin - sh), street, street_font)
    cw, ch = text_size(draw, city, city_font)
    draw_text_with_shadow(draw, (margin, h - margin - sh - ch - 4), city, city_font, fill="#e8e2d4")

    # Top-left: brand mark
    if brand.get("brokerage"):
        brand_font = font_at(26)
        bw, bh = text_size(draw, brand["brokerage"].upper(), brand_font)
        draw_text_with_shadow(draw, (margin, margin), brand["brokerage"].upper(), brand_font, fill="#ffffff")

    # Top-right: thin accent rule + "JUST LISTED" eyebrow
    eyebrow = "JUST LISTED"
    eb_font = font_at(22)
    ew, eh = text_size(draw, eyebrow, eb_font)
    draw.rectangle([w - margin - ew - 24, margin + 12, w - margin, margin + 14], fill=accent)
    draw_text_with_shadow(draw, (w - margin - ew, margin + 24), eyebrow, eb_font, fill=accent)

    # Per-listing footer mark (bottom-center, small)
    if not brand.get("is_white_label") and brand.get("footer_tagline"):
        tag_font = font_at(18)
        tag = brand["footer_tagline"]
        tw, th = text_size(draw, tag, tag_font)
        draw.text(((w - tw) // 2, h - 26), tag, font=tag_font, fill=(255, 255, 255, 140))

    return img.convert("RGB")


def render_story(img, listing, brand, fmt_key):
    """IG Story layout 1080×1920 — vertical, brand top, address+price bottom-third, swipe cue."""
    img = apply_filter(img)
    img = add_gradient_overlay(img, "story")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    accent = brand.get("accent_color", "#a07f3f")
    margin = 64

    # TOP: brokerage all-caps
    if brand.get("brokerage"):
        brand_font = font_at(32)
        bk = brand["brokerage"].upper()
        bw, bh = text_size(draw, bk, brand_font)
        draw_text_with_shadow(draw, ((w - bw) // 2, 80), bk, brand_font)

    # Eyebrow under brand
    eb_font = font_at(28)
    eb = "A NEW LISTING IN " + (listing.get("city", "") or "").upper()
    ew, eh = text_size(draw, eb, eb_font)
    draw_text_with_shadow(draw, ((w - ew) // 2, 80 + 50), eb, eb_font, fill=accent)

    # MIDDLE-BOTTOM: street name big, city smaller, price prominent
    street = listing.get("street_address", "")
    city = f"{listing.get('city', '')}, {listing.get('state', '')}"
    price = listing.get("price_formatted", "")

    street_font = font_at(78)
    city_font = font_at(38)
    price_font = font_at(96)

    # Position from bottom up: swipe cue → price → city → street
    # Swipe cue
    swipe_font = font_at(26)
    swipe_text = "TAP FOR FULL TOUR + VIDEO"
    swipe_w, swipe_h = text_size(draw, swipe_text, swipe_font)
    swipe_y = h - 140
    draw.rectangle([(w - swipe_w) // 2 - 28, swipe_y + swipe_h + 18, (w + swipe_w) // 2 + 28, swipe_y + swipe_h + 22], fill=accent)
    draw_text_with_shadow(draw, ((w - swipe_w) // 2, swipe_y), swipe_text, swipe_font, fill="#ffffff")

    # Price
    pw, ph = text_size(draw, price, price_font)
    price_y = swipe_y - 60 - ph
    draw_text_with_shadow(draw, ((w - pw) // 2, price_y), price, price_font)

    # City
    cw, ch = text_size(draw, city, city_font)
    city_y = price_y - 18 - ch
    draw_text_with_shadow(draw, ((w - cw) // 2, city_y), city, city_font, fill="#e8e2d4")

    # Street
    sw, sh = text_size(draw, street, street_font)
    street_y = city_y - 6 - sh
    draw_text_with_shadow(draw, ((w - sw) // 2, street_y), street, street_font)

    # Per-listing footer
    if not brand.get("is_white_label") and brand.get("footer_tagline"):
        tag_font = font_at(20)
        tag = brand["footer_tagline"]
        tw, th = text_size(draw, tag, tag_font)
        draw.text(((w - tw) // 2, h - 50), tag, font=tag_font, fill=(255, 255, 255, 130))

    return img.convert("RGB")


def render_reels_cover(img, listing, brand, fmt_key):
    """Reels cover 1080×1920 — vertical with big 'TAP TO TOUR' CTA bottom."""
    img = apply_filter(img)
    img = add_gradient_overlay(img, "reels-cover")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    accent = brand.get("accent_color", "#a07f3f")
    margin = 64

    # TOP: brokerage tag
    if brand.get("brokerage"):
        brand_font = font_at(28)
        bk = brand["brokerage"].upper()
        bw, bh = text_size(draw, bk, brand_font)
        draw_text_with_shadow(draw, ((w - bw) // 2, 90), bk, brand_font)

    # MIDDLE: address takes center stage with price below
    street = listing.get("street_address", "")
    city = f"{listing.get('city', '')}, {listing.get('state', '')}"
    price = listing.get("price_formatted", "")

    street_font = font_at(82)
    city_font = font_at(36)
    price_font = font_at(56)

    # Pre-measure for vertical centering of the address block
    sw, sh = text_size(draw, street, street_font)
    cw, ch = text_size(draw, city, city_font)
    pw, ph = text_size(draw, price, price_font)
    block_h = sh + 12 + ch + 28 + ph

    block_top = int(h * 0.42) - block_h // 2

    draw_text_with_shadow(draw, ((w - sw) // 2, block_top), street, street_font)
    draw_text_with_shadow(draw, ((w - cw) // 2, block_top + sh + 12), city, city_font, fill="#e8e2d4")
    draw_text_with_shadow(draw, ((w - pw) // 2, block_top + sh + 12 + ch + 28), price, price_font, fill=accent)

    # BOTTOM: big "TAP TO TOUR" CTA
    cta_font = font_at(64)
    cta_text = "TAP TO TOUR"
    cw2, ch2 = text_size(draw, cta_text, cta_font)
    cta_y = h - 220
    draw_text_with_shadow(draw, ((w - cw2) // 2, cta_y), cta_text, cta_font)

    sub_font = font_at(28)
    sub_text = "Full virtual walkthrough + video"
    sbw, sbh = text_size(draw, sub_text, sub_font)
    draw_text_with_shadow(draw, ((w - sbw) // 2, cta_y + ch2 + 14), sub_text, sub_font, fill="#e8e2d4")

    # Triangle pointer ▼
    tri_font = font_at(34)
    tri_text = "▼"
    tw, th = text_size(draw, tri_text, tri_font)
    draw_text_with_shadow(draw, ((w - tw) // 2, cta_y + ch2 + 14 + sbh + 18), tri_text, tri_font, fill=accent)

    if not brand.get("is_white_label") and brand.get("footer_tagline"):
        tag_font = font_at(20)
        tag = brand["footer_tagline"]
        tw, th = text_size(draw, tag, tag_font)
        draw.text(((w - tw) // 2, h - 50), tag, font=tag_font, fill=(255, 255, 255, 130))

    return img.convert("RGB")


def render_landscape(img, listing, brand, fmt_key):
    """LinkedIn 1200×627 — landscape hero with overlay."""
    img = apply_filter(img)
    img = add_gradient_overlay(img, "landscape")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    accent = brand.get("accent_color", "#a07f3f")
    margin = 56

    street = listing.get("street_address", "")
    city = f"{listing.get('city', '')}, {listing.get('state', '')}"
    price = listing.get("price_formatted", "")

    street_font = font_at(48)
    city_font = font_at(28)
    price_font = font_at(54)

    # Bottom-left: address block
    sw, sh = text_size(draw, street, street_font)
    cw, ch = text_size(draw, city, city_font)

    draw_text_with_shadow(draw, (margin, h - margin - sh), street, street_font)
    draw_text_with_shadow(draw, (margin, h - margin - sh - ch - 4), city, city_font, fill="#e8e2d4")

    # Bottom-right: price
    pw, ph = text_size(draw, price, price_font)
    draw_text_with_shadow(draw, (w - margin - pw, h - margin - ph), price, price_font, fill=accent)

    # Top-left: brokerage
    if brand.get("brokerage"):
        brand_font = font_at(22)
        bk = brand["brokerage"].upper()
        draw_text_with_shadow(draw, (margin, margin), bk, brand_font)

    # Top-right: eyebrow rule
    eb_font = font_at(20)
    eb = "A NEW LISTING"
    ew, eh = text_size(draw, eb, eb_font)
    draw.rectangle([w - margin - ew - 20, margin + 8, w - margin, margin + 10], fill=accent)
    draw_text_with_shadow(draw, (w - margin - ew, margin + 18), eb, eb_font, fill=accent)

    if not brand.get("is_white_label") and brand.get("footer_tagline"):
        tag_font = font_at(16)
        tag = brand["footer_tagline"]
        tw, th = text_size(draw, tag, tag_font)
        draw.text(((w - tw) // 2, h - 22), tag, font=tag_font, fill=(255, 255, 255, 130))

    return img.convert("RGB")


RENDERERS = {
    "square": render_square,
    "story": render_story,
    "reels-cover": render_reels_cover,
    "landscape": render_landscape,
}


def main():
    parser = argparse.ArgumentParser(description="Render Listing Kit social images")
    parser.add_argument("--listing", required=True, help="Path to listing.json")
    parser.add_argument("--agent", default=None, help="Brand profile slug (default: _default)")
    parser.add_argument("--out", required=True, help="Output directory (will write to <out>/social/)")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    social_out = out_dir / "social"
    social_out.mkdir(parents=True, exist_ok=True)

    # Load brand profile
    brand = load_brand_profile(args.agent)
    print(f"Brand profile: {brand.get('agent_slug')!r} (tier={brand.get('tier')!r})")

    # Load listing
    with open(args.listing, "r", encoding="utf-8") as f:
        listing = json.load(f)

    photos = listing.get("photos", []) or []
    if not photos:
        raise SystemExit("Listing has no photos[] — cannot render social images.")
    hero_url = photos[0]
    print(f"Loading hero photo: {hero_url}")
    hero_img = load_image(hero_url)
    print(f"  Source size: {hero_img.size}")

    # Verify font is available
    if not FONT_PATH.exists():
        raise SystemExit(f"Font missing: {FONT_PATH}. Required for social text overlays.")

    for key, spec in OUTPUT_FORMATS.items():
        target_w, target_h = spec["size"]
        layout = spec["layout"]
        cropped = crop_to_aspect(hero_img.copy(), target_w, target_h)
        rendered = RENDERERS[layout](cropped, listing, brand, key)
        out_path = social_out / f"{key}.png"
        rendered.save(out_path, "PNG", optimize=True)
        size_kb = out_path.stat().st_size // 1024
        print(f"  OK: {key}.png ({target_w}x{target_h}, {size_kb} KB)")

    print(f"\n=== Social pack complete ===")
    print(f"Output dir: {social_out}")
    for key in OUTPUT_FORMATS:
        print(f"  · {key}.png")


if __name__ == "__main__":
    main()
