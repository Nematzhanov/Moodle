"""Фоновая музыка для промо CodeCheck — синтез, привязанный к монтажу (30.4 с, 100 BPM).

Запуск: ../../.venv/bin/python scripts/make_music.py --cut 60  → assets/audio/bgm-60s.wav (60 с, index.html)
        ../../.venv/bin/python scripts/make_music.py --cut 22  → assets/audio/bgm.wav (22.7 с)
        ../../.venv/bin/python scripts/make_music.py --cut 30  → assets/audio/bgm-30s.wav (30.4 с)
Почему синтез: вход в HeyGen не выполнен, MusicGen без зависимостей; так трек ещё и
точно попадает в монтажные точки: вердикт 19.4 с, логотип 27.1 с.
"""
from pathlib import Path

import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
# Монтажные точки двух версий ролика. Выбор: --cut 22 (index.html) или --cut 30 (versions/index-30s.html)
CUTS = {
    "22": dict(DUR=22.7, HIT_VERDICT=12.6, HIT_LOGO=19.9, PUSH=[3.05, 15.55], HATS=(7.7, 15.5),
               CREDITS=(17.5, 19.8), OUT="bgm.wav",
               PAD=[(0, 0), (1.8, 0.55), (3.0, 0.6), (3.4, 0.35), (4.2, 0.5), (11.5, 0.5)]),
    "30": dict(DUR=30.4, HIT_VERDICT=19.4, HIT_LOGO=27.1, PUSH=[3.05, 9.85, 22.35], HATS=(14.5, 22.3),
               CREDITS=(24.3, 26.9), OUT="bgm-30s.wav",
               PAD=[(0, 0), (1.8, 0.55), (3.0, 0.6), (3.4, 0.35), (4.2, 0.5), (9.8, 0.5), (10.2, 0.32),
                    (10.9, 0.5), (18.3, 0.5)]),
    # 60-секундная светлая версия (index.html): вердикт 37.2 с, логотип 56.15 с
    "60": dict(DUR=60.0, HIT_VERDICT=37.2, HIT_LOGO=56.15, PUSH=[4.3, 10.45, 16.45, 27.5, 40.15, 47.85],
               HATS=(32.3, 40.1), CREDITS=(52.7, 56.0), OUT="bgm-60s.wav",
               PAD=[(0, 0), (1.8, 0.55), (4.2, 0.6), (4.9, 0.35), (5.6, 0.5), (10.4, 0.5), (11.0, 0.34),
                    (11.7, 0.5), (16.4, 0.5), (17.0, 0.32), (17.7, 0.5), (27.5, 0.5), (28.1, 0.34), (28.9, 0.5)]),
}
cut = CUTS[sys.argv[sys.argv.index("--cut") + 1] if "--cut" in sys.argv else "22"]
DUR, HIT_VERDICT, HIT_LOGO, PUSH = cut["DUR"], cut["HIT_VERDICT"], cut["HIT_LOGO"], cut["PUSH"]
# после вердикта: кольцо → цифры (наезд PUSH[-1]) → логотипы НовГУ (CREDITS) → финал (HIT_LOGO)
P_STATS = PUSH[-1]
BPM = 100
BEAT = 60 / BPM
rng = np.random.default_rng(7)          # фиксированное зерно — трек воспроизводим
t = np.arange(int(SR * DUR)) / SR
out = np.zeros((len(t), 2))


def note(n):                            # MIDI → Гц
    return 440.0 * 2 ** ((n - 69) / 12)


def lowpass(x, f, order=4):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def highpass(x, f, order=4):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def env_curve(points):
    """Огибающая громкости по точкам [(время, значение)], линейно."""
    xs, ys = zip(*points)
    return np.interp(t, xs, ys)


def saw(freq, phase=0.0):
    return 2 * ((t * freq + phase) % 1.0) - 1


# ── Аккорды: Am – F – C – G по 2 такта (такт = 4 доли) ──────────────────────
BAR = 4 * BEAT
chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # A3 C4 E4 / F3.. / C3.. / G3..
pad = np.zeros_like(t)
for i in range(int(np.ceil(DUR / (2 * BAR)))):
    ch = chords[i % 4]
    start, end = i * 2 * BAR, (i + 1) * 2 * BAR
    seg = (t >= start - 0.25) & (t < end + 0.25)
    w = np.clip(np.minimum(t - (start - 0.25), (end + 0.25) - t) / 0.5, 0, 1) * seg   # мягкая смена аккорда
    for n in ch:
        for det in (-0.12, 0.0, 0.11):    # три расстроенных пилы на голос — «широкий» пэд
            pad += w * saw(note(n) * 2 ** (det / 12), phase=rng.random()) / 9
pad = lowpass(pad, 1400)
pad_env = env_curve(cut["PAD"] + [(HIT_VERDICT - 0.05, 0.25), (HIT_VERDICT + 0.1, 0.6),
                     (P_STATS - 0.05, 0.6), (P_STATS + 0.3, 0.3), (P_STATS + 0.85, 0.55),
                     (cut["CREDITS"][0] + 0.1, 0.5), (HIT_LOGO - 0.2, 0.42),
                     (HIT_LOGO + 0.1, 0.8), (DUR - 1.0, 0.7), (DUR, 0.0)])
pad *= pad_env

# ── Суб-бас: корень аккорда, импульс на каждую долю (с 3.4 с) ───────────────
bass = np.zeros_like(t)
roots = [45, 41, 36, 43]                # A2 F2 C2 G2
for k in range(int(DUR / BEAT) + 1):
    bt = k * BEAT
    if bt < 3.4 or any(p - 0.3 < bt < p + 0.6 for p in PUSH) or cut["CREDITS"][0] < bt < cut["CREDITS"][1] or bt > DUR - 0.5:
        continue
    root = roots[int(bt // (2 * BAR)) % 4]
    idx = (t >= bt) & (t < bt + BEAT)
    tt = t[idx] - bt
    bass[idx] += np.sin(2 * np.pi * note(root) * tt) * np.exp(-tt * 5.5) * (1 - np.exp(-tt * 200))
bass = lowpass(bass, 180) * 0.55

# ── Хай-хэт: 8-е доли во время сканирования и вердикта ──────────────────────
hats = np.zeros_like(t)
noise = highpass(rng.standard_normal(len(t)), 7000)
for k in range(int(DUR / (BEAT / 2)) + 1):
    ht = k * BEAT / 2
    if not (cut["HATS"][0] <= ht < cut["HATS"][1]):        # сканирование и вердикт
        continue
    idx = (t >= ht) & (t < ht + 0.08)
    tt = t[idx] - ht
    hats[idx] += noise[idx] * np.exp(-tt * 70) * (0.5 if k % 2 else 0.3)
hats *= 0.22

# ── Подъём шума за 2 с до вердикта ───────────────────────────────────────────
riser = np.zeros_like(t)
idx = (t >= HIT_VERDICT - 2.0) & (t < HIT_VERDICT)
tt = (t[idx] - (HIT_VERDICT - 2.0)) / 2.0
rn = rng.standard_normal(idx.sum())
riser[idx] = bandish = rn * tt ** 2.2
riser = highpass(riser, 1500) * 0.14

# ── Удар на вердикте и на логотипе: низкий «бум» ────────────────────────────
def boom(at, gain):
    b = np.zeros_like(t)
    idx = (t >= at) & (t < at + 1.6)
    tt = t[idx] - at
    f = 55 + 70 * np.exp(-tt * 18)       # питч падает — классический кинематографичный удар
    b[idx] = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.2) * gain
    return b
booms = boom(HIT_VERDICT, 0.6) + boom(HIT_LOGO, 0.55)

# ── Сведение + реверб ───────────────────────────────────────────────────────
mono_dry = bass + booms
stereo_src = pad + hats + riser
ir_len = int(SR * 1.9)
ir_t = np.arange(ir_len) / SR
for ch, seed in ((0, 11), (1, 23)):
    ir = np.random.default_rng(seed).standard_normal(ir_len) * np.exp(-ir_t * 3.0)
    ir /= np.sqrt((ir ** 2).sum())
    wet = fftconvolve(stereo_src, ir)[: len(t)]
    out[:, ch] = stereo_src * 0.75 + wet * 0.45 + mono_dry

out = np.tanh(out * 1.1)                 # мягкое ограничение пиков
fade = np.clip(np.minimum(t / 0.05, (DUR - t) / 0.6), 0, 1)
out *= fade[:, None]
out /= np.max(np.abs(out)) / 0.89        # нормализация до −1 dBFS

path = Path(__file__).resolve().parents[1] / "assets" / "audio" / cut["OUT"]
path.parent.mkdir(parents=True, exist_ok=True)
wavfile.write(path, SR, (out * 32767).astype(np.int16))
print(f"✓ {path} ({DUR} с, {SR} Гц, стерео)")
