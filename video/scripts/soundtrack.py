"""Build the promo timeline and an original soundtrack (music + narration + transition effects).

Everything is synthesised here (no third-party music), so the video is free of copyright claims.
Run after narration.py, from the repository root:  .venv\\Scripts\\python.exe video\\scripts\\soundtrack.py
Writes video/src/timeline.json and video/public/soundtrack.wav.
"""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

SR = 44_100
FPS = 30
ROOT = Path(__file__).resolve().parents[1]
FFMPEG = ROOT / "node_modules" / "@remotion" / "compositor-win32-x64-msvc" / "ffmpeg.exe"
rng = np.random.default_rng(7)

# ----------------------------------------------------------------------------------------------- timeline
LEAD = {"hook": 1.1, "meet": 0.7}  # seconds of picture before the line starts (default below)
TAIL = {"cta": 3.4}  # seconds of picture after the line ends (default below)
DEFAULT_LEAD, DEFAULT_TAIL = 0.45, 0.7


def build_timeline(lines: list[dict]) -> list[dict]:
    t = 0.0
    scenes = []
    for line in lines:
        lead = LEAD.get(line["id"], DEFAULT_LEAD)
        tail = TAIL.get(line["id"], DEFAULT_TAIL)
        start, vo = t, t + lead
        end = vo + line["duration"] + tail
        scenes.append(
            {
                "id": line["id"],
                "text": line["text"],
                "start": round(start, 3),
                "voStart": round(vo, 3),
                "end": round(end, 3),
                "from": round(start * FPS),
                "durationInFrames": round(end * FPS) - round(start * FPS),
                "voFrom": round(vo * FPS) - round(start * FPS),
                "words": [
                    {
                        "text": w["text"],
                        "from": round((vo + w["start"]) * FPS) - round(start * FPS),
                        "to": round((vo + w["end"]) * FPS) - round(start * FPS),
                    }
                    for w in line["words"]
                ],
            }
        )
        t = end
    _add_stage_chips(next(sc for sc in scenes if sc["id"] == "stages"))
    return scenes


def _add_stage_chips(scene: dict) -> None:
    """Frames at which the seven relationship-stage chips land (synced to the spoken words, pops in the mix)."""
    words = {w["text"].lower(): w["from"] for w in scene["words"]}
    single, onesided, dating = words.get("single", 17), words.get("one-sided", 39), words.get("dating", 84)
    longd, married = words.get("long-distance", 102), words.get("married", 132)
    scene["chips"] = [
        single,
        onesided,
        (words.get("love", 56) + dating) // 2 + 2,
        dating,
        longd,
        (longd + married) // 2 + 2,
        married,
    ]


# ----------------------------------------------------------------------------------------------- helpers
def midi(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def tvec(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def place(buf: np.ndarray, sig: np.ndarray, at: float, pan: float = 0.0, gain: float = 1.0) -> None:
    """Mix a mono signal into a stereo buffer at time `at` with constant-power panning (-1..1)."""
    i = int(at * SR)
    if i >= buf.shape[1] or i + len(sig) <= 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    sig = sig[: buf.shape[1] - i] * gain
    ang = (pan + 1) * np.pi / 4
    buf[0, i : i + len(sig)] += sig * np.cos(ang)
    buf[1, i : i + len(sig)] += sig * np.sin(ang)


def env_adsr(n: int, a: float, r: float) -> np.ndarray:
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na) if na < n else np.linspace(0, 1, n)[:na]
    if nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(sig: np.ndarray, hz: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), sig)


def highpass(sig: np.ndarray, hz: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), sig)


def bandpass(sig: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), sig)


# ----------------------------------------------------------------------------------------------- instruments
def piano(note: float, dur: float, vel: float = 0.6) -> np.ndarray:
    f = midi(note)
    t = tvec(dur + 1.2)
    out = np.zeros_like(t)
    for n in range(1, 8):
        if f * n > SR / 2.2:
            break
        amp = (1 / n**1.4) * np.exp(-t * (1.1 + 0.55 * n) * (1 + f / 1400))
        out += amp * (np.sin(2 * np.pi * f * n * t) + 0.5 * np.sin(2 * np.pi * f * n * 1.0012 * t))
    attack = np.minimum(1, t / 0.004)
    release = np.where(t > dur, np.exp(-(t - dur) * 6), 1.0)
    return lowpass(out * attack * release * vel * 0.35, 5200)


def pad(notes: list[float], dur: float, vel: float = 0.25) -> np.ndarray:
    t = tvec(dur + 1.0)
    out = np.zeros_like(t)
    for note in notes:
        for det in (-0.07, 0.0, 0.08):
            f = midi(note + det)
            for n in range(1, 9):
                out += (1 / n) * np.exp(-n * 0.45) * np.sin(2 * np.pi * f * n * t + rng.uniform(0, 6.28))
    e = np.minimum(1, t / 0.9) * np.where(t > dur, np.exp(-(t - dur) * 3.5), 1.0)
    lfo = 1 + 0.06 * np.sin(2 * np.pi * 0.23 * t)
    return lowpass(out * e * lfo, 2400) * vel / (len(notes) * 3)


def pluck(note: float, vel: float = 0.4) -> np.ndarray:
    f = midi(note)
    t = tvec(0.9)
    out = sum((1 / n**1.2) * np.exp(-t * (7 + 3 * n)) * np.sin(2 * np.pi * f * n * t) for n in range(1, 6))
    return out * np.minimum(1, t / 0.002) * vel * 0.4


def bass(note: float, dur: float, vel: float = 0.5) -> np.ndarray:
    f = midi(note)
    t = tvec(dur + 0.2)
    out = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    e = np.minimum(1, t / 0.01) * np.exp(-t * 1.2) * np.where(t > dur, np.exp(-(t - dur) * 25), 1.0)
    return out * e * vel * 0.55


def bell(note: float, vel: float = 0.35) -> np.ndarray:
    f = midi(note)
    t = tvec(2.4)
    index = 2.2 * np.exp(-t * 3)
    out = np.sin(2 * np.pi * f * t + index * np.sin(2 * np.pi * f * 3.5 * t))
    return out * np.exp(-t * 1.8) * np.minimum(1, t / 0.003) * vel * 0.4


def kick(vel: float = 0.9) -> np.ndarray:
    t = tvec(0.45)
    freq = 46 + 95 * np.exp(-t * 32)
    out = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 7.5)
    click = highpass(rng.standard_normal(len(t)), 3000) * np.exp(-t * 300) * 0.15
    return (out + click) * vel


def clap(vel: float = 0.35) -> np.ndarray:
    t = tvec(0.35)
    noise = bandpass(rng.standard_normal(len(t)), 900, 3200)
    e = np.zeros_like(t)
    for d in (0.0, 0.011, 0.022):
        e += np.where(t >= d, np.exp(-(t - d) * 38), 0)
    return noise * e * vel * 0.5


def shaker(vel: float = 0.18) -> np.ndarray:
    t = tvec(0.09)
    return highpass(rng.standard_normal(len(t)), 6500) * np.exp(-t * 55) * np.minimum(1, t / 0.006) * vel


def whoosh(dur: float = 0.75, vel: float = 0.3) -> np.ndarray:
    t = tvec(dur)
    noise = rng.standard_normal(len(t))
    # Sweep a band upwards by mixing three static bands with moving weights.
    x = t / dur
    low, mid, high = bandpass(noise, 300, 900), bandpass(noise, 900, 3000), bandpass(noise, 3000, 9000)
    out = low * (1 - x) + mid * np.sin(np.pi * x) + high * x
    return out * np.sin(np.pi * x) ** 1.6 * vel


def riser(dur: float = 1.6, vel: float = 0.25) -> np.ndarray:
    t = tvec(dur)
    x = t / dur
    noise = highpass(rng.standard_normal(len(t)), 1500)
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * x**2) / SR) * 0.25
    return (noise * 0.6 + tone) * x**2.2 * vel


def impact(vel: float = 0.7) -> np.ndarray:
    t = tvec(2.0)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-t * 9)) / SR) * np.exp(-t * 2.6)
    air = lowpass(rng.standard_normal(len(t)), 5000) * np.exp(-t * 5) * 0.12
    return (boom + air) * vel


def pop(vel: float = 0.18) -> np.ndarray:
    t = tvec(0.12)
    return np.sin(2 * np.pi * np.cumsum(500 + 900 * np.exp(-t * 60)) / SR) * np.exp(-t * 45) * vel


# ----------------------------------------------------------------------------------------------- music
def compose(scenes: list[dict], total: float) -> tuple[np.ndarray, np.ndarray]:
    """Returns (dry music, reverb send) stereo buffers."""
    n = int(total * SR) + SR
    dry = np.zeros((2, n))
    send = np.zeros((2, n))
    starts = {s["id"]: s["start"] for s in scenes}
    meet, cta = starts["meet"], starts["cta"]

    # A — intro (hook, why): soft, a little sad. Bm  G  D  A, one chord per 1.6 s, broken piano.
    intro = [(47, [59, 62, 66]), (43, [59, 62, 67]), (38, [57, 62, 66]), (45, [57, 61, 64])]
    step = meet / 8
    for i in range(8):
        root, chord = intro[i % 4]
        t0 = i * step
        p = pad([root + 12] + chord, step, 0.2)
        place(dry, p, t0, gain=0.9)
        place(send, p, t0, gain=0.5)
        for k, note in enumerate(chord + [chord[1] + 12]):
            pn = piano(note + 12, step * 0.8, 0.45 + 0.1 * (k == 0))
            place(dry, pn, t0 + k * step / 4, pan=-0.3 + 0.2 * k)
            place(send, pn, t0 + k * step / 4, gain=0.8)
    r = riser(1.6)
    place(dry, r, meet - 1.6, gain=0.9)
    place(send, r, meet - 1.6, gain=0.6)
    place(dry, impact(), meet - 0.02, gain=0.8)
    place(send, bell(86, 0.4), meet, gain=1.0)
    place(dry, bell(86, 0.4), meet, gain=0.7)

    # B — features: warm groove at 96 BPM.  D  A  Bm  G  (I V vi IV)
    beat = 60 / 96
    bar = 4 * beat
    prog = [(38, [62, 66, 69]), (33, [61, 64, 69]), (35, [62, 66, 71]), (31, [62, 67, 71])]
    arp_pat = [0, 1, 2, 1, 3, 2, 1, 2]
    t, b = meet, 0
    while t < cta - 0.01:
        root, chord = prog[b % 4]
        length = min(bar, cta - t)
        p = pad([root + 24] + chord, length, 0.17)
        place(dry, p, t, gain=0.8)
        place(send, p, t, gain=0.4)
        place(dry, bass(root + 12, length * 0.95, 0.5), t)
        for k, note in enumerate(chord):
            pn = piano(note, beat * 1.6, 0.32)
            place(dry, pn, t + (0 if k == 0 else 0.012 * k), pan=0.15)
            place(send, pn, t, gain=0.5)
        tones = chord + [chord[0] + 12]
        for s in range(8):
            if t + s * beat / 2 >= cta:
                break
            pl = pluck(tones[arp_pat[s]] + 12, 0.32)
            place(dry, pl, t + s * beat / 2, pan=0.45 if s % 2 else -0.45)
            place(send, pl, t + s * beat / 2, gain=0.7)
        for q in range(4):
            tq = t + q * beat
            if tq >= cta:
                break
            if q in (0, 2):
                place(dry, kick(0.8), tq)
            else:
                place(dry, clap(0.32), tq, pan=0.1)
                place(send, clap(0.32), tq, gain=0.5)
            place(dry, shaker(0.14), tq + beat / 2, pan=0.35)
            place(dry, shaker(0.08), tq + beat / 4, pan=0.35)
            place(dry, shaker(0.08), tq + 3 * beat / 4, pan=0.35)
        t += bar
        b += 1

    # C — call to action: lift, bell melody, final D major chord ringing out.
    place(dry, impact(0.55), cta - 0.02)
    end_prog = [(31, [62, 67, 71]), (33, [61, 64, 69]), (38, [62, 66, 69])]
    lengths = [bar, bar, max(2.0, total - cta - 2 * bar)]
    t = cta
    for (root, chord), length in zip(end_prog, lengths, strict=True):
        p = pad([root + 24] + chord + [chord[0] + 12], length, 0.22)
        place(dry, p, t, gain=0.9)
        place(send, p, t, gain=0.6)
        place(dry, bass(root + 12, length * 0.9, 0.45), t)
        for k, note in enumerate(chord):
            pn = piano(note, min(length, 2.5), 0.38)
            place(dry, pn, t + 0.03 * k)
            place(send, pn, t + 0.03 * k, gain=0.6)
        t += length
    melody = [(78, 0), (81, 1), (83, 2), (81, 3), (78, 4.5), (76, 5.5), (78, 6), (86, 8)]
    for note, beats in melody:
        at = cta + beats * beat
        if at < total - 0.6:
            place(dry, bell(note, 0.32), at, pan=0.2)
            place(send, bell(note, 0.32), at, gain=0.9)
    return dry, send


def reverb(send: np.ndarray, seconds: float = 2.4) -> np.ndarray:
    t = tvec(seconds)
    out = np.zeros_like(send)
    for ch in range(2):
        ir = lowpass(rng.standard_normal(len(t)), 6000) * np.exp(-t * 3.1) * np.minimum(1, t / 0.02)
        ir /= np.sqrt(np.sum(ir**2))
        out[ch] = fftconvolve(send[ch], ir)[: send.shape[1]]
    return out * 0.55


# ----------------------------------------------------------------------------------------------- narration
def decode(mp3: Path) -> np.ndarray:
    # Remotion's slim ffmpeg build can only write WAV, so decode through a temporary file in the project.
    tmp = ROOT.parent / ".cache" / "video-tmp" / (mp3.stem + ".wav")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603 - fixed local ffmpeg binary and our own files
        [str(FFMPEG), "-v", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(tmp)],
        check=True,
    )
    with wave.open(str(tmp), "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    tmp.unlink()
    return data


def narration_track(scenes: list[dict], n: int) -> tuple[np.ndarray, np.ndarray]:
    """Returns (stereo voice, mono 0..1 'voice active' envelope used for ducking)."""
    voice = np.zeros((2, n))
    active = np.zeros(n)
    for s in scenes:
        sig = decode(ROOT / "public" / "vo" / f"{s['id']}.mp3")
        sig = highpass(sig, 85)
        sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.82
        i = int(s["voStart"] * SR)
        sig = sig[: n - i]
        voice[:, i : i + len(sig)] += sig
        active[i : i + len(sig)] = 1.0
    # Smooth: fast duck (≈0.12 s), slow release (≈0.45 s).
    smooth = np.zeros(n)
    a_dn, a_up = np.exp(-1 / (0.12 * SR)), np.exp(-1 / (0.45 * SR))
    # Vectorised approximation: two one-pole filters, then take the max so ducking starts early.
    down = lfilter([1 - a_dn], [1, -a_dn], active)
    up = lfilter([1 - a_up], [1, -a_up], active[::-1])[::-1]
    smooth = np.maximum(down, up * 0.0 + down)
    rel = lfilter([1 - a_up], [1, -a_up], active)
    smooth = np.maximum(smooth, rel)
    return voice, np.clip(smooth, 0, 1)


def main() -> None:
    lines = json.loads((ROOT / "src" / "narration.json").read_text(encoding="utf-8"))
    scenes = build_timeline(lines)
    total = scenes[-1]["end"]
    timeline = {"fps": FPS, "durationInFrames": round(total * FPS), "seconds": round(total, 2), "scenes": scenes}
    (ROOT / "src" / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

    dry, send = compose(scenes, total)
    music = dry + reverb(send)
    n = music.shape[1]
    voice, active = narration_track(scenes, n)

    # Music sits ~13 dB under the voice while she speaks and comes up between lines.
    duck = 1.0 - 0.75 * active
    music *= duck * 0.8

    sfx = np.zeros((2, n))
    for s in scenes[1:]:
        if s["id"] not in ("meet", "cta"):
            place(sfx, whoosh(0.7, 0.22), s["start"] - 0.35, pan=0.0)
    for s in scenes:
        if s["id"] == "stages":
            for k, f in enumerate(s["chips"]):
                place(sfx, pop(0.13), s["start"] + f / FPS, pan=-0.5 + k * 0.16)

    mix = music + voice + sfx
    fade = int(1.8 * SR)
    end = int(total * SR)
    mix = mix[:, :end]
    mix[:, -fade:] *= np.linspace(1, 0, fade) ** 1.5
    mix[:, : int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    peak = np.max(np.abs(mix))
    mix = np.tanh(mix / peak * 1.15) / np.tanh(1.15) * 0.93

    out = ROOT / "public" / "soundtrack.wav"
    pcm = (mix.T * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"timeline {total:.2f}s, {timeline['durationInFrames']} frames; soundtrack -> {out}")
    for s in scenes:
        print(f"  {s['id']:<10} {s['start']:6.2f} -> {s['end']:6.2f}")


if __name__ == "__main__":
    main()
