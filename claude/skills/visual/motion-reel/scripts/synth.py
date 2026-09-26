# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "scipy>=1.10"]
# ///
"""motion-reel soundtrack engine: instruments, buses, a mastering chain, and a
runner that plays a project's score.py against the reel's cue sheet.

    uv run synth.py PROJECT        # PROJECT/score.py + PROJECT/cues.json -> PROJECT/audio.wav

score.py defines `score(s)`, where `s` is a Session: it places sounds on buses at
times read from `s.cues`, registers kicks for the sidechain, silences to gate, and
checks to measure. The runner mixes, masters, writes the WAV, and prints the level
at every check. It exits non-zero when a registered silence is not silent, because
nobody on the pipeline can listen: the measurement is the only ear there is.
"""

import argparse
import importlib.util
import io
import json
import sys
from pathlib import Path

import numpy as np
from project_files import write_file
from scipy import signal
from scipy.io import wavfile

SR = 48000
_rng = np.random.default_rng(2026)


# ------------------------------------------------------------------ basics
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def tvec(dur):
    return np.arange(max(0, int(round(dur * SR)))) / SR


def lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, "lowpass", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, "highpass", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(
        signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x
    )


def sweep(x, fc_of_t, kind="lowpass", block=256, width=1.4):
    """Time-varying filter, block by block, carrying the filter state across blocks."""
    y = np.empty_like(x)
    zi = None
    for s in range(0, len(x), block):
        fc = fc_of_t((s + block / 2) / SR)
        if kind == "bandpass":
            sos = signal.butter(
                2,
                [fc / width, min(fc * width, SR * 0.45)],
                "bandpass",
                fs=SR,
                output="sos",
            )
        else:
            sos = signal.butter(2, min(fc, SR * 0.45), kind, fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        y[s : s + block], zi = signal.sosfilt(sos, x[s : s + block], zi=zi)
    return y


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def saw(freq, t, phase=0.0):
    """Band-limited sawtooth (polyBLEP)."""
    dt = freq / SR
    p = (freq * t + phase) % 1.0
    y = 2 * p - 1
    m = p < dt
    q = p[m] / dt
    y[m] -= q + q - q * q - 1
    m = p > 1 - dt
    q = (p[m] - 1) / dt
    y[m] -= q * q + q + q + 1
    return y


def _env_on(t, a=0.001):
    return np.clip(t / a, 0, 1)


def pan_stereo(x, pan):
    """Mono to stereo, equal-power; `pan` is -1..1, a number or an array per sample."""
    a = (np.asarray(pan) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)]) * np.sqrt(2)


def _with(t, x):
    """`x` laid over zeros the length of `t`: a layer that may be shorter or longer."""
    out = np.zeros_like(t)
    out[: min(len(x), len(t))] = x[: len(t)]
    return out


# ------------------------------------------------------------------ drums
def kick(f0=130.0, f1=46.0, pdec=32.0, adec=6.0, dur=0.6, click=0.1):
    t = tvec(dur)
    f = f1 + (f0 - f1) * np.exp(-t * pdec)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * adec) * _env_on(t)
    x += hp(_rng.standard_normal(len(t)), 3000) * np.exp(-t * 700) * click
    return np.tanh(1.5 * x) / np.tanh(1.5)


def clap():
    t = tvec(0.4)
    nz = bp(_rng.standard_normal(len(t)), 800, 3200)
    env = sum(np.where(t >= d, np.exp(-(t - d) * 170), 0) for d in (0, 0.010, 0.021))
    env = env + 0.9 * np.where(t >= 0.031, np.exp(-(t - 0.031) * 16), 0)
    return norm(nz * env)


def rim(dur=0.18):
    t = tvec(dur)
    body = np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 70) * 0.5
    nz = bp(_rng.standard_normal(len(t)), 1800, 6000) * np.exp(-t * 60)
    return norm(body + nz)


def hat(decay=48.0, dur=0.12):
    t = tvec(dur)
    return norm(hp(_rng.standard_normal(len(t)), 7500, 4) * np.exp(-t * decay))


def tick(dur=0.05):
    t = tvec(dur)
    return norm(hp(_rng.standard_normal(len(t)), 8000, 4) * np.exp(-t * 90))


# ------------------------------------------------------------------ pitched
def bass(freq, dur=0.21):
    t = tvec(max(dur, 0.01) + 0.03)
    x = 0.55 * saw(freq, t) + 0.9 * np.sin(2 * np.pi * freq * t)
    env = (
        np.clip(t / 0.003, 0, 1) * np.exp(-t * 4.0) * np.clip((t[-1] - t) / 0.03, 0, 1)
    )
    return lp(x * env, 520)


def pad(notes, dur, attack=0.08, release=0.12):
    """Detuned saw pad, stereo; filter it on the bus (Session.pad_cut)."""
    t = tvec(dur + release)
    L = np.zeros_like(t)
    R = np.zeros_like(t)
    for n in notes:
        f = midi(n)
        for cents, side in ((-11, "L"), (5, "L"), (0, "C"), (-5, "R"), (11, "R")):
            v = saw(f * 2 ** (cents / 1200), t, _rng.uniform())
            if side in "LC":
                L += v
            if side in "RC":
                R += v
    env = np.clip(t / attack, 0, 1) * np.where(
        t < dur, 1.0, np.clip(1 - (t - dur) / release, 0, 1)
    )
    return np.stack([L, R]) * env / (len(notes) * 3)


def pluck(freq, dur=0.6, bright=0.5):
    """Felt-piano-ish pluck: additive partials, the high ones dying first."""
    t = tvec(dur)
    out = np.zeros_like(t)
    for h in range(1, 14):
        if h * freq > 12000:
            break
        out += (
            np.sin(2 * np.pi * h * freq * t)
            / h**1.1
            * np.exp(-t * (5 + h * h * 0.9 * bright))
        )
    return norm(out * np.clip(t / 0.002, 0, 1))


def plink(freq, dur=0.6):
    """Marimba-ish: partials at 1, 3.93 and 9.2, a tiny pitch drop on the strike."""
    t = tvec(dur)
    ph = 2 * np.pi * np.cumsum(freq * (1 + 0.06 * np.exp(-t * 60))) / SR
    x = (
        np.sin(ph) * np.exp(-t * 8)
        + 0.35 * np.sin(3.93 * ph) * np.exp(-t * 30)
        + 0.15 * np.sin(9.2 * ph) * np.exp(-t * 60)
    )
    return norm(x * _env_on(t))


def woodblock(freq, dur=0.12):
    t = tvec(dur)
    tone = np.sin(2 * np.pi * freq * t) * np.exp(-t * 55) + 0.4 * np.sin(
        2 * np.pi * freq * 2.4 * t
    ) * np.exp(-t * 90)
    click = hp(_rng.standard_normal(len(t)), 2500) * np.exp(-t * 400) * 0.3
    return norm((tone + click) * np.clip(t / 0.0008, 0, 1))


def grain(freq, dur=0.05):
    t = tvec(dur)
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * 70) * np.clip(t / 0.002, 0, 1)


def blip(freq, dur=0.1):
    t = tvec(dur)
    return (
        (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t))
        * np.exp(-t * 38)
        * _env_on(t)
    )


def glide(f0, f1, dur):
    t = tvec(dur)
    f = f0 + (f1 - f0) * (1 - np.exp(-t * 8)) / (1 - np.exp(-8))
    return (
        np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / max(dur, 1e-6)) ** 2
    )


def sonar(dur, f0=520.0, f1=880.0):
    t = tvec(dur)
    u = t / max(dur, 1e-6)
    f = f0 * (f1 / f0) ** u * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.sin(np.pi * u) ** 1.5


# ------------------------------------------------------------------ effects
def whoosh(dur=0.5, lo=250.0, hi=5000.0, peak=0.65, pan=(-0.7, 0.7)):
    """Band-passed noise sweeping up to `peak` of its length, panned across; stereo."""
    t = tvec(dur)
    u = t / max(dur, 1e-6)

    def fc(tt):
        v = tt / dur
        return (
            lo * (hi / lo) ** (v / peak)
            if v < peak
            else hi * 0.5 ** ((v - peak) / (1 - peak))
        )

    y = norm(sweep(_rng.standard_normal(len(t)), fc, "bandpass", width=1.6))
    y = y * np.where(
        u < peak, (u / peak) ** 2, np.clip(1 - (u - peak) / (1 - peak), 0, 1) ** 1.6
    )
    return pan_stereo(y, np.linspace(pan[0], pan[1], len(t)))


def reverse(stereo_or_mono):
    """A sound played backwards with a rising fade: the swell into a hit."""
    x = np.asarray(stereo_or_mono)
    x = x.sum(axis=0) if x.ndim == 2 else x
    x = norm(x[::-1])
    return x * np.linspace(0, 1, len(x)) ** 2


def riser(dur):
    t = tvec(dur)
    u = t / max(dur, 1e-6)
    y = (
        norm(
            sweep(
                _rng.standard_normal(len(t)),
                lambda tt: 250 * (7000 / 250) ** (tt / dur),
                "bandpass",
                width=1.35,
            )
        )
        * u**2.4
    )
    tone = np.sin(2 * np.pi * np.cumsum(160 * (1400 / 160) ** u) / SR) * u**3 * 0.25
    return y + tone


def impact(dur=2.6, crash=1.0):
    """A big hit: pitched boom, crash, kick. For punchy reels."""
    t = tvec(dur)
    boom = np.sin(2 * np.pi * np.cumsum(34 + 70 * np.exp(-t * 16)) / SR) * np.exp(
        -t * 1.9
    )
    cr = hp(_rng.standard_normal(len(t)), 3200) * (
        np.exp(-t * 3.2) * 0.3 + np.exp(-t * 25) * 0.5
    )
    k = _with(t, kick(f0=190, f1=42, adec=4, dur=0.8, click=0.5))
    return np.tanh(1.2 * (boom * 0.9 + cr * crash + k * 0.8))


def soft_impact(dur=3.0):
    """A warm arrival: sub boom and a little air, no crash. For calm brands."""
    t = tvec(dur)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 40 * np.exp(-t * 14)) / SR) * np.exp(
        -t * 1.6
    )
    air = lp(hp(_rng.standard_normal(len(t)), 4000), 9000) * np.exp(-t * 3.5) * 0.12
    k = _with(t, kick(f0=120, f1=44, adec=3.5, dur=0.9, click=0.08))
    return np.tanh(1.1 * (boom + air + 0.6 * k))


def burst(dur=0.9):
    t = tvec(dur)
    y = sweep(
        _rng.standard_normal(len(t)), lambda tt: 9000 * (300 / 9000) ** min(1, tt / 0.7)
    )
    y = norm(y * np.exp(-t * 4.5) * np.clip(t / 0.002, 0, 1))
    th = np.sin(2 * np.pi * np.cumsum(50 + 80 * np.exp(-t * 20)) / SR) * np.exp(-t * 6)
    return y * 0.8 + th * 0.7


def make_ir(dur=2.6, decay=2.6):
    t = tvec(dur)
    ir = _rng.standard_normal((2, len(t))) * np.exp(-t * decay)
    ir = np.stack([lp(ch, 6500) for ch in ir])
    ir[:, : int(0.012 * SR)] = 0
    return ir / np.sqrt(np.sum(ir**2, axis=1, keepdims=True))


# ------------------------------------------------------------------ buses and the session
class Bus:
    def __init__(self, n):
        self.n = n
        self.x = np.zeros((2, n))

    def add(self, sig, t0, gain=1.0, pan=0.0):
        """Mix `sig` (mono or stereo) in at t0 seconds; mono is panned equal-power."""
        sig = np.asarray(sig, dtype=float)
        if sig.ndim == 1:
            sig = pan_stereo(sig, pan)
        i0 = int(round(t0 * SR))
        if i0 < 0:
            sig, i0 = sig[:, -i0:], 0
        n = min(sig.shape[1], self.n - i0)
        if n > 0:
            self.x[:, i0 : i0 + n] += gain * sig[:, :n]


class Session:
    """What score.py gets: the cue sheet, six buses, and the mix settings."""

    def __init__(self, info, seed=2026):
        global _rng
        _rng = np.random.default_rng(seed)
        self.rng = np.random.default_rng(seed + 1)
        self.cues = info["cues"]
        self.dur = float(info["dur"])
        self.bpm = float(self.cues["bpm"])
        self.beat = 60 / self.bpm
        self.bar = 4 * self.beat
        self.n = int(round(self.dur * SR))
        self.drums, self.bass, self.pad, self.keys, self.fx, self.send = (
            Bus(self.n) for _ in range(6)
        )
        self.kicks, self.silences, self.checks = [], [], []
        # mix settings a score may change
        self.duck_depth = 0.45  # sidechain: how far pads and bass dip under a kick
        self.pad_cut = 1500  # pad bus low-pass, Hz
        self.reverb = 0.3
        self.delay = 0.45  # dotted-eighth ping-pong on the keys bus
        self.drive = 1.1  # soft-clip drive before the final normalise
        self.fade_out = 0.6

    def kick(self, t, gain=0.72):
        """A kick that also ducks the pads and bass."""
        self.drums.add(kick(), t, gain)
        self.kicks.append(t)

    def silence(self, t0, t1):
        """Gate [t0, t1) to digital silence. Checked after the mix."""
        self.silences.append((t0, t1))

    def check(self, label, t):
        """Report the peak level of the 30 ms from t, after the mix."""
        self.checks.append((label, t, t + 0.03))

    def render(self, out):
        n, tt = self.n, np.arange(self.n) / SR
        kicks = np.array(sorted(self.kicks)) if self.kicks else np.array([-10.0])
        idx = np.searchsorted(kicks, tt, side="right") - 1
        since = np.where(idx >= 0, tt - kicks[np.clip(idx, 0, None)], 10.0)
        duck = 1 - self.duck_depth * np.exp(-since * 8)
        padf = np.stack([lp(ch, self.pad_cut) for ch in self.pad.x])
        ir = make_ir()
        wet = np.stack(
            [
                signal.fftconvolve(
                    self.send.x[c] + 0.2 * padf[c] + 0.25 * self.keys.x[c], ir[c]
                )[:n]
                for c in range(2)
            ]
        )
        dly = np.zeros_like(self.keys.x)
        d = int(round(3 * self.beat / 4 * SR))
        for k in range(1, 5):
            src = self.keys.x.sum(axis=0) * 0.5 * 0.4**k
            if k * d < n:
                dly[k % 2, k * d :] += src[: n - k * d]
        mix = (
            self.drums.x
            + (self.bass.x + 0.22 * padf) * duck
            + self.keys.x
            + self.delay * dly
            + self.fx.x
            + self.reverb * wet
        )
        mix = np.stack([hp(ch, 30) for ch in mix])
        gate = np.ones(n)
        ramp = int(0.008 * SR)
        for t0, t1 in self.silences:
            a, b = int(t0 * SR), int(t1 * SR)
            gate[a:b] = 0
            gate[max(0, a - ramp) : a] *= np.linspace(1, 0, a - max(0, a - ramp))
        mix *= gate
        mix = norm(mix)
        mix = np.tanh(self.drive * mix) / np.tanh(self.drive)
        mix *= np.clip((self.dur - tt) / self.fade_out, 0, 1)
        mix = 0.89 * norm(mix)  # -1 dBFS peak
        wav = io.BytesIO()
        wavfile.write(wav, SR, (mix.T * 32767).astype(np.int16))
        write_file(out, wav.getvalue(), out.parent)  # never through a link at audio.wav
        return mix


def level_db(mix, t0, t1):
    x = mix.mean(axis=0)
    a, b = int(t0 * SR), max(int(t0 * SR) + 1, int(t1 * SR))
    return 20 * np.log10(np.max(np.abs(x[a:b])) + 1e-9)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("project", type=Path)
    a = ap.parse_args()
    project = a.project.resolve()
    info = json.loads((project / "cues.json").read_text())
    # `from synth import ...` in score.py sees this module
    sys.modules.setdefault("synth", sys.modules[__name__])
    # loading score.py must not write its bytecode into the project (a linked __pycache__
    # would carry it elsewhere): nothing but audio.wav is written there
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("reel_score", project / "score.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    s = Session(info)
    mod.score(s)
    out = project / "audio.wav"
    mix = s.render(out)
    rms = 20 * np.log10(np.sqrt(np.mean(mix**2)))
    print(f"wrote {out}: {s.dur:.2f} s, peak -1.0 dBFS, rms {rms:.1f} dBFS")
    for label, t0, t1 in s.checks:
        print(f"  {label:32s} {t0:8.3f} s  {level_db(mix, t0, t1):7.1f} dB")
    loud = [(t0, t1, level_db(mix, t0 + 0.01, t1 - 0.005)) for t0, t1 in s.silences]
    for t0, t1, db in loud:
        print(f"  {'silence':32s} {t0:8.3f} s  {db:7.1f} dB")
    bad = [x for x in loud if x[2] > -100]
    if bad:
        print(f"FAIL: {len(bad)} silence window(s) are not silent", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
