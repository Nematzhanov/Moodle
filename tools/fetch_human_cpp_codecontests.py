"""Собирает проверяемо человеческие, короткие/средние C++ решения из
DeepMind CodeContests (https://huggingface.co/datasets/deepmind/code_contests).

Почему это надёжно "человеческое": датасет опубликован в феврале 2022 —
до выхода ChatGPT (ноябрь 2022) — и состоит из реальных решений участников
судей Codeforces/CodeChef/HackerEarth/CodeJam/AtCoder/AIZU. Авторство человека
гарантировано самой датой релиза, а не самодекларацией источника.

Зачем он нужен: в cppdata.csv класс "человек" почти не содержит короткого,
чисто написанного кода (конкурсное программирование, типовые шаблоны) —
см. README.md, раздел «Ограничения». Эти решения ровно такого профиля.

Запуск из корня проекта:  .venv/bin/python tools/fetch_human_cpp_codecontests.py
Вывод:   cpp_human_codecontests.csv (code;label, label=0, разделитель ";")
"""
import csv
import json
import os
import time
import urllib.request
from pathlib import Path

API = "https://datasets-server.huggingface.co/rows"
DATASET = "deepmind/code_contests"
SPLIT = "train"
PAGE_SIZE = 100
MAX_PAGES = 40          # 40 * 100 = 4000 задач с запасом (весь train ~3762)
TARGET_COUNT = 500      # сколько решений хотим набрать
MIN_LEN, MAX_LEN = 80, 4000   # разумный диапазон длины для одного файла-решения
CPP_LANG_ID = 2         # ClassLabel: UNKNOWN=0, PYTHON=1, CPP=2, PYTHON3=3, JAVA=4

ROOT     = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
OUT_PATH = ROOT / "data" / "sources" / "cpp_human_codecontests.csv"


def fetch_page(offset: int) -> dict:
    url = f"{API}?dataset={DATASET}&config=default&split={SPLIT}&offset={offset}&length={PAGE_SIZE}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  (повтор после ошибки {e})")
            time.sleep(2)


def clean_code(code: str) -> str:
    # нормализуем переносы строк, убираем висящие пробелы в конце
    return code.replace("\r\n", "\n").strip()


def pick_solution(solutions: dict) -> str | None:
    """Берём одно решение на C++ на задачу — предпочитаем ближе к медианной
    длине среди доступных, чтобы не тянуть вырожденно короткие/длинные."""
    langs = solutions.get("language", [])
    codes = solutions.get("solution", [])
    cpp_codes = [c for lang, c in zip(langs, codes) if lang == CPP_LANG_ID]
    cpp_codes = [clean_code(c) for c in cpp_codes]
    cpp_codes = [c for c in cpp_codes if MIN_LEN <= len(c) <= MAX_LEN]
    if not cpp_codes:
        return None
    cpp_codes.sort(key=len)
    return cpp_codes[len(cpp_codes) // 2]


def main():
    seen = set()
    rows_out = []

    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        print(f"Страница {page + 1}/{MAX_PAGES} (offset={offset})...")
        data = fetch_page(offset)
        rows = data.get("rows", [])
        if not rows:
            print("  пустая страница — задачи закончились")
            break

        for item in rows:
            row = item["row"]
            code = pick_solution(row.get("solutions", {}))
            if not code or code in seen:
                continue
            seen.add(code)
            rows_out.append(code)

        print(f"  накоплено решений: {len(rows_out)}")
        if len(rows_out) >= TARGET_COUNT:
            break

    print(f"\nВсего собрано уникальных C++ решений: {len(rows_out)}")

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writerow(["code", "label"])
        for code in rows_out:
            writer.writerow([code, 0])

    print(f"Сохранено в {OUT_PATH} (label=0, разделитель ';')")


if __name__ == "__main__":
    main()
