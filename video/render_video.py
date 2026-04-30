"""
Video pipeline — produce 3 aspect ratios (16:9, 1:1, 9:16) from a list of selected
photos + a narration script via FFmpeg + ElevenLabs.

Wraps the existing `assemble.py` (the FFmpeg orchestrator from the 148 build) plus
adds the upstream Ken Burns clip generation and ElevenLabs narration steps.

Usage:
    python video/render_video.py \
      --photos /path/to/photo1.jpg /path/to/photo2.jpg ... \
      --narration-text narration.txt \
      --slug 148-pheasant-run-paducah-ky \
      --out ~/Downloads/<slug>-kit/video/

Inputs:
  --photos    : 8–12 selected photos in story-arc order (caller picks them)
  --narration-text : path to a .txt file with the narration script (or pass --skip-narration)
  --slug      : URL slug for output filenames
  --out       : output directory

Outputs in <out>/:
  - hero.mp4         (1920×1080, 16:9 — for landing page)
  - hero-sq.mp4      (1080×1080, 1:1 — for FB/IG feed)
  - hero-vt.mp4      (1080×1920, 9:16 — for Reels/Stories)
  - narration.mp3    (ElevenLabs output, mixed with music bed)

Dependencies (assumed installed):
  - ffmpeg on PATH
  - ELEVENLABS_API_KEY env var (for narration; skip with --skip-narration)
  - python: requests (for ElevenLabs HTTP)

Status:
  Phase 1 — clip generation + assembly (this script). Phase 2 will integrate with
  tier1.py / tier2.py automatically. For now, run this manually after the photos
  + narration script are picked.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS = SKILL_ROOT / "assets"
MUSIC_BED = ASSETS / "music-bed-piano.mp3"

# Per-clip duration. 11 clips × 3.0s = 33s base; with xfade overlap = ~36s total
CLIP_DUR = 3.0
FADE_DUR = 0.5

ASPECT_SIZES = {
    "":     {"w": 1920, "h": 1080},  # 16:9 main
    "-sq":  {"w": 1080, "h": 1080},  # 1:1 square
    "-vt":  {"w": 1080, "h": 1920},  # 9:16 vertical
}


def run(cmd: list, **kwargs):
    """Run a subprocess command, surfacing output on failure."""
    print(f"  $ {' '.join(str(c) for c in cmd[:8])}{'...' if len(cmd) > 8 else ''}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kwargs)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed (exit {result.returncode})")
    return result


def render_kenburns_clip(photo: Path, out_path: Path, w: int, h: int, dur: float = CLIP_DUR):
    """Generate a Ken Burns clip from a still photo at the given resolution."""
    # 24 fps, slow zoom from 1.0 → 1.06 over `dur` seconds
    frames = int(dur * 24)
    zoom_per_frame = 0.06 / frames
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(photo),
        "-vf",
        f"scale=8000:-1,zoompan=z='1.0+{zoom_per_frame}*on':"
        f"d={frames}:s={w}x{h}:fps=24,format=yuv420p",
        "-t", str(dur),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    run(cmd)


def render_clips_for_aspect(photos: list, work_dir: Path, suffix: str, w: int, h: int):
    """Render Ken Burns clips for a single aspect ratio."""
    work_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, photo in enumerate(photos, 1):
        out = work_dir / f"c{i:02d}{suffix}.mp4"
        if out.exists():
            print(f"  cached: {out.name}")
        else:
            print(f"  rendering {out.name} ({w}x{h})...")
            render_kenburns_clip(photo, out, w, h)
        paths.append(out)
    return paths


def synth_narration(text: str, out_path: Path, voice_id: str = "JBFqnCBsd6RMkjVDRZzb"):
    """Call ElevenLabs to synthesize narration. Voice = George (free-tier compatible)."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit(
            "ELEVENLABS_API_KEY not set. Get one from https://elevenlabs.io/app/settings "
            "and run `set ELEVENLABS_API_KEY=<key>`. Or pass --skip-narration."
        )
    try:
        import requests
    except ImportError:
        raise SystemExit("Install requests: pip install requests")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.75},
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"}
    print(f"  ElevenLabs synth ({len(text)} chars)...")
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    print(f"  OK: {out_path.name} ({out_path.stat().st_size // 1024} KB)")


def assemble_aspect(clips: list, narration_path: Path, suffix: str, out_path: Path,
                     music_bed: Path = MUSIC_BED):
    """Stitch clips with xfade transitions, mix narration + music bed."""
    n = len(clips)

    # Build the FFmpeg filter graph for xfade chain
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]
    if narration_path and narration_path.exists():
        inputs += ["-i", str(narration_path)]
    if music_bed and music_bed.exists():
        inputs += ["-i", str(music_bed)]

    # xfade chain: [0:v][1:v]xfade=offset=2.5:duration=0.5[v01]; etc.
    xfade_parts = []
    for i in range(n - 1):
        prev = f"[{i}:v]" if i == 0 else f"[vx{i}]"
        offset = (i + 1) * (CLIP_DUR - FADE_DUR)
        xfade_parts.append(
            f"{prev}[{i + 1}:v]xfade=transition=fade:offset={offset:.3f}:"
            f"duration={FADE_DUR}[vx{i + 1}]"
        )
    xfade = ";".join(xfade_parts)

    has_narration = narration_path and narration_path.exists()
    has_music = music_bed and music_bed.exists()
    audio_idx_narr = n if has_narration else None
    audio_idx_music = n + (1 if has_narration else 0) if has_music else None

    audio_filter = ""
    if has_narration and has_music:
        audio_filter = (
            f"[{audio_idx_narr}:a]volume=1.0[narr];"
            f"[{audio_idx_music}:a]volume=0.18,afade=t=in:d=1.5,"
            f"afade=t=out:st=33.0:d=2.0[bed];"
            f"[narr][bed]amix=inputs=2:normalize=0:duration=longest[afinal]"
        )
    elif has_narration:
        audio_filter = f"[{audio_idx_narr}:a]volume=1.0[afinal]"
    elif has_music:
        audio_filter = f"[{audio_idx_music}:a]volume=0.4,afade=t=in:d=1.0[afinal]"

    fc = f"{xfade};[vx{n - 1}]copy[vfinal]"
    if audio_filter:
        fc += f";{audio_filter}"

    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + [
        "-filter_complex", fc,
        "-map", "[vfinal]",
    ]
    if audio_filter:
        cmd += ["-map", "[afinal]"]
    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_path),
    ]
    run(cmd)
    print(f"  OK: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")


def main():
    parser = argparse.ArgumentParser(description="Render 3-aspect listing video")
    parser.add_argument("--photos", nargs="+", required=True, help="8-12 photos in story-arc order")
    parser.add_argument("--narration-text", default=None, help="Path to .txt file with narration")
    parser.add_argument("--slug", required=True, help="URL slug for output filenames")
    parser.add_argument("--out", required=True, help="Output dir (e.g. <kit>/video/)")
    parser.add_argument("--skip-narration", action="store_true", help="No ElevenLabs call (silent video)")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = out_dir / ".work"
    work_dir.mkdir(exist_ok=True)

    photos = [Path(p).resolve() for p in args.photos]
    for p in photos:
        if not p.exists():
            raise SystemExit(f"Photo missing: {p}")
    print(f"Video pipeline — {len(photos)} photos")

    # 1. Render Ken Burns clips for each aspect
    print(f"\n--- Ken Burns clips (3 aspects × {len(photos)} photos = {3 * len(photos)} clips) ---")
    clips_by_aspect = {}
    for suffix, dims in ASPECT_SIZES.items():
        print(f"  Aspect {suffix or '16:9'} ({dims['w']}x{dims['h']}):")
        clips_by_aspect[suffix] = render_clips_for_aspect(
            photos, work_dir, suffix, dims["w"], dims["h"]
        )

    # 2. Narration via ElevenLabs (or skip)
    narration_path = None
    if not args.skip_narration and args.narration_text:
        text_path = Path(args.narration_text)
        if not text_path.exists():
            raise SystemExit(f"Narration text not found: {text_path}")
        narration_path = work_dir / "narration.mp3"
        print(f"\n--- Narration ---")
        synth_narration(text_path.read_text(encoding="utf-8"), narration_path)
    else:
        print(f"\n--- Narration: skipped ---")

    # 3. Assemble each aspect
    print(f"\n--- Assembling 3 aspect ratios ---")
    for suffix in ASPECT_SIZES:
        out_name = f"hero{suffix}.mp4"
        out_path = out_dir / out_name
        print(f"  {out_name}:")
        assemble_aspect(clips_by_aspect[suffix], narration_path, suffix, out_path)

    print(f"\n=== Video complete ===")
    print(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
