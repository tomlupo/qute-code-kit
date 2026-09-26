# Craft notes

What makes a code-rendered reel read as designed rather than generated. Every rule
here came out of a film that was made, reviewed and changed.

## The grid

Everything sits on a musical grid. At 128 BPM a beat is 0.469 s and a bar 1.875 s.
Scenes last whole bars, cuts land on bar lines, events land on beats or eighths, and
the soundtrack is written to the same grid, so picture and sound agree by
construction rather than by nudging.

| a scene that carries | bars at 128 BPM | seconds |
|---|---|---|
| a title and one idea | 2–3 | 3.8–5.6 |
| numbers to read: a chart, a legend | 4 | 7.5 |
| one montage card | ½ | 0.94 |
| a one-word punchline | ¼–½ | 0.5–0.9 |

**Reading time is the constraint, not the music.** Give a headline at least 1 s after
its reveal settles, every number on screen 1.5 s, a legend of n rows about
0.4 s × n + 1 s, and 2 s more wherever the viewer is meant to compare. A 15-second cut
of eight data scenes (1.9 s each) came back as "nice, but too fast"; re-timed to 56 s
it landed. Keep fast cuts for mood teasers.

**Re-time, don't slow down.** Stretching a finished film 3–4× turns 128 BPM into
35 BPM and every spring into slow motion. Give scenes more bars instead
(each scene's `bars` in `SCENES`), let entrances run about 2× calmer, and add holds
after each idea.

## Easing vocabulary

| motion | curve | typical length |
|---|---|---|
| an entrance (text rising, a bar growing) | outExpo | 0.6–0.9 s; 0.25–0.3 s on a card |
| a move between two states | inOutCubic | 0.5–1 s |
| a dive or zoom that accelerates into a cut | inExpo | 1–1.2 s |
| ambient drift and rotation | linear / sine | the whole hold |

`spring(s, f, d)`: lively is f = 2–3 Hz, d = 7–8 (about 15–25 % overshoot); calm is
f = 1–1.2 Hz, d = 6 (about 8 %). An object that lands on a floor must bounce, not sink:
reflect the overshoot, `y = -abs(1 - spring(s)) * height`. Squash on contact for
0.03–0.05 s, stretch along the speed in flight.

## Physics that reads as craft

- `makeBounce` pins the first two contacts to beats and derives the rest from the
  restitution, so the ball is both musical and physical.
- The spacing chart (a dot every 2–3 frames of the path) shows the easing to anyone who
  animates; frame numbers at the contacts say the timing was chosen.
- Let a motion encode a quantity: hop heights that grow with the level, a ring that is
  exactly the next chart's radius.

## Holds that stay alive

A hold is where the viewer reads, but a frozen frame looks broken. Keep something
moving at a fraction of its entrance speed: a 1–2 % camera drift over the hold, a
sphere that keeps turning, a focus cycle (dim the others to about 45 %, push the
focused item out 10 px, light its legend rows), a slow light sweep. Slow things down;
never stop them.

## Transitions in the template

- **Iris from an object:** the ball rises, becomes a ring, and the ring opens the next
  scene.
- **Dive:** the camera accelerates into one block of a chart until its colour fills the
  frame, and the next scene is that colour.
- **Push:** the next scene rises from below (inOutExpo, 0.9 s).
- **Match cut by geometry:** items fly from a histogram to exactly where the next
  scene's sphere will have them; the sphere folds into a ring at the radius of the next
  scene's donut; the donut floods the screen with the next card's colour.
- **Hard cut on a downbeat after silence**, for the name.

## Restraint

- One punchline card: a small word, a lot of space, digital silence under it, then the
  name on the downbeat. It is the most remembered beat of the film.
- A calm brand gets shallow springs, flashes no brighter than 10 %, no chromatic
  glitches, a half-time groove.
- A showreel may spike chromatic aberration and flash on the drop, and shake the
  camera on the name slam. Choose one register per film.

## Honesty on screen

- Every number is read from a source and the as-of date is on screen (HUD, bottom
  right).
- An illustrative value carries a visible tag (the template's `ILLUSTRATION` pill).
- The template's own numbers are invented and internally consistent; no real client's
  data belongs in a template.
- No return or performance claims unless the user supplies them with their source.
- A film that carries a real organisation's name and branding is a file for its owner,
  not something to publish on their behalf.

## The HUD

Brand top left, the process tracker top right with the current step underlined, the
scene name and a one-line spec typed on at each cut bottom left, the as-of bottom
right, a progress line with a tick per scene bottom centre. It frames the film as a
designed object and carries the facts that do not fit the frame. `HUD_ON` turns it off.
