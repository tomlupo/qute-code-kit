"""The soundtrack for this reel. It runs inside motion-reel's synth.py:

    ./make.sh audio          (or: uv run <skill>/scripts/synth.py .)

Every sound is placed from cues.json, which reel.js exports, so when the picture moves
the sound moves with it. Change the harmony, the instruments and the gains here; add a
cue to reel.js's cueSheet() when a new picture event should be heard.
"""

import numpy as np
from synth import bass as bass_note
from synth import (
    glide,
    grain,
    midi,
    pad,
    plink,
    pluck,
    reverse,
    rim,
    soft_impact,
    sonar,
    sweep,
    tick,
    whoosh,
    woodblock,
)

# F major in half-time. One (pad voicing, bass root) per groove bar, cycling.
CHORDS = [
    ([53, 57, 60, 64, 67], 41),  # Fmaj9
    ([53, 57, 60, 64, 67], 41),
    ([50, 53, 57, 60, 64], 38),  # Dm9
    ([50, 53, 57, 60, 64], 38),
    ([46, 50, 53, 57, 60], 34),  # Bbmaj9
    ([46, 50, 53, 57, 60], 34),
    ([46, 50, 53, 55, 57], 43),  # Gm9 over Bb
    ([48, 53, 55, 60], 36),  # Csus4
]
INTRO = [53, 57, 60, 64, 67]
FINAL = [41, 48, 53, 57, 60, 67, 72, 79]  # F add9, wide
PENTA = [77, 79, 81, 84, 86, 89, 91, 93, 96]  # F major pentatonic, high
ARP = [0, 2, 1, 3, 2, 4, 3, 1]


def score(s):
    c, beat, bar, rng = s.cues, s.beat, s.bar, s.rng
    g0, g1 = c["groove"]
    start = dict(zip(c["scenes"], c["starts"]))  # scene start time by id

    def span(key):  # the length of a [t0, t1] cue window
        return c[key][1] - c[key][0]

    def hit(
        sound, t, gain, pan=0.0, wet=0.0
    ):  # one sound, dry on fx and, when wet, into the reverb
        s.fx.add(sound, t, gain, pan)
        if wet:
            s.send.add(sound, t, wet)

    # ---- intro: a slow swell, soft quarter ticks, a marimba note per level
    s.pad.add(
        np.stack(
            [
                sweep(ch, lambda t: 220 * (1600 / 220) ** min(1, t / g0))
                for ch in pad(INTRO, g0 - 0.02, attack=min(2.5, g0 / 2), release=0.02)
            ]
        ),
        0,
        0.9,
    )
    t = bar
    while t < g0 - 1e-6:
        s.drums.add(tick(), t, 0.03, 0.35)
        t += beat
    for k, t in enumerate(c["scale"]):
        hit(
            plink(midi(PENTA[min(k, len(PENTA) - 1)])),
            t,
            0.24 + 0.03 * k,
            -0.6 + 1.2 * k / max(1, len(c["scale"]) - 1),
            wet=0.1,
        )
    hit(plink(midi(89)), c["scaleSettle"], 0.09, 0.6)
    # the ball rises into the ring: a swell that peaks on the arrival
    rise = c["rise"][0]
    hit(whoosh(c["arrive"] - rise + 0.1, 200, 2500, 0.92, (0, 0)), rise, 0.12)
    hit(soft_impact(2.6), c["arrive"], 0.55, wet=0.2)

    # ---- the groove: the kicks reel.js pulses on (KICK), rim on 3, eighth ticks, bass, pads
    bars = []
    b = g0
    while b < g1 - 1e-6:
        bars.append(b)
        b += bar
    for t in c["kicks"]:  # a kick on a bar line hits harder
        s.kick(t, 0.72 if min(abs(t - x) for x in bars) < 1e-3 else 0.5)
    for j, b in enumerate(bars):
        notes, root = CHORDS[j % len(CHORDS)]
        if b + 2 * beat < g1:
            r = rim()
            s.drums.add(r, b + 2 * beat, 0.2, 0.1)
            s.send.add(r, b + 2 * beat, 0.1)
        for e in range(8):
            if b + e * beat / 2 < g1:
                s.drums.add(tick(), b + e * beat / 2, 0.06 if e % 2 else 0.035, 0.35)
        for off, d in (
            (0, 0.9 * beat),
            (1.5 * beat, 0.4 * beat),
            (2 * beat, 1.5 * beat),
        ):
            if b + off < g1:
                s.bass.add(
                    bass_note(midi(root), min(d, g1 - b - off - 0.02)), b + off, 0.34
                )
        end = min(b + bar, g1)
        s.pad.add(
            pad(notes, end - b, attack=0.08, release=0.1 if end == b + bar else 0.01),
            b,
            1.0,
        )
        if (
            start["signal"] <= b < start["rhythm"]
        ):  # felt-piano eighths through the analytic middle
            for i in range(8):
                if b + i * beat / 2 < g1:
                    note = midi(notes[ARP[i] % len(notes)] + 12)
                    s.keys.add(
                        pluck(note, dur=0.7, bright=0.45),
                        b + i * beat / 2,
                        0.1 if i % 2 == 0 else 0.07,
                        0.4 if i % 2 else -0.4,
                    )

    # ---- one sound per picture event
    for k, t in enumerate(c["columns"]):
        hit(woodblock(midi(PENTA[k % len(PENTA)] - 5) * 2), t, 0.16, -0.5 + k * 0.25)
    hit(whoosh(span("dive") + 0.1, 250, 6500, 0.9, (0, 0)), c["dive"][0], 0.16)
    hit(soft_impact(1.6), c["cut"], 0.25)
    for k, t in enumerate(c["inputs"]):
        hit(woodblock(midi(84 + 2 * k) * 1.5, 0.08), t, 0.1)
    hit(whoosh(span("fold"), 400, 2500, 0.6, (-0.3, 0.3)), c["fold"][0], 0.08)
    hit(whoosh(span("connector"), 600, 3000, 0.5, (-0.2, 0.4)), c["connector"][0], 0.05)
    hit(glide(660, 780, span("slide")) * 0.5, c["slide"][0], 0.1, 0.4)
    hit(woodblock(2600, 0.06), c["snap"], 0.22, 0.4)
    hit(whoosh(span("push") + 0.1, 250, 4000, 0.8, (0, 0)), c["push"][0], 0.14)
    for t in c["landings"]:  # one grain per item landing in the ranking
        hit(
            grain(midi(PENTA[int(rng.integers(0, len(PENTA)))])),
            t,
            0.016,
            float(rng.uniform(-0.8, 0.8)),
        )
    for k, t in enumerate(c["stars"]):
        hit(plink(midi(PENTA[2 + k]), 0.8), t, 0.12, -0.2 + 0.1 * k, wet=0.07)
    hit(whoosh(span("fly"), 500, 7000, 0.9, (-0.3, 0.3)), c["fly"][0], 0.14)
    hit(sonar(span("scan")), c["scan"][0], 0.12, wet=0.1)
    for k in range(2):
        hit(woodblock(220, 0.1), c["flag"] + 0.1 * k, 0.12, 0.3)
    hit(
        reverse(whoosh(span("collapse"), 300, 3000, 0.95, (0, 0))),
        c["collapse"][0],
        0.14,
    )
    hit(soft_impact(1.6), c["iris"], 0.22)
    hit(whoosh(span("sweep"), 300, 2000, 0.5, (-0.4, 0.4)), c["sweep"][0], 0.1)
    for k, t in enumerate(c["items"]):
        hit(
            woodblock(midi(PENTA[k % len(PENTA)] - 5) * 2, 0.09),
            t,
            0.14,
            -0.4 + 0.16 * k,
        )
    for k, t in enumerate(c["focus"]):
        hit(plink(midi(PENTA[2 * k % len(PENTA)]), 0.9), t, 0.1, -0.3 + 0.3 * k)
    hit(whoosh(span("flood"), 250, 3500, 0.85, (0, 0)), c["flood"][0], 0.16)
    for k, t in enumerate(c["cards"]):
        if k != c["quiet"]:
            hit(plink(midi(PENTA[k % len(PENTA)]), 0.6), t, 0.14, -0.3 + 0.1 * k)
    # an odometer, ticking as fast as the number on screen climbs
    for t in c["countTicks"]:
        hit(tick(0.02), t, 0.05, 0.2)
    for i in range(int((c["cards"][-1] + c["card"] - c["cards"][0]) / (beat / 2))):
        t = c["cards"][0] + i * beat / 2 + beat / 4
        if t < g1:
            s.drums.add(tick(0.03), t, 0.03, -0.35)

    # ---- the end: after the silence, a warm arrival and the last chord; the ball lands as the full stop
    if c["silence"][1] > c["silence"][0]:
        s.silence(*c["silence"])
    s.fade_out = span("fade")  # the sound fades with the picture
    hit(soft_impact(3.2), c["end"], 0.7, wet=0.25)
    s.pad.add(
        pad(FINAL, s.dur - c["end"] - 0.3, attack=0.01, release=0.3), c["end"], 1.25
    )
    for k, n in enumerate([65, 69, 72, 76]):
        s.keys.add(
            pluck(midi(n + 12), dur=1.6, bright=0.35),
            c["end"] + 0.03 + 0.09 * k,
            0.08,
            -0.3 + 0.2 * k,
        )
    for k, t in enumerate(c["endBall"]):
        hit(plink(midi(PENTA[5 + min(k, 3)])), t, 0.16 * 0.55**k, 0.3)

    # ---- what to measure after the mix (nobody here can listen)
    s.check("first level lands", c["scale"][0])
    s.check("arrival", c["arrive"])
    s.check("snap to grid", c["snap"])
    s.check("the end", c["end"])
