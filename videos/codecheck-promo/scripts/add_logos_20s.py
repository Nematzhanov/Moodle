"""Прежний 20-секундный ролик + сцена с логотипами НовГУ → index.html на 22.7 с.

Сцены: вопрос (0–3.75) · редактор/сканирование/вердикт (3.4–16.25) · цифры (15.8–17.8) ·
«Проект студентов НовГУ» (17.6–20.1) · финал (19.9–22.7, на +1.8 с позже прежнего).
Запуск: python3 scripts/add_logos_20s.py <index-20s.html>
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
s = re.sub(r' data-hf-id="[^"]*"', "", Path(sys.argv[1]).read_text(encoding="utf-8"))
TOTAL = 22.7


def rep(a, b):
    global s
    assert a in s, a[:80]
    s = s.replace(a, b, 1)


rep('data-duration="20.4" data-width="1920"', f'data-duration="{TOTAL}" data-width="1920"')
rep('const W = 1920, H = 1080, TOTAL = 20.4;', f'const W = 1920, H = 1080, TOTAL = {TOTAL};')

rep('    </style>', '''
      /* сцена «НовГУ»: логотипы университета и института */
      #cr-title { position: absolute; left: 0; right: 0; top: 220px; text-align: center;
        font-size: 54px; font-weight: 700; letter-spacing: -0.03em; }
      #cr-logos { position: absolute; left: 0; right: 0; top: 360px; height: 380px;
        display: flex; align-items: center; justify-content: center; gap: 84px; }
      #cr-novsu { display: block; height: 206px; width: auto; }
      #cr-line { width: 1px; height: 260px; background: rgba(255,255,255,0.18); }
      #cr-emblem { display: block; height: 360px; width: auto; }
      #cr-sub { position: absolute; left: 0; right: 0; top: 790px; text-align: center; font-size: 30px; color: #a1a1a6; }
    </style>''')

# ── HTML: сцена 3 → цифры / НовГУ / финал ──
a = s.index('      <!-- ── Сцена 3: доказательства и призыв ── -->')
b = s.index('    </div>\n\n    <script>')
s = s[:a] + '''      <!-- ── Сцена 3: цифры качества ── -->
      <section id="s3" class="clip scene" data-start="15.8" data-duration="2.0" data-track-index="3">
        <div id="cam3" class="cam">
          <div id="s3-inner">
            <div id="stats">
              <div id="stats-title">Проверено на реальном коде</div>
              <div id="card1" class="card">
                <div class="card-num"><span id="n1">0</span>%</div>
                <div class="card-label">точность модели</div>
                <div class="card-sub">на тестовой выборке из 214 программ</div>
              </div>
              <div id="card2" class="card">
                <div class="card-num"><span id="n2">0</span>%</div>
                <div class="card-label">ложных срабатываний</div>
                <div class="card-sub">на коде людей: 6 из 111</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Сцена 4: проект студентов НовГУ ── -->
      <section id="s4" class="clip scene" data-start="17.6" data-duration="2.5" data-track-index="4">
        <div id="cam4" class="cam">
          <div id="s4-inner">
            <div id="cr-title">Проект студентов НовГУ</div>
            <div id="cr-logos">
              <img id="cr-novsu" src="assets/logos/novsu-white.png" alt="" />
              <div id="cr-line"></div>
              <img id="cr-emblem" src="assets/logos/ieis-emblem.png" alt="" />
            </div>
            <div id="cr-sub">Направление «Информатика и вычислительная техника» · 2026</div>
          </div>
        </div>
      </section>

      <!-- ── Сцена 5: призыв ── -->
      <section id="s5" class="clip scene" data-start="19.9" data-duration="2.8" data-track-index="3">
        <div id="cam5" class="cam">
          <div id="s5-inner">
            <div id="end">
              <div id="end-row">
                <img id="end-logo" src="assets/codecheck-logo.svg" alt="" />
                <div id="end-name">CodeCheck</div>
              </div>
              <div id="end-sub">Детектор ИИ-кода на C++ для преподавателей</div>
              <div id="end-btn">Проверьте код</div>
              <div id="end-foot">Новгородский государственный университет имени Ярослава Мудрого · 2026</div>
            </div>
            <svg id="cursor3" class="cursor" viewBox="0 0 44 54">
              <path d="M4 3 L4 41 L14 32 L21 49 L28 46 L21 30 L34 30 Z" fill="#fff" stroke="#000" stroke-width="2.5" stroke-linejoin="round" />
            </svg>
            <div id="ripple3" class="ripple"></div>
          </div>
        </div>
      </section>
''' + s[b:]

# ── скрипт: сцены 3–5 ──
a = s.index('      // ═══ Сцена 3:')
b = s.index('      window.__timelines["main"] = tl;')
s = s[:a] + '''      // ═══ Сцена 3: цифры качества (15.8 – 17.8) ═══
      const c3 = makeCamera(document.getElementById("cam3"), { s: 1.18, fx: 960, fy: 540 }, 3);
      tl.fromTo("#s3-inner", { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power2.out" }, 15.8);
      c3.move({ s: 1, fx: 960, fy: 540 }, 15.8, 1.6, "power3.out");
      tl.fromTo("#stats-title", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 15.95);
      tl.fromTo(".card", { opacity: 0, y: 50 }, { opacity: 1, y: 0, duration: 0.7, ease: "power3.out", stagger: 0.15 }, 16.05);
      const n = { a: 0, b: 0 }, n1 = document.getElementById("n1"), n2 = document.getElementById("n2");
      tl.to(n, { a: 96.3, b: 5.4, duration: 1.2, ease: "power2.out",
        onUpdate: () => { n1.textContent = fmt(n.a, 1); n2.textContent = fmt(n.b, 1); } }, 16.2);
      tl.to("#s3-inner", { opacity: 0, y: -30, filter: "blur(8px)", duration: 0.45, ease: "power2.in" }, 17.35);

      // ═══ Сцена 4: проект студентов НовГУ (17.6 – 20.1) ═══
      const c4 = makeCamera(document.getElementById("cam4"), { s: 1.06, fx: 960, fy: 540 }, 2);
      c4.move({ s: 1, fx: 960, fy: 540 }, 17.6, 2.4, "sine.out");     // медленный отъезд
      tl.fromTo("#cr-title", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.7, ease: "power3.out" }, 17.7);
      tl.fromTo("#cr-novsu", { opacity: 0, x: -40, filter: "blur(8px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.9, ease: "power3.out" }, 17.9);
      tl.fromTo("#cr-line", { scaleY: 0 }, { scaleY: 1, duration: 0.7, ease: "power3.out" }, 18.05);
      tl.fromTo("#cr-emblem", { opacity: 0, x: 40, filter: "blur(8px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.9, ease: "power3.out" }, 18.1);
      tl.fromTo("#cr-sub", { opacity: 0 }, { opacity: 1, duration: 0.6 }, 18.45);
      tl.to("#s4-inner", { opacity: 0, filter: "blur(8px)", duration: 0.4, ease: "power2.in" }, 19.7);

      // ═══ Сцена 5: призыв (19.9 – 22.7) ═══
      const c5 = makeCamera(document.getElementById("cam5"), { s: 1.0, fx: 960, fy: 540 }, 3);
      tl.fromTo("#end-logo", { opacity: 0, scale: 0.6, rotation: -12 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.7, ease: "back.out(1.6)" }, 19.9);
      tl.fromTo("#end-name", { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.6, ease: "power3.out" }, 20.0);
      tl.fromTo("#end-sub", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 20.2);
      tl.fromTo("#end-btn", { opacity: 0, y: 20, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out" }, 20.4);
      tl.fromTo("#end-foot", { opacity: 0 }, { opacity: 1, duration: 0.6 }, 20.6);
      tl.set("#cursor3", { x: 1500, y: 900 }, 0);
      tl.fromTo("#cursor3", { opacity: 0 }, { opacity: 1, duration: 0.25 }, 20.55);
      tl.to("#cursor3", { x: 952, y: 624, duration: 0.75, ease: "power3.inOut" }, 20.65);
      tl.to("#cursor3", { scale: 0.86, duration: 0.09, yoyo: true, repeat: 1, transformOrigin: "10% 10%" }, 21.45);
      tl.to("#end-btn", { scale: 0.95, duration: 0.09, yoyo: true, repeat: 1 }, 21.45);
      tl.fromTo("#ripple3", { x: 915, y: 587, scale: 0.3, opacity: 0.9 }, { immediateRender: false, scale: 1.5, opacity: 0, duration: 0.6, ease: "power2.out" }, 21.47);
      c5.move({ s: 1.05, fx: 960, fy: 520 }, 19.9, 2.8, "sine.inOut");    // финальный медленный наезд

''' + s[b:]

# ── звук ──
cues = [("sfx-whoosh-1", "whoosh", 3.02, 0.45), ("sfx-whoosh-2", "whoosh-short", 3.5, 0.3), ("sfx-typing", "typing", 4.1, 0.22),
        ("sfx-click-1", "click", 7.4, 0.55), ("sfx-scan", "glitch-3", 7.7, 0.18), ("sfx-ping-1", "ping", 9.6, 0.28),
        ("sfx-impact-1", "impact-bass-1", 12.6, 0.35), ("sfx-ping-2", "ping", 13.95, 0.3), ("sfx-whoosh-3", "whoosh", 15.52, 0.45),
        ("sfx-pop-1", "pop", 16.05, 0.3), ("sfx-pop-2", "pop", 16.2, 0.3), ("sfx-whoosh-4", "whoosh-short", 17.5, 0.25),
        ("sfx-sparkle-1", "sparkle", 17.95, 0.18), ("sfx-impact-2", "impact-bass-1", 19.9, 0.35),
        ("sfx-sparkle-2", "sparkle", 19.95, 0.22), ("sfx-click-2", "click", 21.45, 0.55)]
lines = ['      <!-- ── звук: музыка (assets/audio/bgm.wav, scripts/make_music.py --cut 22) и звуки интерфейса ── -->',
         f'      <audio id="bgm" src="assets/audio/bgm.wav" data-start="0" data-duration="{TOTAL}" data-track-index="10" data-volume="0.55"></audio>']
for i, (id_, f, st, v) in enumerate(cues):
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                       str(ROOT / "assets" / "sfx" / f"{f}.mp3")]).decode())
    lines.append(f'      <audio id="{id_}" src="assets/sfx/{f}.mp3" data-start="{st}" data-duration="{min(d, TOTAL - st):.2f}" '
                 f'data-track-index="{11 + i % 3}" data-volume="{v}"></audio>')
a = s.index('      <!-- ── звук:')
b = s.index('      <!-- ── Сцена 1: вопрос ── -->')
s = s[:a] + "\n".join(lines) + "\n\n" + s[b:]

(ROOT / "index.html").write_text(s, encoding="utf-8")
print(f"✓ index.html: прежний ролик + логотипы НовГУ, {TOTAL} с")
