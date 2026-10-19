"""Одноразовая перестройка index.html из 20-секундной версии в 30-секундную:
тур по настоящему сайту (3.4–10.5), сцена редактора сдвигается на +6.8 с,
цифры (22.6), логотипы НовГУ (24.4), финал (26.8–30.4).
"""
import re
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "index.html"
s = P.read_text(encoding="utf-8")


def rep(a, b):
    global s
    assert a in s, a[:80]
    s = s.replace(a, b, 1)


# ── длительность ──
rep('data-duration="20.4" data-width="1920"', 'data-duration="30.4" data-width="1920"')
rep('const W = 1920, H = 1080, TOTAL = 20.4;', 'const W = 1920, H = 1080, TOTAL = 30.4;')

# ── CSS новых сцен ──
rep('    </style>', '''
      /* сцена «сайт»: окно браузера с настоящими снимками сайта */
      #browser { position: absolute; left: 240px; top: 150px; width: 1440px; height: 842px; border-radius: 22px;
        overflow: hidden; background: #000;
        box-shadow: 0 60px 140px -30px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.10); }
      #br-bar { position: absolute; left: 0; right: 0; top: 0; height: 52px; background: #1c1c1e;
        border-bottom: 1px solid rgba(255,255,255,0.06); }
      #br-bar .dot { top: 18px; }
      #br-url { position: absolute; left: 520px; top: 11px; width: 400px; height: 30px; border-radius: 9px;
        background: #2c2c2e; color: #a1a1a6; font-size: 17px; line-height: 30px; text-align: center; }
      #br-view { position: absolute; left: 0; top: 52px; width: 1440px; height: 790px; overflow: hidden; }
      #br-nav { position: absolute; left: 0; top: 0; width: 1440px; height: 61px; z-index: 2; }
      #br-strip { position: absolute; left: 0; top: 61px; width: 1440px; }
      #br-strip img { display: block; width: 1440px; height: 839px; }
      .site-cap { position: absolute; left: 0; right: 0; top: 56px; text-align: center;
        font-size: 46px; font-weight: 700; letter-spacing: -0.02em; opacity: 0; }

      /* сцена «НовГУ»: логотипы университета и института */
      #cr-title { position: absolute; left: 0; right: 0; top: 250px; text-align: center;
        font-size: 54px; font-weight: 700; letter-spacing: -0.03em; }
      #cr-logos { position: absolute; left: 0; right: 0; top: 390px; height: 300px;
        display: flex; align-items: center; justify-content: center; gap: 84px; }
      #cr-novsu { display: block; height: 168px; width: auto; }
      #cr-line { width: 1px; height: 220px; background: rgba(255,255,255,0.18); }
      #cr-emblem { display: block; height: 300px; width: auto; }
      #cr-sub { position: absolute; left: 0; right: 0; top: 770px; text-align: center; font-size: 30px; color: #a1a1a6; }
    </style>''')

# ── HTML: сцена «сайт» перед сценой 2 ──
rep('      <!-- ── Сцена 2: редактор → сканирование → вердикт ── -->', '''      <!-- ── Сцена «сайт»: тур по настоящему сайту ── -->
      <section id="ss" class="clip scene" data-start="3.4" data-duration="7.1" data-track-index="4">
        <div id="camS" class="cam">
          <div id="ss-inner">
            <div id="persp-s" style="position:absolute;left:0;top:0;width:1920px;height:1080px;perspective:1800px;">
              <div id="browser">
                <div id="br-bar">
                  <span class="dot" style="left:22px;background:#ff5f57"></span>
                  <span class="dot" style="left:46px;background:#febc2e"></span>
                  <span class="dot" style="left:70px;background:#28c840"></span>
                  <div id="br-url">localhost:8000 — CodeCheck</div>
                </div>
                <div id="br-view">
                  <div id="br-strip">
                    <img src="assets/site/page-top.jpg" alt="" />
                    <img src="assets/site/page-how.jpg" alt="" />
                    <img src="assets/site/page-quality.jpg" alt="" />
                    <img src="assets/site/page-check.jpg" alt="" />
                  </div>
                  <img id="br-nav" src="assets/site/nav.png" alt="" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div id="cap-a" class="site-cap">Сайт для преподавателей</div>
        <div id="cap-b" class="site-cap">Понятно, как это работает</div>
        <div id="cap-c" class="site-cap">Честные метрики качества</div>
      </section>

      <!-- ── Сцена 2: редактор → сканирование → вердикт ── -->''')
rep('<section id="s2" class="clip scene" data-start="3.4" data-duration="12.85"',
    '<section id="s2" class="clip scene" data-start="10.2" data-duration="12.85"')

# ── HTML: сцена 3 делится на цифры / НовГУ / финал ──
a = s.index('      <!-- ── Сцена 3: доказательства и призыв ── -->')
b = s.index('    </div>\n\n    <script>')
s = s[:a] + '''      <!-- ── Сцена 3: цифры качества ── -->
      <section id="s3" class="clip scene" data-start="22.6" data-duration="2.2" data-track-index="3">
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
      <section id="s4" class="clip scene" data-start="24.4" data-duration="2.7" data-track-index="4">
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
      <section id="s5" class="clip scene" data-start="26.8" data-duration="3.6" data-track-index="3">
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

# ── скрипт: камера принимает шкалу времени ──
rep('function makeCamera(el, init, driftAmp) {', 'function makeCamera(el, init, driftAmp, T = tl) {')
rep('tl.to(cam, { p: Math.PI * 2, duration: TOTAL, ease: "none", onUpdate: write }, 0);',
    'T.to(cam, { p: Math.PI * 2, duration: TOTAL, ease: "none", onUpdate: write }, 0);')
rep('tl.to(cam, { ...to, duration: dur, ease, onUpdate: write }, at) };',
    'T.to(cam, { ...to, duration: dur, ease, onUpdate: write }, at) };')

# ── свечения под новые времена ──
rep('tl.to("#glow-red", { opacity: 1, duration: 1.2, ease: "sine.inOut" }, 12.4);',
    'tl.to("#glow-red", { opacity: 1, duration: 1.2, ease: "sine.inOut" }, 19.2);')
rep('tl.to("#glow-red", { opacity: 0, duration: 1.0, ease: "sine.inOut" }, 15.6);',
    'tl.to("#glow-red", { opacity: 0, duration: 1.0, ease: "sine.inOut" }, 22.4);')
rep('tl.to("#glow-blue", { x: 140, y: -40, duration: 6, ease: "sine.inOut" }, 12);',
    'tl.to("#glow-blue", { x: 140, y: -40, duration: 6, ease: "sine.inOut" }, 18.8);')

# ── сцена 2 → вложенная шкала со сдвигом +6.8 с (исходные времена сохраняются) ──
a = s.index('      // ═══ Сцена 2:')
b = s.index('      // ═══ Сцена 3:')
block = s[a:b]
block = block.replace(
    'const c2 = makeCamera(document.getElementById("cam2"), { s: 1.25, fx: 960, fy: 560 }, 4);',
    'const T2 = gsap.timeline();   // времена ниже — как в 20-секундной версии; весь блок сдвинут на +6.8 с\n'
    '      const c2 = makeCamera(document.getElementById("cam2"), { s: 1.25, fx: 960, fy: 560 }, 4, T2);')
block = re.sub(r'\btl\.', 'T2.', block)
block = block.rstrip() + '\n      tl.add(T2, 6.8);\n\n'
s = s[:a] + block + s[b:]

# ── сцены 3–5 ──
a = s.index('      // ═══ Сцена 3:')
b = s.index('      window.__timelines["main"] = tl;')
s = s[:a] + '''      // ═══ Сцена 3: цифры качества (22.6 – 24.8) ═══
      const c3 = makeCamera(document.getElementById("cam3"), { s: 1.18, fx: 960, fy: 540 }, 3);
      tl.fromTo("#s3-inner", { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power2.out" }, 22.6);
      c3.move({ s: 1, fx: 960, fy: 540 }, 22.6, 1.6, "power3.out");
      tl.fromTo("#stats-title", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 22.75);
      tl.fromTo(".card", { opacity: 0, y: 50 }, { opacity: 1, y: 0, duration: 0.7, ease: "power3.out", stagger: 0.15 }, 22.85);
      const n = { a: 0, b: 0 }, n1 = document.getElementById("n1"), n2 = document.getElementById("n2");
      tl.to(n, { a: 96.3, b: 5.4, duration: 1.2, ease: "power2.out",
        onUpdate: () => { n1.textContent = fmt(n.a, 1); n2.textContent = fmt(n.b, 1); } }, 23.0);
      tl.to("#s3-inner", { opacity: 0, y: -30, filter: "blur(8px)", duration: 0.45, ease: "power2.in" }, 24.35);

      // ═══ Сцена 4: проект студентов НовГУ (24.4 – 27.1) ═══
      const c4 = makeCamera(document.getElementById("cam4"), { s: 1.06, fx: 960, fy: 540 }, 2);
      c4.move({ s: 1, fx: 960, fy: 540 }, 24.4, 2.6, "sine.out");     // медленный отъезд
      tl.fromTo("#cr-title", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.7, ease: "power3.out" }, 24.55);
      tl.fromTo("#cr-novsu", { opacity: 0, x: -40, filter: "blur(8px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.9, ease: "power3.out" }, 24.75);
      tl.fromTo("#cr-line", { scaleY: 0 }, { scaleY: 1, duration: 0.7, ease: "power3.out" }, 24.9);
      tl.fromTo("#cr-emblem", { opacity: 0, x: 40, filter: "blur(8px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.9, ease: "power3.out" }, 24.95);
      tl.fromTo("#cr-sub", { opacity: 0 }, { opacity: 1, duration: 0.6 }, 25.3);
      tl.to("#s4-inner", { opacity: 0, filter: "blur(8px)", duration: 0.4, ease: "power2.in" }, 26.7);

      // ═══ Сцена 5: призыв (26.8 – 30.4) ═══
      const c5 = makeCamera(document.getElementById("cam5"), { s: 1.0, fx: 960, fy: 540 }, 3);
      tl.fromTo("#end-logo", { opacity: 0, scale: 0.6, rotation: -12 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.7, ease: "back.out(1.6)" }, 26.95);
      tl.fromTo("#end-name", { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.6, ease: "power3.out" }, 27.05);
      tl.fromTo("#end-sub", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 27.25);
      tl.fromTo("#end-btn", { opacity: 0, y: 20, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out" }, 27.45);
      tl.fromTo("#end-foot", { opacity: 0 }, { opacity: 1, duration: 0.6 }, 27.65);
      tl.set("#cursor3", { x: 1500, y: 900 }, 0);
      tl.fromTo("#cursor3", { opacity: 0 }, { opacity: 1, duration: 0.25 }, 27.75);
      tl.to("#cursor3", { x: 952, y: 624, duration: 0.85, ease: "power3.inOut" }, 27.85);
      tl.to("#cursor3", { scale: 0.86, duration: 0.09, yoyo: true, repeat: 1, transformOrigin: "10% 10%" }, 28.75);
      tl.to("#end-btn", { scale: 0.95, duration: 0.09, yoyo: true, repeat: 1 }, 28.75);
      tl.fromTo("#ripple3", { x: 915, y: 587, scale: 0.3, opacity: 0.9 }, { immediateRender: false, scale: 1.5, opacity: 0, duration: 0.6, ease: "power2.out" }, 28.77);
      c5.move({ s: 1.06, fx: 960, fy: 520 }, 26.9, 3.4, "sine.inOut");    // финальный медленный наезд

''' + s[b:]

# ── сцена «сайт» ──
rep('      // ═══ Сцена 2:', '''      // ═══ Сцена «сайт»: тур по настоящему сайту (3.4 – 10.5) ═══
      const cS = makeCamera(document.getElementById("camS"), { s: 1.25, fx: 960, fy: 560 }, 4);
      tl.fromTo("#ss-inner", { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power2.out" }, 3.4);
      cS.move({ s: 1, fy: 571 }, 3.4, 1.4, "power3.out");
      tl.fromTo("#browser", { rotationX: 22, rotationY: -16, y: 60, scale: 0.86 },
        { rotationX: 0, rotationY: 0, y: 0, scale: 1, duration: 1.5, ease: "power3.out" }, 3.45);
      const cap = (id, inAt, outAt) => {
        tl.fromTo(id, { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, inAt);
        tl.to(id, { opacity: 0, y: -14, duration: 0.4, ease: "power2.in" }, outAt);
      };
      cap("#cap-a", 4.0, 5.55); cap("#cap-b", 6.45, 7.55); cap("#cap-c", 8.35, 9.15);
      // главная страница: наезд на демо-окно сайта
      cS.move({ s: 1.32, fx: 1222, fy: 660 }, 4.6, 1.0, "sine.inOut");
      // прокрутка → «Как это работает»
      cS.move({ s: 1, fx: 960, fy: 571 }, 5.6, 1.0, "power3.inOut");
      tl.to("#br-strip", { y: -839, duration: 0.95, ease: "power3.inOut" }, 5.7);
      cS.move({ s: 1.12, fx: 900, fy: 700 }, 6.6, 0.9, "sine.inOut");
      // прокрутка → «Качество моделей», наезд на 96,3%
      cS.move({ s: 1, fx: 960, fy: 571 }, 7.5, 0.85, "power3.inOut");
      tl.to("#br-strip", { y: -1678, duration: 0.95, ease: "power3.inOut" }, 7.6);
      cS.move({ s: 1.5, fx: 600, fy: 646 }, 8.35, 0.8, "power3.inOut");
      // прокрутка → «Проверьте код» и наезд сквозь поле кода
      cS.move({ s: 1, fx: 960, fy: 571 }, 9.15, 0.6, "power3.inOut");
      tl.to("#br-strip", { y: -2517, duration: 0.75, ease: "power3.inOut" }, 9.15);
      cS.move({ s: 2.9, fx: 960, fy: 700 }, 9.8, 0.7, "power3.in");
      tl.to("#ss-inner", { opacity: 0, filter: "blur(14px)", duration: 0.4, ease: "power2.in" }, 10.1);

      // ═══ Сцена 2:''')

P.write_text(s, encoding="utf-8")
print("✓ index.html перестроен на 30.4 с")
