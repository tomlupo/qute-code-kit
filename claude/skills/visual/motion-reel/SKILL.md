---
name: motion-reel
description: Render motion-graphics films as code — showreels, brand and product films, animated data stories, explainer reels, kinetic typography. One JavaScript function of time draws every frame on a canvas, headless Chrome renders it at 1080p60 with real motion blur, a numpy synth scores it to the same cue sheet, ffmpeg encodes it. Use when the user asks for a motion graphics video, a showreel, a reel, a brand film, an animated explainer, a data animation, or "make a 15/30/60-second video". Scaffolds a project, reviews contact sheets before the full render, verifies the encoded file.
argument-hint: "[project dir]"
---

# Motion reel

A film here is a project directory with two sources of truth: `reel.js`, whose
`render(ctx, t)` paints any frame from nothing but the time, and `score.py`, which
places every sound at a time `reel.js` exports. Everything else is generated.

```
reel.js ──render.py (headless Chrome, 8 sub-frames of motion blur)──> frames/*.png ──┐
   └─ cueSheet() ─> cues.json ─> synth.py runs score.py ──────────────> audio.wav ───┴─> encode.py ─> NAME.mp4
```

`SKILL` below means this skill's directory. The scripts carry their dependencies
inline (PEP 723), so `uv run` is the whole setup; Chrome is found on the system or
Playwright's Chromium is installed on first use.

## Workflow

1. **Scaffold.** `uv run SKILL/scripts/new_reel.py DIR` copies `reel.js` and
   `score.py` from `assets/`, downloads the fonts (Inter + DM Mono by default,
   `--family` to change, latin-ext kept for diacritics) and writes `DIR/make.sh`,
   the one command for every later step. The template is a complete 8-scene,
   56-second demo with placeholder copy: it renders before you change anything.

2. **Pin the story and the facts before any pixels.** Read the numbers from their
   source (config, data, a document the user points to) and write them into
   `CONTENT` with the as-of date; the template's numbers are invented placeholders, and
   none may survive into a real film. A number with no source does not go on screen. An
   illustrative value is labelled on screen (`CONTENT.signal.tag`). No performance
   or return claims unless the user supplies them with their source. Copy follows the
   brand's voice and language; `CONTENT.locale` formats every number.

3. **Pace it: each scene's `bars` in `SCENES`.** A scene is choreographed for `nom`
   bars at 128 BPM and stretches or squeezes to the bars it gets. The defaults (3–4 bars a scene, 56 s)
   were set after a 15-second cut of the same content came back "too fast": a scene
   that carries numbers needs about 7 s. All 1s is a 15-second teaser for mood, not
   for reading. Reading rules are in `references/craft.md`.

4. **Look: `THEME`, `FAM`, `GRAIN`, and each scene's `bloom` and `vig`.** Take colours and type from the
   brand. A calm brand gets eased motion, no flashes and no chromatic glitches; a
   showreel may punch. `LIGHT` lists the grounds that take dark type.

5. **Review loop, cheap.** `./make.sh sheets` first runs `render.py check`, which
   draws every quarter second of the film and two seconds around every cut at one
   sample each and fails on the first script error, then renders 8 frames per scene
   into `review/sheet-*.png` (4 PNGs, seconds). Sheets alone sample too sparsely to
   prove a scene runs: a template once shipped with an error between two samples.
   **Read every sheet** before
   rendering in full: clipped or colliding text, a transition that does not cover the
   frame, a scene that reads too small. Fix `reel.js`, re-run, repeat. The full
   render costs minutes; a sheet costs seconds.

6. **Render, score, encode.** `./make.sh all`: every frame with motion blur
   (`render.py frames`, parallel workers), the soundtrack (`synth.py`), the video
   (`encode.py`: a CRF-14 master plus `NAME.mp4`, the lowest CRF under `--max-mb`,
   default 29 MiB for chat uploads), and a contact sheet pulled from the encoded
   file. Each step exits non-zero when it cannot vouch for its output: a page error, a
   missing frame, a decoded frame count that differs from `cues.json`, a silence
   window that is not silent.

7. **Verify what ships, then report.** Look at `review/NAME-sheet.png` (frames of
   the ENCODED file) and at 1:1 crops of the densest text, e.g.
   `ffmpeg -ss 12.5 -i NAME.mp4 -frames:v 1 -vf crop=1100:560:760:300 crop.png`.
   Quote what `encode.py` printed (frames, duration, size) and the levels `synth.py`
   printed at its checks. You cannot listen: say that the mix is measured, not judged
   by ear.

## Editing reel.js

- **Contract.** A scene is `draw(ctx, t, lt, tf)`. `lt` is choreography time inside
  the scene (entrances count from 0, exits from `ND(i)`, the choreographed end);
  `t` is absolute time (kick pulse, flashes); `tf` is the frame's own time, used for
  anything discrete (which card is showing, a count) so a cut never blends two states
  inside one motion-blurred frame.
- **Pure function of time.** No state between calls; randomness only from
  `mulberry32(seed)`, never `Math.random`. Anything that must persist is recomputed.
- **Adding a scene:** one record in `SCENES` (`id`, HUD `name` and `spec`, process
  `step`, `nom` and `bars`, `ground`, `bloom`, `vig`, `draw`), its copy in `CONTENT`,
  its sound cues in `cueSheet()`, their sounds in `score.py`. Refer to scenes by id
  (`ST[at.check]`), never by position. Transitions live in `TRANS`, windowed in film
  time via `absTime(i, u)`, which maps choreography time `u` of scene `i` to the film.
- **Layout** assumes 1920×1080 at 60 fps. Another aspect ratio means revisiting
  every scene's coordinates; review sheets will show where.

## Sound

`score.py` is a function `score(s)` over a `Session`: six buses (`drums`, `bass`,
`pad`, `keys`, `fx`, `send` for reverb), instruments from `synth.py`, `s.kick(t)` for
kicks that also duck the pads, `s.silence(t0, t1)` for gated silence, and
`s.check(label, t)` for levels to print after the mix. Place every sound from `s.cues`,
never from a typed time. See `references/sound.md`.

## References

- `references/craft.md`: timing grid, easing and spring settings, reading time,
  holds that stay alive, the transition catalogue, restraint.
- `references/pipeline.md`: motion blur, `t` versus `tf`, headless canvas and font
  pitfalls, encoding and file sizes, render costs.
- `references/sound.md`: scoring to the cue sheet, the instrument set, the mix,
  checking a soundtrack you cannot hear.
