# Sound notes

## Scoring to the cue sheet

`render.py info` writes `cues.json`: the timing (`dur`, `bpm`, scene `starts`), the
groove window, the silence window, and one named time or list of times for every
picture event that should be heard. It comes from `cueSheet()` in `reel.js`, which
reads the same per-scene timing records the scenes animate with; a sound on an eased
motion is placed where the easing reaches it (`reach`), so the count-up's ticks thin
out as the number slows. `score.py` places sounds only from it, so re-timing the
picture re-times the sound on the next `./make.sh audio`.

One family of sound per kind of picture event:

| picture | sound |
|---|---|
| a contact (a ball landing, a level reached) | `plink` (marimba), rising in pitch with the quantity |
| something locking into place | `woodblock`, one per item, stepping up the scale |
| a move, a dive, a push | `whoosh` panned with the motion |
| an arrival, a scene opening | `soft_impact` (calm) or `impact` (punchy) |
| items landing in a chart | `grain`, one per item: a soft rain |
| a scan | `sonar` |
| a number counting up | `tick` bursts, thinning as the count slows |
| a snap to a grid | a high `woodblock` |
| the swell into a hit | `reverse(...)` of the sound that follows |
| a build into a drop (punchy register) | `riser` |
| an explosion, particles bursting (punchy register) | `burst` |
| a cut in a fast montage (punchy register) | `blip`, climbing the scale |

## Harmony and groove

`score.py` cycles `CHORDS`, one (pad voicing, bass root) per groove bar, after a
filtered pad swell under the intro and before a wide final chord from the `end` cue.
The template is in F major with a half-time groove: the kicks of `KICK` in `reel.js`
(1 and the and-of-2, exported as the `kicks` cue, so the picture pulses on the same
hits), rim on 3, eighth ticks, felt-piano eighths through the analytic middle. For an
energetic film, set `KICK` to `[0, 1, 2, 3]` (four on the floor), add a `clap` on 2
and 4 and off-beat `hat`s, and switch the arrivals to `impact`.

`s.kick(t)` places a kick and registers it for the sidechain, which ducks the pads and
bass (`s.duck_depth`) so the groove breathes.

## Silence as a device

A quiet card gets digital silence: `s.silence(t0, t1)` gates the whole mix after the
reverb and delay, so no tail leaks into it. The next downbeat then hits harder than
any drum could.

## The mix

Six buses: `drums`, `bass`, `pad` (low-passed at `s.pad_cut`), `keys` (with a
dotted-eighth ping-pong delay), `fx`, and `send` (convolution reverb, plus a little
pad and keys). Master chain: 30 Hz high-pass, gates, normalise, `tanh` soft clip
(`s.drive`), fade-out, −1 dBFS peak. Measured RMS: about −16.8 dBFS for the calm
template, about −13.7 dBFS for a four-on-the-floor showreel.

## Checking a soundtrack nobody can hear

A model cannot listen to what it made, so measure and say so:

- `s.check(label, t)` prints the post-mix peak at each named event: the cue should be
  well above its surroundings (in the template, the first level about −15 dB, the
  arrival about −1 dB). A reading can move by a decibel after an unrelated edit,
  because every noise-based sound draws from one random stream; a cue that went
  missing drops by far more.
- Every silence window must read about −180 dB; `synth.py` fails above −100 dB.
- Report the levels, and report that the mix is measured, not judged by ear.
