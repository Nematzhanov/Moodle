---
version: alpha
name: CodeCheck — Frame (video / frame layer)
description: >
  Тёмная продуктовая система в духе сайта CodeCheck и референсов (тёмный UI, наезды камеры на детали).
  Чёрный фон, графитовые поверхности, один электрический синий как основной акцент, фиолетовый —
  только в градиенте бренда, красный — только для сигнала «ИИ». Inter для текста, JetBrains Mono для кода.
  Основано на пресете code-editorial (вручную переведён в тёмную схему: бренд тёмный).
unit: the frame — 1920×1080
principle: один фокус в кадре · камера ведёт взгляд · цифры только реальные

colors:
  canvas: "#000000"        # фон всего ролика
  surface: "#141416"       # карточки, панели
  surface-2: "#1c1c1e"     # приподнятые элементы
  code-bg: "#0f1117"       # окно редактора
  code-bar: "#161922"      # шапка окна редактора
  ink: "#f5f5f7"           # основной текст
  ink-2: "#a1a1a6"         # вторичный текст
  ink-3: "#6e6e73"         # подписи, служебное
  accent: "#2997ff"        # главный акцент: кнопки, линия сканирования, кольцо в норме
  accent-2: "#9d8cff"      # только в паре с accent — градиент бренда
  danger: "#ff453a"        # сигнал «ИИ»: подсветка строк, кольцо 91%
  warn: "#ff9f0a"          # «тёплые» строки, средняя вероятность
  success: "#30d158"       # «человек»
  hairline: "rgba(255,255,255,0.10)"
  syntax-keyword: "#ff7ab2"
  syntax-type: "#6bdfff"
  syntax-string: "#fc6a5d"
  syntax-comment: "#6c7986"
  syntax-preproc: "#a167e6"

typography:
  display:    { fontFamily: "Inter", px: 112, weight: 700, lineHeight: 1.02, tracking: "-0.035em" }
  headline:   { fontFamily: "Inter", px: 76,  weight: 700, lineHeight: 1.06, tracking: "-0.03em" }
  number-hero:{ fontFamily: "Inter", px: 220, weight: 700, lineHeight: 0.9,  tracking: "-0.05em" }
  lead:       { fontFamily: "Inter", px: 34,  weight: 400, lineHeight: 1.4 }
  label:      { fontFamily: "Inter", px: 26,  weight: 500, lineHeight: 1.3 }
  eyebrow:    { fontFamily: "Inter", px: 26,  weight: 600, tracking: "0.02em" }
  code:       { fontFamily: "JetBrains Mono", px: 30, weight: 400, lineHeight: 1.75 }
  mono-label: { fontFamily: "JetBrains Mono", px: 22, weight: 500 }

spacing:
  frame-pad: "96px"
  radius-card: "28px"
  radius-window: "26px"
  radius-pill: "9999px"

effects:
  window-shadow: "0 60px 140px -30px rgba(0,0,0,0.75), 0 0 0 1px rgba(255,255,255,0.08)"
  glow-accent: "radial-gradient(closest-side, rgba(41,151,255,0.22), transparent 70%)"
  glow-danger: "radial-gradient(closest-side, rgba(255,69,58,0.20), transparent 70%)"
  brand-gradient: "linear-gradient(100deg, #2997ff, #9d8cff)"

components:
  code-window:
    description: "Окно редактора как на сайте: фон code-bg, шапка code-bar с тремя точками (#ff5f57 #febc2e #28c840) и именем файла mono-label ink-3, тень window-shadow. Код — code, подсветка syntax-*."
  scanline:
    description: "Горизонтальная линия сканирования: 2px accent + мягкий градиент accent@18%→55% над ней высотой ~110px. Идёт сверху вниз по окну кода."
  line-highlight:
    description: "Подозрительная строка: фон danger@14% + слева 4px полоса danger. Тёплая — warn@10% + 4px warn."
  probability-ring:
    description: "Кольцо вероятности: трек ink@14% толщиной 14px, заполнение danger (для ИИ) со скруглёнными концами; число внутри number-hero, подпись label ink-3."
  stat-card:
    description: "Карточка цифры: surface, radius-card, число Inter 700 с brand-gradient, подпись label ink-2 + мелкая ink-3."
  cta-button:
    description: "Белая капсула (ink фон, canvas текст) Inter 600, radius-pill. Единственная кнопка в кадре."
  cursor:
    description: "Курсор macOS (белый с чёрным контуром) — ведёт взгляд к кнопке/строке, клик = короткое сжатие 0.92."
  logo:
    description: "assets/codecheck-logo.svg — квадрат с brand-gradient и «< >»; рядом слово CodeCheck Inter 600."

rules:
  - "Один фокус в кадре; камера (scale/translate обёртки сцены) подводит к нему плавно, ease power2/power3.inOut, без рывков."
  - "Красный (danger) появляется только как сигнал ИИ. Акцент синий. Фиолетовый — только в градиенте бренда."
  - "Заголовки короткие (2–6 слов), сентенс-кейс, по-русски."
  - "Цифры только из источника: 96,3% точность (214 примеров), 5,4% ложных (6 из 111), 91% — пример демо."
  - "Фон всегда canvas; мягкое свечение glow-* допустимо за фокусом."
---

# CodeCheck — визуальный язык ролика

Тёмная сцена, где светится только то, что важно сейчас. Интерфейс CodeCheck показан крупно и чисто,
камера медленно наезжает на деталь (строку кода, кольцо, цифру) и отъезжает к общему плану —
как в референсах. Текст — короткие заголовки поверх, без нагромождения.
