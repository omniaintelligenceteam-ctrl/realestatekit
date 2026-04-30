import subprocess, os, sys

BUILD = r"C:\Users\default.DESKTOP-ON29PVN\Downloads\148-pheasant-run-paducah-ky-build"
FONT = r"C\:/Users/default.DESKTOP-ON29PVN/.claude/skills/zillow-clone/assets/Cormorant-SemiBold.ttf"
MUSIC = r"C:/Users/default.DESKTOP-ON29PVN/.claude/skills/zillow-clone/assets/music-bed-piano.mp3"
NARR = os.path.join(BUILD, "narration.mp3")

PHRASES = [
    "A private courtyard",
    "in west Paducah",
    "Twelve-foot ceilings",
    "A stone fireplace",
    "Amish cabinetry. Granite island.",
    "Dining opens to kitchen.",
    "Primary suite.",
    "Rain shower. Jetted tub.",
    "Nearly twenty-four hundred feet.",
    "Exposed wood beams.",
    "Three bedrooms.",
    "Listed at four forty-nine.",
]

N = 12
CLIP_DUR = 3.5
FADE_DUR = 0.5
TOTAL = N * CLIP_DUR - (N - 1) * FADE_DUR  # 36.5s

# Build xfade chain: [0:v][1:v]xfade...offset=3.0[vx1]; [vx1][2:v]xfade...offset=6.0[vx2]; ...
def build_xfade(suffix):
    parts = []
    for i in range(1, N):
        offset = i * (CLIP_DUR - FADE_DUR)
        if i == 1:
            a, b = "[0:v]", f"[{i}:v]"
        else:
            a = f"[vx{i-1}]"
            b = f"[{i}:v]"
        label = f"[vx{i}]"
        parts.append(f"{a}{b}xfade=transition=fade:duration={FADE_DUR}:offset={offset}{label}")
    return ";".join(parts)

# Build drawtext chain: one drawtext per phrase, timed to clip window
def build_drawtext(fontsize, y_pos):
    parts = []
    for i, phrase in enumerate(PHRASES):
        start = i * (CLIP_DUR - FADE_DUR)
        end = start + CLIP_DUR + 0.3
        # Escape single quotes for drawtext: ' -> '\''
        esc = phrase.replace("'", r"'\''")
        dt = (
            f"drawtext=fontfile='{FONT}'"
            f":text='{esc}'"
            f":fontsize={fontsize}"
            f":fontcolor=white"
            f":borderw=2"
            f":bordercolor=black@0.7"
            f":x=(w-text_w)/2"
            f":y={y_pos}"
            f":enable='between(t\\,{start}\\,{end})'"
        )
        parts.append(dt)
    return ",".join(parts)

# Variants: (clip_suffix, fontsize, y_expr, output_name)
VARIANTS = [
    ("",     42, "h-180", "hero.mp4"),
    ("-sq",  38, "h-150", "hero-sq.mp4"),
    ("-vt",  46, "h-280", "hero-vt.mp4"),
]

for suffix, fontsize, y_pos, outname in VARIANTS:
    print(f"\n=== Assembling {outname} ===")
    inputs = []
    for i in range(1, N + 1):
        clip = os.path.join(BUILD, f"c{i:02d}{suffix}.mp4")
        inputs += ["-i", clip]
    inputs += ["-i", NARR, "-i", MUSIC]

    xfade = build_xfade(suffix)
    captions = build_drawtext(fontsize, y_pos)

    # Audio: narration + music bed mixed
    audio_filter = (
        f"[{N}:a]apad,atrim=0:{TOTAL},asetpts=PTS-STARTPTS,volume=1.0[narr];"
        f"[{N+1}:a]volume=0.18,atrim=0:{TOTAL},"
        f"afade=t=in:st=0:d=1.5,afade=t=out:st=34.5:d=2.0[mus];"
        f"[narr][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]"
    )

    filter_complex = f"{xfade};[vx{N-1}]copy[vfinal];{audio_filter}"

    outpath = os.path.join(BUILD, outname)
    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filter_complex,
            "-map", "[vfinal]",
            "-map", "[a]",
            "-t", str(TOTAL),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "slow",
            "-crf", "19",
            "-r", "24",
            "-maxrate", "6500k",
            "-bufsize", "13000k",
            "-c:a", "aac",
            "-b:a", "192k",
            outpath,
        ]
    )

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        size_mb = os.path.getsize(outpath) / 1024 / 1024
        print(f"  OK: {outname} ({size_mb:.1f} MB)")
    else:
        print(f"  FAILED: {result.stderr[-1000:]}")
        sys.exit(1)

print("\n=== All 3 variants complete ===")
