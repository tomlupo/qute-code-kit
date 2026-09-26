# Pipeline notes

## One function of time

`reel.js` exposes `Reel.init()` (fonts, precomputed geometry; returns the cue sheet),
`Reel.render(ctx, t, tf)` and `Reel.post(src, dst, tf)`. The harness
(`assets/render.html`, served by `render.py` next to the project) owns the canvases.
Because a frame depends on nothing but time, frames render in any order, in parallel
workers, and a single frame can be re-rendered to check it.

## Motion blur

The harness renders `sub` sub-frames at
`t = tf + ((s + 0.5) / sub − 0.5) × shutter / FPS` and keeps a running average
(`globalAlpha = 1 / (s + 1)`). `shutter = 0.5` is a film camera's 180° shutter: fast
moves smear, held type stays sharp. Grain, bloom and the vignette run once in `post`,
after the average. If they ran per sub-frame, the averaging would erase the grain.

**`t` versus `tf`.** Sub-frames straddle the frame's time. Anything discrete (which
card shows, a count, the scene index, HUD text) must switch on `tf`, or one frame
blends two cards. Continuous motion uses `t`.

`sheets` renders with `sub = 1` (fast, sharp, good for layout); `frames` with 8.

## Costs, measured on an 8-core box at 1920×1080

| job | time |
|---|---|
| `render.py check`, 1,065 frames of 56 s at one sample | about 50 s |
| review sheets, 64 frames | 5–6 s |
| 900 frames × 8 sub-frames | 42–69 s |
| 3,375 frames (56 s) × 8 sub-frames | 134–146 s |
| encode 56 s, master and share copy | about 3 min |

PNG frames take 1.3–2.3 MB each, so a 56-second film needs about 5 GB while it
renders. Delete `frames/` after encoding when space is tight.

## Headless canvas specifics

- **Fonts.** `document.fonts.load(font, sample)` loads only the faces whose
  `unicode-range` covers `sample`. The default sample `" "` loads the latin face alone,
  and ł, ą or ß then fall back to another font without an error. The template passes a
  sample with diacritics; `fonts.py` keeps latin-ext for the same reason.
- `ctx.letterSpacing` is part of the canvas state and sticks; set it with every font
  (`setFont` does).
- `ctx.filter = 'blur()'` works in software rendering. `shadowBlur` is expensive: one
  glowing ring is fine, a thousand shadowed dots is not.
- Batch primitives of one colour into a single path and fill once; that is how several
  thousand particles stay cheap.
- Per-pixel effects (metaballs, fields) belong in an ImageData at ½ or ¼ resolution,
  drawn scaled up with smoothing.
- Transitions draw two scenes in one frame, so a scene must have no side effects.
  Wrap each in save/restore and reset the transform before the HUD.
- A scene drawn outside its own time (a transition runs it early or late) must still
  draw something sensible: clamp its timelines rather than assume `lt ≥ 0`.

## Checks that fail loudly

- `render.py check` draws every quarter second and two seconds around every cut at one
  sample and exits non-zero on the first script error; `make.sh` runs it before the
  sheets and before the full render.
- `render.py` exits non-zero on any page error or console error (a missing
  `fonts.css` is a 404, not a warning) and on any missing frame.
- `encode.py` decodes both outputs and compares their frame counts with `cues.json`,
  and fails when even the last CRF cannot bring the share copy under `--max-mb`.
- `synth.py` exits non-zero when a registered silence window is louder than −100 dB.

## Encoding

H.264 High, yuv420p, bt709 primaries, transfer and matrix tagged, `+faststart`. The
master is CRF 14. The share copy climbs a CRF ladder (14, 16, 18…) until it fits
`--max-mb`.

| film | size |
|---|---|
| 15 s, flat-colour brand film, CRF 14 | 13.5 MB |
| 56 s, same film re-timed, CRF 14 / CRF 16 | 39 MiB / 26 MiB |
| 15 s, grain-heavy showreel, CRF 14 | 48.7 MB (needed 2-pass at 6.4 Mbps to fit 15 MB) |

Grain is the expensive part. Keep `GRAIN ≤ 0.04` when the copy must be small.

## Delivering

Send `NAME.mp4` as a file. When a page presents the film (chapters, a cue sheet), a
video under 15 MB can be published next to it. What may be published at all is in
`craft.md`, under "Honesty on screen".
