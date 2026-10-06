// Демо-режим: сервер с моделью пока не подключён, поэтому результат
// считается локально и детерминированно по тексту кода.
// Когда появится сервер, нужно заменить только функцию analyze().

const MIN_LENGTH = 10;

const codeEl = document.getElementById("code");
const errorEl = document.getElementById("error");
const checkBtn = document.getElementById("check");
const uploadBtn = document.getElementById("upload");
const fileEl = document.getElementById("file");
const resultEl = document.getElementById("result");
const pctEl = document.getElementById("pct");
const verdictEl = document.getElementById("verdict");
const barEl = document.getElementById("bar");
const metaEl = document.getElementById("meta");
const segs = document.querySelectorAll(".seg");

document.getElementById("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try { localStorage.setItem("theme", next); } catch (e) {}
});

let language = "C++";

segs.forEach((btn) => {
  btn.addEventListener("click", () => {
    language = btn.dataset.lang;
    segs.forEach((b) => {
      const active = b === btn;
      b.classList.toggle("active", active);
      b.setAttribute("aria-selected", String(active));
    });
  });
});

uploadBtn.addEventListener("click", () => fileEl.click());

fileEl.addEventListener("change", () => {
  const file = fileEl.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    codeEl.value = String(reader.result);
    if (/\.java$/i.test(file.name)) selectLanguage("Java");
    else if (/\.(cpp|cc|c|h|hpp)$/i.test(file.name)) selectLanguage("C++");
    hideError();
  };
  reader.onerror = () => showError("Не получилось прочитать файл. Попробуйте другой.");
  reader.readAsText(file);
  fileEl.value = "";
});

function selectLanguage(lang) {
  document.querySelector(`.seg[data-lang="${lang}"]`).click();
}

codeEl.addEventListener("input", hideError);

checkBtn.addEventListener("click", async () => {
  const code = codeEl.value.trim();
  if (code.length < MIN_LENGTH) {
    showError("Вставьте код — хотя бы несколько строк.");
    return;
  }
  hideError();
  checkBtn.disabled = true;
  checkBtn.textContent = "Проверяем…";
  try {
    const result = await analyze(code, language);
    showResult(result);
  } catch (e) {
    showError("Не удалось выполнить проверку. Попробуйте ещё раз.");
  } finally {
    checkBtn.disabled = false;
    checkBtn.textContent = "Проверить";
  }
});

// Единственное место, которое нужно заменить при подключении сервера:
//   const r = await fetch("/api/detect", { method: "POST", headers: {"Content-Type": "application/json"},
//                         body: JSON.stringify({ code, language }) });
//   return r.json();   // { ai: число 0..100, human: число 0..100 }
async function analyze(code, lang) {
  await new Promise((r) => setTimeout(r, 700));
  let hash = 2166136261;
  for (let i = 0; i < code.length; i++) {
    hash ^= code.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  const ai = Math.round(((hash >>> 0) % 1000) / 10);
  return { ai, human: Math.round((100 - ai) * 10) / 10, language: lang, demo: true };
}

function verdictFor(ai) {
  if (ai >= 80) return ["Почти точно написан ИИ", "danger"];
  if (ai >= 60) return ["Скорее всего написан ИИ", "danger"];
  if (ai >= 40) return ["Сложно определить", "warn"];
  if (ai >= 20) return ["Скорее всего написан человеком", "success"];
  return ["Почти точно написан человеком", "success"];
}

function showResult({ ai, language: lang, demo }) {
  const [text, tone] = verdictFor(ai);
  resultEl.hidden = false;
  pctEl.textContent = ai;
  verdictEl.textContent = text;
  pctEl.parentElement.className = "result-number tone-" + tone;
  barEl.className = "bar bg-" + tone;
  barEl.style.width = "0";
  requestAnimationFrame(() => requestAnimationFrame(() => { barEl.style.width = ai + "%"; }));
  metaEl.textContent = `Модель: ${lang}` + (demo ? " · демо-результат, сервер не подключён" : "");
  resultEl.scrollIntoView({ behavior: "smooth", block: "center" });
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function hideError() {
  errorEl.hidden = true;
}
