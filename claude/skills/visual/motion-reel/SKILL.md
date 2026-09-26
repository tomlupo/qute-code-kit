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

2. **Pin the story and the facts before any pixels.** Read every number from its
   source (config, data, a document the user points to) into `CONTENT`, with the
   as-of date. The template's numbers are invented placeholders: none may survive
   into a real film, and a number with no source does not go on screen. What else may
   appear (illustrations, performance claims, a real brand) is in
   `references/craft.md` under "Honesty on screen". Copy follows the brand's voice and
   language; `CONTENT.locale` formats every number.

3. **Pace it: each scene's `bars` in `SCENES`.** A scene is choreographed for `nom`
   bars at 128 BPM and stretches or squeezes to the bars it gets. A scene that
   carries numbers needs about 4 bars (7.5 s); all 1s is a 15-second teaser for mood,
   not for reading. Reading time and re-timing: `references/craft.md`, "The grid".

4. **Look: `THEME`, `FAM`, `GRAIN`, and each scene's `bloom` and `vig`.** Take colours
   and type from the brand, and pick one register per film, calm or punchy
   (`references/craft.md`, "Restraint"). `LIGHT` lists the grounds that take dark type.

5. **Review loop, about a minute.** `./make.sh sheets` runs `render.py check` (about
   50 s; what it proves is in `references/pipeline.md`, "Checks that fail loudly") and
   then writes 8 frames per scene into `review/sheet-*.png`. **Read every sheet**
   before rendering in full: clipped or colliding text, a transition that does not
   cover the frame, a scene that reads too small. Sheets are quarter size; for small
   type, `./make.sh still 39.9` renders that second at full size. Fix `reel.js`,
   re-run, repeat.

6. **Render, score, encode.** `./make.sh all`: every frame with motion blur (a few
   minutes), the soundtrack, the video (a CRF-14 master plus `NAME.mp4`, the lowest
   CRF under `--max-mb`, default 29 MiB for chat uploads), and a contact sheet pulled
   from the encoded file. Every step exits non-zero when it cannot vouch for its
   output.

7. **Verify what ships, then report.** Look at `review/NAME-sheet.png` (frames of
   the ENCODED file) and at 1:1 crops of the densest text, in the template the result
   legend: `./make.sh review --at 39.9 --crop 1100:560:760:300`. Quote what `encode.py`
   printed (frames, duration, size) and the levels `synth.py` printed at its checks.
   You cannot listen: say that the mix is measured, not judged by ear.

## Editing reel.js

- **Contract.** A scene is `draw(ctx, t, lt, tf)`. `lt` is choreography time inside
  the scene: entrances count from 0, exits back from `choreoLen(i)`, the choreographed
  end. `t` is film time (the kick pulse, flashes). `tf` is the frame's own time, for
  anything discrete, such as which card shows or a count (why: `references/pipeline.md`,
  "Motion blur").
- **One timing record per scene.** Every time a sound hangs on lives in one record
  that both the scene and `cueSheet()` read: `T_SCALE`, `T_MIX`, `T_SIG`, `T_RANK`,
  `T_CHECK`, `T_RES`, `COUNT`, `T_END`, and `KICK` for the groove. A sound on an eased
  motion sits where the easing gets there (`reach(ease, y)`), a sound on a spring where
  it lands (`springLands(f)`). Re-timing a scene then moves its sound with it. Never
  type a cue time twice.
- **Pure function of time.** No state between calls; randomness only from
  `mulberry32(seed)`, never `Math.random`. Anything that must persist is recomputed.
- **Adding a scene:** one record in `SCENES` (`id`, HUD `name` and `spec`, process
  `step`, `nom` and `bars`, `ground`, `bloom`, `vig`, `draw`), its copy in `CONTENT`,
  its timing record, its cues in `cueSheet()`, their sounds in `score.py`. Refer to
  scenes by id (`ST[at.check]`), never by position. Transitions live in `TRANS`,
  windowed in film time via `absTime(i, u)`, which maps choreography time `u` of
  scene `i` to the film.
- **Layout** assumes 1920×1080 at 60 fps. Another aspect ratio means revisiting
  every scene's coordinates; review sheets will show where.

## Sound

`score.py` is a function `score(s)` over a `Session` from `synth.py`. Place every
sound from `s.cues`, never from a typed time. The buses, the instruments, gated
silence and the level checks are in `references/sound.md`.

## References

- `references/craft.md`: timing grid, easing and spring settings, reading time,
  holds that stay alive, the transition catalogue, restraint, honesty on screen.
- `references/pipeline.md`: motion blur, `t` versus `tf`, headless canvas and font
  pitfalls, the checks, encoding and file sizes, render costs.
- `references/sound.md`: scoring to the cue sheet, the instrument set, the mix,
  checking a soundtrack you cannot hear.
