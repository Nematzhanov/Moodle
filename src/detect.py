"""Консольный детектор ИИ-кода.

    python src/detect.py                                  # интерактивный режим
    python src/detect.py --lang cpp --file solution.cpp   # проверить один файл и выйти

Модели берутся из models/cpp и models/java. Папку можно переопределить переменными окружения
CODECHECK_ROOT или CODECHECK_MODELS_DIR (используется в Docker).
"""
import argparse
import os
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ── Настройки ──────────────────────────────────────────────────────────────
ROOT       = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
MODELS_DIR = Path(os.environ.get("CODECHECK_MODELS_DIR") or ROOT / "models")
MODELS = {
    "C++":  MODELS_DIR / "cpp",
    "Java": MODELS_DIR / "java",
}
LANG_ALIASES = {"c++": "C++", "cpp": "C++", "java": "Java"}
MAX_LENGTH = 512  # должен совпадать с MAX_LENGTH из train.py,
                  # иначе детектор видит только часть того, на чём училась модель
# ───────────────────────────────────────────────────────────────────────────


# Определяем устройство: NVIDIA → Apple Silicon → CPU
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")


def load_model(path):
    tokenizer = AutoTokenizer.from_pretrained(path)
    model     = AutoModelForSequenceClassification.from_pretrained(path, num_labels=2)
    model     = model.to(device)
    model.eval()
    return tokenizer, model


def detect(code, tokenizer, model):
    # padding не нужен: в батче один пример, а короткая последовательность
    # обсчитывается быстрее, чем допаддленная до 512
    inputs = tokenizer(
        code,
        return_tensors="pt",
        max_length=MAX_LENGTH,
        truncation=True,
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    probs      = F.softmax(outputs.logits.float(), dim=1)[0]
    human_pct  = round(probs[0].item() * 100, 1)
    ai_pct     = round(probs[1].item() * 100, 1)
    return ai_pct, human_pct


def print_result(ai_pct, human_pct, lang):
    filled = int(ai_pct / 5)
    empty  = 20 - filled
    bar    = "█" * filled + "░" * empty

    print(f"\n─── Результат [{lang}] ────────────────────────")
    print(f"  Шкала ИИ:  [{bar}] {ai_pct}%")
    print(f"  🤖 ИИ-код:       {ai_pct}%")
    print(f"  👤 Код человека: {human_pct}%")

    if ai_pct >= 80:
        verdict = "Почти точно написан ИИ"
    elif ai_pct >= 60:
        verdict = "Скорее всего ИИ"
    elif ai_pct >= 40:
        verdict = "Сложно определить"
    elif ai_pct >= 20:
        verdict = "Скорее всего человек"
    else:
        verdict = "Почти точно написан человеком"

    print(f"  📌 Вывод: {verdict}")
    print("─────────────────────────────────────────\n")


def check_file(lang_arg, file_path):
    """Режим одной команды: проверить файл и выйти (код возврата 0 — успех)."""
    lang = LANG_ALIASES.get(lang_arg.lower())
    if lang is None:
        print(f"Неизвестный язык '{lang_arg}'. Доступно: cpp, java", file=sys.stderr)
        return 2
    path = Path(file_path)
    try:
        code = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        code = path.read_text(encoding="latin-1")
    except OSError as e:
        print(f"Не удалось прочитать файл: {e}", file=sys.stderr)
        return 2
    if len(code.strip()) < 10:
        print("Файл пустой или слишком короткий", file=sys.stderr)
        return 2
    try:
        tokenizer, model = load_model(MODELS[lang])
    except Exception as e:
        print(f"Модель [{lang}] не найдена: {e}", file=sys.stderr)
        return 1
    ai_pct, human_pct = detect(code, tokenizer, model)
    print_result(ai_pct, human_pct, f"{lang}, {path.name}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Детектор AI-кода (C++, Java)")
    ap.add_argument("--lang", help="язык файла: cpp или java")
    ap.add_argument("--file", help="путь к файлу с кодом (без него — интерактивный режим)")
    args = ap.parse_args()
    if args.file:
        if not args.lang:
            ap.error("вместе с --file укажите --lang cpp или --lang java")
        return check_file(args.lang, args.file)

    print("=" * 45)
    print("  Детектор AI-кода")
    print("  Поддерживает: C++, Java")
    print("=" * 45)

    # Загружаем модели
    loaded_models = {}
    for lang, path in MODELS.items():
        try:
            print(f"Загружаем модель [{lang}]...")
            loaded_models[lang] = load_model(path)
            print(f"  ✅ [{lang}] готова")
        except Exception as e:
            print(f"  ❌ [{lang}] не найдена: {e}")

    if not loaded_models:
        print("Ни одна модель не загружена! Проверь папки с моделями.")
        return 1

    print(f"\nУстройство: {device}")
    print("Введи 'выход' для завершения\n")

    while True:
        # Выбор языка
        print(f"Доступные модели: {', '.join(loaded_models.keys())}")
        try:
            lang = input("Выбери язык (или 'выход'): ").strip()
        except EOFError:
            return 0

        if lang.lower() == "выход":
            print("До свидания!")
            return 0

        lang = LANG_ALIASES.get(lang.lower(), lang)
        if lang not in loaded_models:
            print(f"Язык '{lang}' не поддерживается. Попробуй ещё раз.\n")
            continue

        print("Вставь код (затем на отдельной строке введи END):")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip().lower() == "выход":
                print("До свидания!")
                return 0
            if line.strip().upper() == "END":
                break
            lines.append(line)

        code = "\n".join(lines).strip()
        if not code or len(code) < 10:
            print("Пусто, попробуй ещё раз.\n")
            continue

        tokenizer, model = loaded_models[lang]
        ai_pct, human_pct = detect(code, tokenizer, model)
        print_result(ai_pct, human_pct, lang)


if __name__ == "__main__":
    sys.exit(main())
