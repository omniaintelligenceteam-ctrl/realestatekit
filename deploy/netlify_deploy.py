"""
Netlify deploy helper — zip a directory, upload, poll for ready, return the live URL.

Two modes:
  1. **Per-listing site** (per-listing tier): creates a new Netlify site named
     `<slug>-kit.netlify.app` (or `<slug>.netlify.app` for Tier 1 digital-only).
  2. **Custom domain site** (monthly tier): deploys to an existing Netlify site
     that's already configured with the agent's wildcard domain.

Auth:
  Set NETLIFY_TOKEN env var (Personal access token from
  https://app.netlify.com/user/applications#personal-access-tokens).

Usage:
    python deploy/netlify_deploy.py \
      --dir ~/Downloads/<slug>-kit/ \
      --slug <slug>-kit \
      --tier per-listing

    python deploy/netlify_deploy.py \
      --dir ~/Downloads/<slug>-kit/ \
      --site-id 4432b2e8-1cb6-4914-8f8d-f08bbc203622 \
      --tier monthly
"""

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

API = "https://api.netlify.com/api/v1"


def get_token() -> str:
    tok = os.environ.get("NETLIFY_TOKEN") or os.environ.get("NETLIFY_AUTH_TOKEN")
    if not tok:
        raise SystemExit(
            "NETLIFY_TOKEN not set. Get one from "
            "https://app.netlify.com/user/applications#personal-access-tokens "
            "and run `set NETLIFY_TOKEN=<token>` (Windows) or `export NETLIFY_TOKEN=<token>` (Unix)."
        )
    return tok


def api_request(method: str, path: str, token: str, body: bytes = None,
                content_type: str = "application/json") -> dict:
    url = f"{API}{path}"
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            if not data:
                return {}
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Netlify API {e.code} {method} {url}: {body}")


def make_zip(src_dir: Path) -> bytes:
    """Build a zip in memory of the directory contents (flat layout from src_dir root)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src_dir.rglob("*")):
            if path.is_file():
                # Skip our scratch files
                if any(part in (".work", "__pycache__") for part in path.parts):
                    continue
                arcname = path.relative_to(src_dir).as_posix()
                zf.write(path, arcname)
    return buf.getvalue()


def find_or_create_site(token: str, slug: str) -> dict:
    """Look up an existing site by name, or create a new one."""
    name = slug.lower().replace("_", "-")
    sites = api_request("GET", f"/sites?name={name}", token)
    if isinstance(sites, list) and sites:
        for s in sites:
            if s.get("name") == name:
                print(f"  Using existing Netlify site: {s.get('ssl_url') or s.get('url')}")
                return s
    # Create
    body = json.dumps({"name": name}).encode("utf-8")
    site = api_request("POST", "/sites", token, body)
    print(f"  Created Netlify site: {site.get('ssl_url') or site.get('url')}")
    return site


def deploy_zip(token: str, site_id: str, zip_bytes: bytes) -> dict:
    """POST a zip to the site's deploys endpoint."""
    deploy = api_request(
        "POST",
        f"/sites/{site_id}/deploys",
        token,
        body=zip_bytes,
        content_type="application/zip",
    )
    return deploy


def poll_until_ready(token: str, site_id: str, deploy_id: str, timeout: int = 180) -> dict:
    """Poll the deploy endpoint until state == 'ready' (or 'error')."""
    start = time.time()
    while time.time() - start < timeout:
        d = api_request("GET", f"/sites/{site_id}/deploys/{deploy_id}", token)
        state = d.get("state")
        print(f"    deploy state: {state}")
        if state == "ready":
            return d
        if state in ("error", "rejected"):
            raise SystemExit(f"Deploy failed: {d}")
        time.sleep(3)
    raise SystemExit(f"Deploy did not become ready within {timeout}s")


def main():
    parser = argparse.ArgumentParser(description="Deploy a Listing Kit directory to Netlify")
    parser.add_argument("--dir", required=True, help="Directory to deploy")
    parser.add_argument("--slug", default=None, help="Site slug (creates <slug>.netlify.app)")
    parser.add_argument("--site-id", default=None, help="Existing Netlify site ID (for monthly tier)")
    parser.add_argument("--tier", default="per-listing", choices=["per-listing", "monthly"])
    args = parser.parse_args()

    if not args.slug and not args.site_id:
        raise SystemExit("Must provide --slug (creates new site) or --site-id (uses existing)")

    src_dir = Path(args.dir).resolve()
    if not src_dir.is_dir():
        raise SystemExit(f"Source dir not found: {src_dir}")

    token = get_token()
    print(f"Netlify deploy")
    print(f"  Source: {src_dir}")

    print(f"  Building zip...")
    zip_bytes = make_zip(src_dir)
    print(f"  Zip size: {len(zip_bytes) // 1024} KB")

    if args.site_id:
        site_id = args.site_id
        print(f"  Target site_id: {site_id}")
    else:
        site = find_or_create_site(token, args.slug)
        site_id = site["id"]

    print(f"  Uploading...")
    deploy = deploy_zip(token, site_id, zip_bytes)
    deploy_id = deploy["id"]
    print(f"  Deploy ID: {deploy_id}")

    print(f"  Polling for ready...")
    final = poll_until_ready(token, site_id, deploy_id)

    live_url = final.get("ssl_url") or final.get("url") or final.get("deploy_ssl_url")
    print(f"\n=== Deploy complete ===")
    print(f"  Live URL: {live_url}")
    print(f"  Site ID: {site_id}")
    return live_url


if __name__ == "__main__":
    main()
