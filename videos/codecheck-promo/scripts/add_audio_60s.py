"""Звук для 60-секундной светлой версии: музыка bgm-60s.wav + звуки интерфейса по монтажным точкам.

Заменяет блок <!--AUDIO--> (или прежний блок звука) в index.html. Дорожки звуков раздаются так,
чтобы клипы на одной дорожке не перекрывались.
Запуск: python3 scripts/add_audio_60s.py
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOTAL = 60.0
CUES = [  # (файл, время, громкость)
    ("whoosh", 4.27, 0.45), ("whoosh-short", 4.9, 0.3), ("pop", 5.25, 0.3),          # вопрос → 24%
    ("whoosh-short", 7.7, 0.3), ("pop", 8.45, 0.3), ("whoosh", 10.42, 0.42),        # панорама → 89%
    ("glitch-3", 11.5, 0.1), ("ping", 12.85, 0.26), ("impact-bass-1", 13.9, 0.32),  # проверка → штамп
    ("whoosh", 16.42, 0.42),
    ("whoosh-short", 19.65, 0.22), ("whoosh-short", 22.05, 0.22),                    # прокрутка сайта
    ("whoosh-short", 24.3, 0.22), ("whoosh-short", 26.4, 0.22), ("whoosh", 27.5, 0.42),
    ("typing", 28.7, 0.22), ("click", 32.0, 0.55), ("glitch-3", 32.3, 0.18),          # редактор
    ("ping", 34.2, 0.28), ("impact-bass-1", 37.2, 0.35), ("ping", 38.55, 0.3), ("whoosh", 40.12, 0.45),
    ("pop", 40.9, 0.25), ("pop", 42.25, 0.25), ("pop", 43.65, 0.25),                  # конвейер
    ("sparkle", 45.25, 0.2), ("whoosh-short", 46.25, 0.25), ("whoosh", 47.82, 0.4),
    ("pop", 48.55, 0.3), ("pop", 48.7, 0.3), ("pop", 48.85, 0.3),                     # цифры
    ("whoosh-short", 52.7, 0.25), ("sparkle", 53.15, 0.18),                           # НовГУ
    ("impact-bass-1", 56.1, 0.35), ("sparkle", 56.15, 0.22), ("click", 58.1, 0.55),   # финал
]


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                          "csv=p=0", str(ROOT / "assets" / "sfx" / f"{f}.mp3")]).decode())


lines = ['      <!-- ── звук: музыка (scripts/make_music.py --cut 60) и звуки интерфейса (scripts/add_audio_60s.py) ── -->',
         f'      <audio id="bgm" src="assets/audio/bgm-60s.wav" data-start="0" data-duration="{TOTAL}" '
         'data-track-index="10" data-volume="0.55"></audio>']
busy = {11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0}
for i, (f, st, v) in enumerate(CUES):
    d = min(dur(f), TOTAL - st)
    track = next(t for t in busy if busy[t] <= st)
    busy[track] = st + d + 0.01
    lines.append(f'      <audio id="sfx-{i + 1:02d}-{f}" src="assets/sfx/{f}.mp3" data-start="{st}" data-duration="{d:.2f}" '
                 f'data-track-index="{track}" data-volume="{v}"></audio>')

p = ROOT / "index.html"
s = p.read_text(encoding="utf-8")
block = "\n".join(lines)
if "<!--AUDIO-->" in s:
    s = s.replace("      <!--AUDIO-->", block, 1)
else:
    s = re.sub(r"      <!-- ── звук:.*?(?=\n\n      <!-- ── 1\.)", lambda _: block, s, count=1, flags=re.S)
p.write_text(s, encoding="utf-8")
print(f"✓ звук: {len(CUES)} эффектов + музыка, {TOTAL} с")
