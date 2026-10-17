// Проверка идёт через сервер src/server.py (модель C++). Если сайт открыт без сервера
// (файлом или на GitHub Pages), включается демо-режим с имитацией результата.

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const RING_LEN = 327; // длина окружности r=52 (2πr ≈ 326.7)
const $ = (sel) => document.querySelector(sel);

/* ── тема ─────────────────────────────────────────────────────────────── */
$("#theme").addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try { localStorage.setItem("theme", next); } catch (e) {}
});

/* ── общие функции анимации ──────────────────────────────────────────── */
function countUp(el, to, decimals = 0, duration = 1200) {
  if (REDUCED) { el.textContent = to.toFixed(decimals).replace(".", ","); return; }
  const start = performance.now();
  const step = (now) => {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = (to * eased).toFixed(decimals).replace(".", ",");
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function setRing(circle, pct) {
  circle.style.strokeDashoffset = String(RING_LEN * (1 - pct / 100));
}

function toneFor(ai) {
  if (ai >= 80) return ["Почти точно написан ИИ", "danger"];
  if (ai >= 60) return ["Скорее всего написан ИИ", "danger"];
  if (ai >= 40) return ["Сложно определить", "warn"];
  if (ai >= 20) return ["Скорее всего написан человеком", "ok"];
  return ["Почти точно написан человеком", "ok"];
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function runScan(scanEl, distance, seconds) {
  if (REDUCED) return Promise.resolve();
  scanEl.style.setProperty("--scan-to", distance + "px");
  scanEl.style.setProperty("--scan-time", seconds + "s");
  scanEl.classList.remove("run");
  void scanEl.offsetWidth; // перезапуск анимации
  scanEl.classList.add("run");
  return sleep(seconds * 1000);
}

/* ── появление при прокрутке и счётчики ──────────────────────────────── */
const revealObserver = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    e.target.classList.add("visible");
    e.target.querySelectorAll(".stat-num").forEach((n) => {
      countUp(n, parseFloat(n.dataset.count), parseInt(n.dataset.decimals, 10), 1400);
    });
    revealObserver.unobserve(e.target);
  }
}, { threshold: 0.18 });
document.querySelectorAll(".reveal").forEach((el) => revealObserver.observe(el));

/* ── демо на первом экране: что делает сервис ────────────────────────── */
// Строки демо-кода: [html, «температура» строки для подсветки]
const DEMO_LINES = [
  ['<span class="tk-p">#include</span> <span class="tk-s">&lt;vector&gt;</span>', 0],
  ['<span class="tk-p">#include</span> <span class="tk-s">&lt;algorithm&gt;</span>', 0],
  ['', 0],
  ['<span class="tk-c">// Returns the k largest elements in descending order.</span>', 2],
  ['<span class="tk-t">std::vector</span>&lt;<span class="tk-k">int</span>&gt; topK(<span class="tk-k">const</span> <span class="tk-t">std::vector</span>&lt;<span class="tk-k">int</span>&gt;&amp; nums, <span class="tk-k">int</span> k) {', 1],
  ['    <span class="tk-t">std::vector</span>&lt;<span class="tk-k">int</span>&gt; result(nums.begin(), nums.end());', 2],
  ['    <span class="tk-t">std::sort</span>(result.begin(), result.end(), <span class="tk-t">std::greater</span>&lt;<span class="tk-k">int</span>&gt;());', 2],
  ['    <span class="tk-c">// Ensure k does not exceed the vector size.</span>', 2],
  ['    <span class="tk-k">if</span> (k &gt; <span class="tk-k">static_cast</span>&lt;<span class="tk-k">int</span>&gt;(result.size())) {', 1],
  ['        k = result.size();', 0],
  ['    }', 0],
  ['    result.resize(k);', 1],
  ['    <span class="tk-k">return</span> result;', 0],
  ['}', 0],
];

const demo = {
  code: $("#demo-code"), scan: $("#demo-scan"), ring: $("#demo-ring"),
  num: $("#demo-num"), verdict: $("#demo-verdict"), state: $("#demo-state"),
  running: false, visible: true,
};

function demoReset() {
  demo.code.innerHTML = DEMO_LINES.map(([html]) => `<span class="ln">${html || " "}</span>`).join("");
  setRing(demo.ring, 0);
  demo.ring.classList.remove("stroke-danger");
  demo.num.textContent = "0";
  demo.verdict.textContent = "вероятность ИИ";
  demo.state.textContent = "сканирование…";
  demo.state.classList.remove("done");
}

async function demoCycle() {
  if (demo.running) return;
  demo.running = true;
  while (demo.visible) {
    demoReset();
    const lines = [...demo.code.children];
    for (const ln of lines) {                      // строки появляются, как при вставке
      ln.classList.add("in");
      await sleep(REDUCED ? 0 : 70);
    }
    await sleep(300);
    // линия (высота 56px) доходит ровно до нижнего края области кода
    await runScan(demo.scan, demo.code.parentElement.offsetHeight - 56, 1.8);
    lines.forEach((ln, i) => {                     // подсвечиваются «подозрительные» строки
      const heat = DEMO_LINES[i][1];
      if (heat === 2) ln.classList.add("hot");
      else if (heat === 1) ln.classList.add("warm");
    });
    demo.ring.classList.add("stroke-danger");
    setRing(demo.ring, 91);
    countUp(demo.num, 91, 0, 1100);
    demo.state.textContent = "готово";
    demo.state.classList.add("done");
    await sleep(1200);
    demo.verdict.textContent = "Почти точно написан ИИ";
    if (REDUCED) break;
    await sleep(4200);
  }
  demo.running = false;
}

// демо работает только когда видно на экране — не тратит ресурсы при прокрутке ниже
new IntersectionObserver(([e]) => {
  demo.visible = e.isIntersecting;
  if (demo.visible) demoCycle();
}, { threshold: 0.3 }).observe($(".demo"));

/* ── токенизация на шаге 2 ───────────────────────────────────────────── */
const TOKENS = [["int", "kw"], ["main", "id"], ["(", "op"], [")", "op"], ["{", "op"],
  ["std", "ty"], ["::", "op"], ["cout", "id"], ["<<", "op"], ["sum", "id"], [";", "op"], ["}", "op"]];
const tokensEl = $("#tokens");
tokensEl.innerHTML = TOKENS.map(([t, c]) => `<span class="tok ${c}">${t}</span>`).join("");
new IntersectionObserver(([e], obs) => {
  if (!e.isIntersecting) return;
  [...tokensEl.children].forEach((t, i) => setTimeout(() => t.classList.add("in"), REDUCED ? 0 : 120 + i * 70));
  obs.disconnect();
}, { threshold: 0.6 }).observe($("#tokenize-step"));

/* ── линия процесса прорисовывается при прокрутке ────────────────────── */
const pipeline = $("#pipeline");
const pipeProgress = $("#pipe-progress");
const steps = [...pipeline.querySelectorAll(".step")];
function updatePipeline() {
  const rect = pipeline.getBoundingClientRect();
  const anchor = window.innerHeight * 0.6;          // «точка чтения» — 60% высоты окна
  const p = Math.min(Math.max((anchor - rect.top) / rect.height, 0), 1);
  pipeProgress.style.strokeDashoffset = String(100 - p * 100);
  steps.forEach((s) => s.classList.toggle("lit", s.getBoundingClientRect().top + 19 < anchor));
}
window.addEventListener("scroll", updatePipeline, { passive: true });
window.addEventListener("resize", updatePipeline);
updatePipeline();

/* ── проверка кода ───────────────────────────────────────────────────── */
const codeEl = $("#code");
const errorEl = $("#error");
const checkBtn = $("#check-btn");
const fileEl = $("#file");
const resultEl = $("#result");
const wrap = $("#editor-wrap");
const TOP_FRAGMENTS = 6;   // сколько самых «ИИ-шных» фрагментов длинного файла показывать
let serverOnline = false;

// есть ли рядом сервер с моделью — от этого зависит, настоящий результат или демо
fetch("/api/health", { cache: "no-store" })
  .then((r) => (r.ok ? r.json() : Promise.reject()))
  .then((info) => {
    serverOnline = true;
    $("#server-status").textContent = `Модель C++ подключена · ${info.device}`;
  })
  .catch(() => { $("#server-status").textContent = "Демо-версия: сервер с моделью не подключён"; });

function updateCounter() {
  const n = codeEl.value ? codeEl.value.split("\n").length : 0;
  const mod10 = n % 10, mod100 = n % 100;
  const word = mod10 === 1 && mod100 !== 11 ? "строка"
    : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? "строки" : "строк";
  $("#counter").textContent = `${n} ${word}`;
}
codeEl.addEventListener("input", () => { hideError(); updateCounter(); });

$("#upload").addEventListener("click", () => fileEl.click());
fileEl.addEventListener("change", () => {
  const file = fileEl.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    codeEl.value = String(reader.result);
    hideError(); updateCounter();
  };
  reader.onerror = () => showError("Не получилось прочитать файл. Попробуйте другой.");
  reader.readAsText(file);
  fileEl.value = "";
});

checkBtn.addEventListener("click", async () => {
  const code = codeEl.value.trim();
  if (code.length < 10) {
    showError("Вставьте код — хотя бы несколько строк.");
    $(".checker-card").classList.remove("shake");
    void $(".checker-card").offsetWidth;
    $(".checker-card").classList.add("shake");
    return;
  }
  hideError();
  checkBtn.disabled = true;
  checkBtn.textContent = "Анализ…";
  wrap.classList.add("scanning");
  try {
    const [result] = await Promise.all([
      analyze(code),
      runScan($("#editor-scan"), codeEl.offsetHeight + 40, 1.4), // обратная связь: код «читается»
    ]);
    showResult(result, code);
  } catch (e) {
    showError(e.message || "Не удалось выполнить проверку. Попробуйте ещё раз.");
  } finally {
    wrap.classList.remove("scanning");
    checkBtn.disabled = false;
    checkBtn.textContent = "Проверить";
  }
});

async function analyze(code) {
  if (serverOnline) {
    const r = await fetch("/api/detect", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || "Сервер не смог проверить код");
    return {
      ai: data.ai_pct,
      fragments: data.fragments.map((f) => ({ lines: f.lines, ai: f.ai_pct })),
      tokens: data.tokens, seconds: data.seconds, demo: false,
    };
  }
  return demoAnalyze(code);
}

// имитация ответа для демо-режима: детерминированно по тексту кода
function demoAnalyze(code) {
  const hash = (s) => {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return (h >>> 0) % 1000 / 10;
  };
  const lines = code.split("\n");
  const size = 40, step = 25;                       // те же фрагменты с перекрытием, что в приложении
  const fragments = [];
  for (let start = 0; start < lines.length; start += step) {
    const end = Math.min(start + size, lines.length);
    fragments.push({ lines: [start + 1, end], ai: hash(lines.slice(start, end).join("\n")) });
    if (end === lines.length) break;
  }
  const ai = Math.round(fragments.reduce((a, f) => a + f.ai, 0) / fragments.length);
  return new Promise((resolve) => setTimeout(() => resolve({ ai, fragments, demo: true }), 600));
}

function showResult({ ai, fragments, tokens, seconds, demo: isDemo }) {
  ai = Math.round(ai * 10) / 10;
  const [text, tone] = toneFor(ai);
  resultEl.hidden = false;
  resultEl.classList.remove("enter");
  void resultEl.offsetWidth;
  resultEl.classList.add("enter");

  const ring = $("#res-ring");
  ring.classList.remove("stroke-danger", "stroke-warn", "stroke-ok");
  ring.classList.add("stroke-" + tone);
  setRing(ring, 0);
  requestAnimationFrame(() => requestAnimationFrame(() => setRing(ring, ai)));
  countUp($("#pct"), Math.round(ai), 0, 1200);
  $(".result-num").className = "result-num tone-" + tone;

  const verdict = $("#verdict");
  verdict.textContent = text;
  verdict.className = "verdict tone-" + tone;

  // карта фрагментов: где в коде сосредоточены признаки ИИ
  const frEl = $("#fragments");
  frEl.innerHTML = "";
  if (fragments.length > 1) {
    // в длинном файле показываем самые подозрительные фрагменты, в порядке строк
    const shown = fragments.length > TOP_FRAGMENTS
      ? [...fragments].sort((a, b) => b.ai - a.ai).slice(0, TOP_FRAGMENTS).sort((a, b) => a.lines[0] - b.lines[0])
      : fragments;
    const title = fragments.length > TOP_FRAGMENTS
      ? `Самые похожие на ИИ фрагменты (${TOP_FRAGMENTS} из ${fragments.length})` : "Фрагменты кода";
    frEl.insertAdjacentHTML("beforeend", `<p class="fragments-title">${title}</p>`);
    shown.forEach((f, i) => {
      const [, ftone] = toneFor(f.ai);
      const row = document.createElement("div");
      row.className = "frag";
      row.style.animationDelay = (REDUCED ? 0 : 0.5 + i * 0.08) + "s";
      row.innerHTML = `<span class="frag-lines">строки ${f.lines[0]}–${f.lines[1]}</span>
        <span class="frag-bar"><i style="background: var(--${ftone === "ok" ? "success" : ftone})"></i></span>
        <span class="frag-pct">${Math.round(f.ai)}%</span>`;
      frEl.appendChild(row);
      setTimeout(() => { row.querySelector("i").style.width = f.ai + "%"; }, REDUCED ? 0 : 600 + i * 80);
    });
  }
  $("#meta").textContent = isDemo
    ? "Демо-результат: сервер с моделью не подключён"
    : `Модель C++ · ${tokens} токенов · ${seconds} с`;
  resultEl.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "center" });
}

function showError(message) { errorEl.textContent = message; errorEl.hidden = false; }
function hideError() { errorEl.hidden = true; }
